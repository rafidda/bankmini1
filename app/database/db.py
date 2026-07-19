import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import declarative_base

# --- 1. Setup Koneksi ke Database SQLite ---

# Tentukan path absolut ke root folder project.
# os.path.dirname(__file__) -> folder saat ini (app/database)
# '..' -> naik satu level ke folder 'app'
# '..' -> naik satu level lagi ke root folder project (sejajar dengan main.py)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

# Nama file database SQLite
DATABASE_FILE = "bankmini.db"

# Buat URL koneksi untuk SQLAlchemy. Formatnya "sqlite:///path/ke/file.db"
DATABASE_URL = f"sqlite:///{os.path.join(PROJECT_ROOT, DATABASE_FILE)}"

# Buat engine SQLAlchemy.
# Engine adalah titik masuk utama ke database.
# 'connect_args' diperlukan untuk SQLite agar memperbolehkan koneksi dari thread yang berbeda,
# yang umum terjadi pada aplikasi desktop untuk menghindari error.
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

# --- 2. Setup Session untuk Interaksi Database ---

# Buat kelas SessionLocal menggunakan sessionmaker.
# Instance dari kelas SessionLocal ini akan menjadi sesi database yang kita gunakan
# untuk semua interaksi dengan database (query, insert, update, delete).
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# --- 3. Setup Base untuk Model Declarative ---

# Buat kelas Base yang akan menjadi dasar untuk semua model tabel kita.
# Semua kelas model (misalnya, Nasabah, Transaksi, dll.) yang akan Anda buat nanti
# di app/models/models.py harus mewarisi (inherit) dari kelas Base ini.
Base = declarative_base()

# --- 4. Fungsi Inisialisasi Database ---

def init_db():
    """
    Fungsi ini akan membuat semua tabel dalam database berdasarkan model yang ada.
    PENTING: Semua model harus di-import di sini sebelum create_all() dipanggil
    agar SQLAlchemy tahu tabel apa saja yang harus dibuat.
    """
    # Import semua modul yang berisi definisi model Anda di sini.
    # Ini akan mendaftarkan model-model tersebut ke metadata Base.
    import app.models.models

    # Membuat semua tabel yang terdaftar di metadata Base.
    # Perintah ini aman untuk dijalankan berulang kali karena tidak akan
    # membuat ulang tabel yang sudah ada.
    Base.metadata.create_all(bind=engine)