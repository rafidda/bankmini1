# File: app/controllers/settings_manager.py
# Berisi fungsi-fungsi utilitas untuk mengelola tabel 'settings'.

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.models import Settings


def get_setting(db: Session, key: str, default: str) -> str:
    """
    Mengambil nilai pengaturan dari database berdasarkan key.
    Jika key tidak ditemukan, nilai default akan dikembalikan tanpa
    membuat record baru di database.

    :param db: Sesi database SQLAlchemy yang aktif.
    :param key: Kunci (nama) dari pengaturan yang ingin diambil.
    :param default: Nilai default yang akan dikembalikan jika key tidak ditemukan.
    :return: Nilai pengaturan dalam bentuk string.
    """
    stmt = select(Settings.value).where(Settings.key == key)
    result = db.execute(stmt).scalar_one_or_none()
    return result if result is not None else default


def set_setting(db: Session, key: str, value: str) -> None:
    """
    Menyimpan atau memperbarui nilai pengaturan di database.
    Jika key sudah ada, value akan di-update. Jika belum ada,
    record baru akan dibuat.

    :param db: Sesi database SQLAlchemy yang aktif.
    :param key: Kunci (nama) dari pengaturan yang ingin disimpan.
    :param value: Nilai baru untuk pengaturan tersebut.
    """
    # Cek apakah setting dengan key tersebut sudah ada
    setting = db.execute(select(Settings).where(Settings.key == key)).scalar_one_or_none()

    if setting:
        # Jika ada, update nilainya
        setting.value = value
    else:
        # Jika tidak ada, buat record baru
        new_setting = Settings(key=key, value=value)
        db.add(new_setting)

    # Simpan perubahan ke database
    db.commit()


def get_bulan_cutoff_tahun_ajaran(db: Session) -> int:
    """
    Fungsi spesifik untuk mendapatkan bulan cutoff tahun ajaran dari settings.
    Bulan ini menentukan kapan tahun ajaran baru dimulai.

    :param db: Sesi database SQLAlchemy yang aktif.
    :return: Angka bulan (1-12). Defaultnya adalah 7 (Juli).
    """
    # Panggil get_setting dengan key spesifik dan default '7'
    bulan_str = get_setting(db, 'bulan_cutoff_tahun_ajaran', '7')
    try:
        # Konversi ke integer, dengan fallback ke 7 jika nilai di DB tidak valid
        return int(bulan_str)
    except (ValueError, TypeError):
        return 7