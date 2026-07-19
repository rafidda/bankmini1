# File: app/controllers/backup_manager.py
# Berisi logika untuk melakukan backup dan restore database SQLite.

import os
import shutil
from datetime import datetime
from typing import Optional


def get_database_path() -> str:
    """
    Menghitung dan mengembalikan path absolut ke file database 'bankmini.db'.
    Path dihitung secara dinamis relatif terhadap lokasi file ini,
    sehingga akan selalu benar meskipun aplikasi dijalankan dari direktori yang berbeda,
    termasuk saat sudah di-compile menjadi file executable.

    Struktur:
    - project_root/
      - app/
        - controllers/
          - backup_manager.py  (file ini)
      - bankmini.db (target)

    Dari file ini, kita perlu naik 2 level ('..', '..') untuk mencapai root.
    """
    # Tentukan path absolut ke root folder project.
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

    # Nama file database
    database_file = "bankmini.db"

    # Gabungkan path root dengan nama file database dan kembalikan hasilnya.
    return os.path.join(project_root, database_file)


def generate_backup_filename() -> str:
    """
    Membuat nama file default untuk backup dengan format timestamp.
    Contoh: 'BankMiniSMK_Backup_20231027_143000.db'
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return f"BankMiniSMK_Backup_{timestamp}.db"


def backup_database(destination_path: str) -> bool:
    """
    Menyalin file database aktif ke lokasi tujuan yang ditentukan.

    :param destination_path: Path lengkap (termasuk nama file) untuk menyimpan file backup.
    :return: True jika berhasil.
    :raises Exception: Jika file database sumber tidak ditemukan atau terjadi error saat menyalin.
    """
    source_path = get_database_path()

    # Validasi: Pastikan file database sumber benar-benar ada sebelum mencoba menyalin.
    if not os.path.exists(source_path):
        raise Exception(f"File database tidak ditemukan di path: {source_path}")

    try:
        # Gunakan shutil.copy2 untuk menyalin file beserta metadatanya (seperti tanggal modifikasi).
        shutil.copy2(source_path, destination_path)
        return True
    except Exception as e:
        # Tangkap error yang mungkin terjadi selama proses penyalinan file.
        raise Exception(f"Gagal melakukan backup database: {e}")


def restore_database(source_path: str) -> bool:
    """
    Menimpa database aktif dengan file backup dari `source_path`.
    Secara otomatis membuat backup dari database saat ini sebelum menimpanya sebagai jaring pengaman.

    :param source_path: Path lengkap menuju file backup (.db) yang akan di-restore.
    :return: True jika berhasil.
    :raises Exception: Jika file sumber tidak valid atau terjadi error saat proses restore.
    """
    # Validasi 1: Pastikan file sumber (backup) yang dipilih ada.
    if not os.path.exists(source_path):
        raise Exception(f"File backup sumber tidak ditemukan di: {source_path}")

    # Validasi 2: Pastikan file adalah file .db
    if not source_path.lower().endswith('.db'):
        raise Exception("File yang dipilih bukan file database yang valid (harus berekstensi .db).")

    db_path = get_database_path()
    db_dir = os.path.dirname(db_path)
    auto_backup_path = ""

    # --- Jaring Pengaman: Buat backup otomatis dari database AKTIF sebelum ditimpa ---
    # Ini sangat penting untuk mencegah kehilangan data jika file restore ternyata korup atau salah.
    try:
        if os.path.exists(db_path):
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            auto_backup_filename = f"bankmini_auto_backup_before_restore_{timestamp}.db"
            auto_backup_path = os.path.join(db_dir, auto_backup_filename)
            shutil.copy2(db_path, auto_backup_path)
    except Exception as e:
        # Jika pembuatan jaring pengaman gagal, batalkan seluruh proses restore.
        raise Exception(f"Gagal membuat backup otomatis sebelum restore. Proses dibatalkan. Error: {e}")

    # --- Proses Inti: Timpa database aktif dengan file backup ---
    try:
        # Salin file dari source_path (backup) ke db_path (database aktif). Ini akan menimpa file yang ada.
        shutil.copy2(source_path, db_path)
        return True
    except Exception as e:
        # Jika proses restore gagal, beri tahu pengguna dan sebutkan file jaring pengaman.
        error_message = f"Gagal melakukan restore database: {e}\n\n"
        if auto_backup_path:
            error_message += (f"PENTING: Sebuah backup otomatis dari kondisi sebelum restore telah disimpan di:\n{auto_backup_path}\n"
                              f"Anda bisa mencoba me-restore dari file tersebut secara manual.")
        raise Exception(error_message)