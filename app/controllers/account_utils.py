# File: app/controllers/account_utils.py
# Berisi fungsi-fungsi utilitas terkait dengan manajemen rekening.

from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models import Account
from app.controllers.settings_manager import get_bulan_cutoff_tahun_ajaran, get_setting


def get_kode_tahun_ajaran(db: Session, tanggal: Optional[datetime] = None) -> str:
    """
    Menentukan kode tahun ajaran (4 digit) berdasarkan tanggal.
    Tahun ajaran dihitung dari Juli hingga Juni tahun berikutnya, sesuai
    dengan kalender pendidikan di Indonesia.

    Contoh:
    - 15 Juli 2026 -> Tahun Ajaran 2026/2027 -> Kode "2627"
    - 10 Maret 2026 -> Tahun Ajaran 2025/2026 -> Kode "2526"

    :param db: Sesi database SQLAlchemy yang aktif untuk mengambil settings.
    :param tanggal: Tanggal yang akan digunakan. Jika None, gunakan waktu saat ini.
    :return: String 4 digit kode tahun ajaran.
    """
    if tanggal is None:
        tanggal = datetime.now()

    tahun = tanggal.year
    bulan = tanggal.month

    # Ambil bulan cutoff dari database, default ke 7 (Juli) jika tidak ada.
    bulan_cutoff = get_bulan_cutoff_tahun_ajaran(db)

    # Jika bulan saat ini >= bulan cutoff, tahun ajaran dimulai pada tahun ini.
    if bulan >= bulan_cutoff:
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
    Format: [2 digit kode custom][4 digit kode tahun ajaran][4 digit nomor urut]
    Contoh: 0026270001

    Fungsi ini harus dipanggil dalam satu sesi transaksi database yang sama dengan
    saat menyimpan rekening baru untuk menghindari race condition.

    :param db: Sesi database SQLAlchemy yang aktif.
    :param tanggal: Tanggal pembuatan rekening. Jika None, gunakan waktu saat ini.
    :return: String nomor rekening baru yang unik.
    """
    # 1. Ambil kode custom 2 digit dari settings, dengan fallback '00'.
    # Sanitasi untuk memastikan selalu 2 digit.
    kode_custom_raw = get_setting(db, 'kode_custom_rekening', '00')
    kode_custom = kode_custom_raw.strip()[:2].zfill(2)

    # 2. Dapatkan prefix 4 digit berdasarkan tahun ajaran.
    prefix_tahun_ajaran = get_kode_tahun_ajaran(db, tanggal)

    # 3. Gabungkan kedua prefix untuk pencarian di database.
    full_prefix = f"{kode_custom}{prefix_tahun_ajaran}"

    # 4. Query semua nomor rekening yang ada dengan prefix gabungan yang sama.
    # PENTING: Query ini TIDAK memfilter is_deleted=False. Semua nomor rekening,
    # termasuk yang sudah ditutup (soft-deleted), harus diperiksa untuk
    # memastikan nomor yang baru benar-benar unik dan tidak pernah dipakai ulang.
    stmt = select(Account.nomor_rekening).where(Account.nomor_rekening.like(f'{full_prefix}%'))
    hasil_query = db.execute(stmt).scalars().all()

    # 5. Cari nomor urut terakhir dari hasil query.
    nomor_urut_terakhir = 0
    if hasil_query:
        # Ambil 4 digit terakhir dari setiap nomor rekening, konversi ke int, lalu cari nilai maksimum.
        list_nomor_urut = [int(nomor[-4:]) for nomor in hasil_query]
        if list_nomor_urut:
            nomor_urut_terakhir = max(list_nomor_urut)

    # 6. Buat nomor urut baru dan format menjadi 4 digit.
    nomor_urut_baru = nomor_urut_terakhir + 1
    nomor_urut_formatted = f"{nomor_urut_baru:04d}"

    # 7. Gabungkan semua bagian menjadi nomor rekening final.
    return f"{full_prefix}{nomor_urut_formatted}"