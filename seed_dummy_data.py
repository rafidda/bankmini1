# seed_dummy_data.py
# Script untuk membuat data dummy (guru, siswa, nasabah, transaksi) untuk testing.
# Aman dijalankan berkali-kali (skip jika data user/nasabah sudah ada; transaksi
# hanya di-generate SEKALI, dicek lewat jumlah transaksi yang sudah ada).
#
# Cara pakai setelah reset database:
#   Remove-Item bankmini.db
#   python main.py        (biar superadmin & tabel ke-seed dulu, lalu tutup aplikasinya)
#   alembic stamp head    (supaya alembic tidak bingung, karena init_db() bikin skema terbaru langsung)
#   python seed_dummy_data.py

import random
from datetime import datetime, timedelta
from decimal import Decimal

import bcrypt
from app.database.db import SessionLocal, init_db
from app.models.models import Account, JournalEntry, Transaction, User

# Pastikan tabel sudah ada (aman dipanggil berkali-kali, tidak akan menghapus data)
init_db()

NAMA_DEPAN = ["Budi", "Siti", "Ahmad", "Dewi", "Rudi", "Ani", "Joko", "Rina", "Agus", "Lina"]
NAMA_BELAKANG = ["Santoso", "Wijaya", "Pratama", "Kusuma", "Saputra", "Lestari", "Hidayat", "Utami"]
KELAS_LIST = [10, 11, 12]  # Tingkat kelas SMK: 10, 11, 12


def random_nama():
    return f"{random.choice(NAMA_DEPAN)} {random.choice(NAMA_BELAKANG)}"


