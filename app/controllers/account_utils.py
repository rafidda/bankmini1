# File: app/controllers/account_utils.py
# Berisi fungsi-fungsi utilitas terkait dengan manajemen rekening.

from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models import Account


def get_kode_tahun_ajaran(tanggal: Optional[datetime] = None) -> str:
    """
    Menentukan kode tahun ajaran (4 digit) berdasarkan tanggal.
    Tahun ajaran dihitung dari Juli hingga Juni tahun berikutnya, sesuai
    dengan kalender pendidikan di Indonesia.

    Contoh:
    - 15 Juli 2026 -> Tahun Ajaran 2026/2027 -> Kode "2627"
    - 10 Maret 2026 -> Tahun Ajaran 2025/2026 -> Kode "2526"

    :param tanggal: Tanggal yang akan digunakan. Jika None, gunakan waktu saat ini.
    :return: String 4 digit kode tahun ajaran.
    """
    if tanggal is None:
        tanggal = datetime.now()

    tahun = tanggal.year
    bulan = tanggal.month

    # Jika bulan adalah Juli (7) atau setelahnya, tahun ajaran dimulai pada tahun ini.
    if bulan >= 7:
        tahun_mulai = tahun
        tahun_selesai = tahun + 1
    # Jika bulan adalah Januari-Juni, tahun ajaran dimulai pada tahun sebelumnya.
    else:
        tahun_mulai = tahun - 1
        tahun_selesai = tahun

    # Ambil 2 digit terakhir dari masing-masing tahun dan gabungkan.
    # Contoh: 2026 -> "26", 2027 -> "27", hasilnya "2627"
    kode_tahun_ajaran = f"{str(tahun_mulai)[-2:]}{str(tahun_selesai)[-2:]}"
    return kode_tahun_ajaran


def generate_nomor_rekening(db: Session, tanggal: Optional[datetime] = None) -> str:
    """
    Membuat nomor rekening baru yang unik berdasarkan tahun ajaran.
    Format: [4 digit kode tahun ajaran][4 digit nomor urut]
    Contoh: 26270001

    Fungsi ini harus dipanggil dalam satu sesi transaksi database yang sama dengan
    saat menyimpan rekening baru untuk menghindari race condition.

    :param db: Sesi database SQLAlchemy yang aktif.
    :param tanggal: Tanggal pembuatan rekening. Jika None, gunakan waktu saat ini.
    :return: String nomor rekening baru yang unik.
    """
    # 1. Dapatkan prefix 4 digit berdasarkan tahun ajaran.
    prefix = get_kode_tahun_ajaran(tanggal)

    # 2. Query semua nomor rekening yang ada dengan prefix yang sama.
    # PENTING: Query ini TIDAK memfilter is_deleted=False. Semua nomor rekening,
    # termasuk yang sudah ditutup (soft-deleted), harus diperiksa untuk
    # memastikan nomor yang baru benar-benar unik dan tidak pernah dipakai ulang.
    stmt = select(Account.nomor_rekening).where(Account.nomor_rekening.like(f'{prefix}%'))
    hasil_query = db.execute(stmt).scalars().all()

    # 3. Cari nomor urut terakhir dari hasil query.
    nomor_urut_terakhir = 0
    if hasil_query:
        # Ambil 4 digit terakhir dari setiap nomor rekening, konversi ke int, lalu cari nilai maksimum.
        list_nomor_urut = [int(nomor[-4:]) for nomor in hasil_query]
        if list_nomor_urut:
            nomor_urut_terakhir = max(list_nomor_urut)

    # 4. Buat nomor urut baru dan format menjadi 4 digit.
    nomor_urut_baru = nomor_urut_terakhir + 1
    nomor_urut_formatted = f"{nomor_urut_baru:04d}"

    # 5. Gabungkan prefix dengan nomor urut baru.
    return f"{prefix}{nomor_urut_formatted}"