def hash_pw(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def random_tanggal_dalam_hari_terakhir(jumlah_hari: int = 45) -> datetime:
    """Menghasilkan datetime acak dalam rentang N hari terakhir dari sekarang,
    dengan jam acak juga (biar realistis, tidak semua jam 00:00)."""
    hari_mundur = random.randint(0, jumlah_hari)
    jam_acak = random.randint(7, 15)  # jam kerja bank mini, 07:00 - 15:59
    menit_acak = random.randint(0, 59)
    target = datetime.now() - timedelta(days=hari_mundur)
    return target.replace(hour=jam_acak, minute=menit_acak, second=0, microsecond=0)


with SessionLocal() as db:
    # ==========================================================
    # 1. BUAT 2 AKUN ADMIN (GURU PEMBINA)
    # ==========================================================
    admin_data = [
        ("guru1", "NIP198501012010011001"),
        ("guru2", "NIP199003152012012002"),
    ]
    created_admins = []

    for username, nip in admin_data:
        existing = db.query(User).filter(User.username == username).first()
        if existing:
            print(f"⏭️  User '{username}' sudah ada, dilewati.")
            created_admins.append(existing)
            continue

        user = User(
            username=username,
            password_hash=hash_pw(username),
            role="admin",
            nama_lengkap=random_nama(),
            nomor_induk=nip,
            kelas=None,
            is_active=True,
        )
        db.add(user)
        db.flush()
        created_admins.append(user)
        print(f"✅ Admin dibuat: {username} / password: {username} (NIP: {nip}, nama: {user.nama_lengkap})")

    db.commit()

    # ==========================================================
    # 2. BUAT 2 AKUN SISWA (TELLER)
    # ==========================================================
    siswa_data = [
        ("siswa1", "0051234567"),
        ("siswa2", "0051234568"),
    ]
    created_siswa = []

    for username, nis in siswa_data:
        existing = db.query(User).filter(User.username == username).first()
        if existing:
            print(f"⏭️  User '{username}' sudah ada, dilewati.")
            created_siswa.append(existing)
            continue

        user = User(
            username=username,
            password_hash=hash_pw(username),
            role="siswa",
            nama_lengkap=random_nama(),
            nomor_induk=nis,
            kelas=random.choice(KELAS_LIST),
            is_active=True,
            created_by=created_admins[0].id if created_admins else None,
        )
        db.add(user)
        db.flush()
        created_siswa.append(user)
        print(f"✅ Siswa dibuat: {username} / password: {username} (NIS: {nis}, nama: {user.nama_lengkap}, kelas: {user.kelas})")

    db.commit()

    # ==========================================================
    # 3. BUAT 5 NASABAH CONTOH
    #    Saldo awal dinaikkan (Rp 300.000) supaya aman dari saldo minus
    #    saat transaksi tarik/transfer diproses sebelum transaksi setor
    #    (karena urutan transaksi nanti diacak berdasarkan tanggal, bukan jenis).
    # ==========================================================
    creator_id = created_admins[0].id if created_admins else None

    nasabah_contoh = [
        ("001", "Budi Santoso", "0041111001", 12, Decimal("300000")),
        ("002", "Ani Wijaya", "0041111002", 12, Decimal("300000")),
        ("003", "Joko Pratama", "0041111003", 11, Decimal("300000")),
        ("004", "Dewi Kusuma", "0041111004", 11, Decimal("300000")),
        ("005", "Rudi Hidayat", "0041111005", 10, Decimal("300000")),
    ]
    created_accounts = {}

    for nomor_rek, nama, nis, kelas, saldo_awal in nasabah_contoh:
        existing_acc = db.query(Account).filter(Account.nomor_rekening == nomor_rek).first()
        if existing_acc:
            print(f"⏭️  Rekening '{nomor_rek}' sudah ada, dilewati.")
            created_accounts[nomor_rek] = existing_acc
            continue

        acc = Account(
            nomor_rekening=nomor_rek,
            nama_nasabah=nama,
            nis_nasabah=nis,
            kelas_nasabah=kelas,
            saldo=saldo_awal,
            created_by=creator_id,
        )
        db.add(acc)
        db.flush()
        created_accounts[nomor_rek] = acc
        print(f"✅ Nasabah dibuat: {nomor_rek} - {nama} (NIS: {nis}, saldo awal: Rp {saldo_awal:,.0f})")

    db.commit()

    # ==========================================================
    # 4. BUAT DATA TRANSAKSI LENGKAP DENGAN TANGGAL BERVARIASI
    #    Setiap nasabah (5 akun) mendapat:
    #    - 2x Setor
    #    - 2x Tarik
    #    - 2x jadi pengirim transfer (transfer_keluar)
    #    - 2x jadi penerima transfer (transfer_masuk), via skema rotasi
    #    Semua event diberi tanggal acak dalam 45 hari terakhir, LALU
    #    diproses berurutan sesuai tanggal supaya saldo_akhir tetap konsisten
    #    secara kronologis (bukan sesuai urutan kode).
    # ==========================================================
    existing_trx_count = db.query(Transaction).count()
    if existing_trx_count > 0:
        print(f"⏭️  Sudah ada {existing_trx_count} transaksi di database, "
              f"seed transaksi dilewati (hindari duplikat). "
              f"Reset database dulu jika ingin data transaksi baru.")
    else:
        siswa1, siswa2 = created_siswa[0], created_siswa[1]
        tellers = [siswa1.id, siswa2.id]

        urutan_rekening = ["001", "002", "003", "004", "005"]

        # --- Kumpulkan semua "event" transaksi dulu, lengkap dengan tanggal acak ---
        events = []

        jumlah_setor_pilihan = [15000, 20000, 25000, 30000, 35000, 40000]
        jumlah_tarik_pilihan = [10000, 15000, 20000]

        for nomor_rek in urutan_rekening:
            for _ in range(2):
                events.append({
                    "type": "setor",
                    "account_id": nomor_rek,
                    "jumlah": Decimal(random.choice(jumlah_setor_pilihan)),
                    "teller_id": random.choice(tellers),
                    "tanggal": random_tanggal_dalam_hari_terakhir(),
                })
            for _ in range(2):
                events.append({
                    "type": "tarik",
                    "account_id": nomor_rek,
                    "jumlah": Decimal(random.choice(jumlah_tarik_pilihan)),
                    "teller_id": random.choice(tellers),
                    "tanggal": random_tanggal_dalam_hari_terakhir(),
                })

        # Transfer: skema rotasi 2 putaran penuh, supaya tiap akun jadi
        # pengirim 2x dan penerima 2x (001->002->003->004->005->001, x2)
        jumlah_transfer_pilihan = [10000, 15000, 18000, 20000, 25000]
        for putaran in range(2):
            for i in range(len(urutan_rekening)):
                sumber = urutan_rekening[i]
                tujuan = urutan_rekening[(i + 1) % len(urutan_rekening)]
                events.append({
                    "type": "transfer",
                    "sumber_id": sumber,
                    "tujuan_id": tujuan,
                    "jumlah": Decimal(random.choice(jumlah_transfer_pilihan)),
                    "teller_id": random.choice(tellers),
                    "tanggal": random_tanggal_dalam_hari_terakhir(),
                })

        # --- Urutkan SEMUA event berdasarkan tanggal, dari yang PALING LAMA ---
        events.sort(key=lambda e: e["tanggal"])

        # --- Proses satu per satu sesuai urutan tanggal ---
        for event in events:
            waktu = event["tanggal"]
            teller_id = event["teller_id"]
            jumlah = event["jumlah"]

            if event["type"] == "setor":
                acc = created_accounts[event["account_id"]]
                acc.saldo += jumlah
                trx = Transaction(
                    account_id=acc.id, jenis='setor', jumlah=jumlah,
                    saldo_akhir=acc.saldo, teller_id=teller_id,
                    keterangan="Setor tabungan (data testing)",
                    waktu_transaksi=waktu,
                )
                db.add(trx)
                db.flush()
                db.add_all([
                    JournalEntry(transaction_id=trx.id, akun='Kas', debit=jumlah, kredit=0, waktu=waktu),
                    JournalEntry(transaction_id=trx.id, akun=f'Tabungan Nasabah - {acc.nama_nasabah}', debit=0, kredit=jumlah, waktu=waktu),
                ])
                print(f"✅ [{waktu.strftime('%d/%m/%Y')}] Setor: {acc.nomor_rekening} +Rp {jumlah:,.0f}")

            elif event["type"] == "tarik":
                acc = created_accounts[event["account_id"]]
                acc.saldo -= jumlah
                trx = Transaction(
                    account_id=acc.id, jenis='tarik', jumlah=jumlah,
                    saldo_akhir=acc.saldo, teller_id=teller_id,
                    keterangan="Tarik tabungan (data testing)",
                    waktu_transaksi=waktu,
                )
                db.add(trx)
                db.flush()
                db.add_all([
                    JournalEntry(transaction_id=trx.id, akun=f'Tabungan Nasabah - {acc.nama_nasabah}', debit=jumlah, kredit=0, waktu=waktu),
                    JournalEntry(transaction_id=trx.id, akun='Kas', debit=0, kredit=jumlah, waktu=waktu),
                ])
                print(f"✅ [{waktu.strftime('%d/%m/%Y')}] Tarik: {acc.nomor_rekening} -Rp {jumlah:,.0f}")

            elif event["type"] == "transfer":
                acc_sumber = created_accounts[event["sumber_id"]]
                acc_tujuan = created_accounts[event["tujuan_id"]]
                acc_sumber.saldo -= jumlah
                acc_tujuan.saldo += jumlah

                trx_keluar = Transaction(
                    account_id=acc_sumber.id, jenis='transfer_keluar', jumlah=jumlah,
                    saldo_akhir=acc_sumber.saldo, teller_id=teller_id,
                    keterangan=f"Transfer ke {acc_tujuan.nomor_rekening} - {acc_tujuan.nama_nasabah} (data testing)",
                    waktu_transaksi=waktu,
                )
                db.add(trx_keluar)
                db.flush()

                trx_masuk = Transaction(
                    account_id=acc_tujuan.id, jenis='transfer_masuk', jumlah=jumlah,
                    saldo_akhir=acc_tujuan.saldo, teller_id=teller_id,
                    keterangan=f"Transfer masuk dari {acc_sumber.nomor_rekening} - {acc_sumber.nama_nasabah} (data testing)",
                    waktu_transaksi=waktu,
                )
                db.add(trx_masuk)

                db.add_all([
                    JournalEntry(transaction_id=trx_keluar.id, akun=f'Tabungan Nasabah - {acc_sumber.nama_nasabah}', debit=jumlah, kredit=0, waktu=waktu),
                    JournalEntry(transaction_id=trx_keluar.id, akun=f'Tabungan Nasabah - {acc_tujuan.nama_nasabah}', debit=0, kredit=jumlah, waktu=waktu),
                ])
                print(f"✅ [{waktu.strftime('%d/%m/%Y')}] Transfer: {acc_sumber.nomor_rekening} -> {acc_tujuan.nomor_rekening} Rp {jumlah:,.0f}")

        db.commit()

print("\n" + "=" * 60)
print("SELESAI. Ringkasan akun & data untuk testing:")
print("=" * 60)
print("Admin  : guru1 / guru1   |   guru2 / guru2")
print("Siswa  : siswa1 / siswa1 |   siswa2 / siswa2")
print("Nasabah: 001 (Budi), 002 (Ani), 003 (Joko), 004 (Dewi), 005 (Rudi)")
print("Transaksi per nasabah: 2 Setor, 2 Tarik, 2x jadi pengirim transfer,")
print("                       2x jadi penerima transfer")
print("Total: 40 baris transaksi, tanggal tersebar acak 45 hari terakhir")
print("=" * 60)