import bcrypt
from sqlalchemy import select

# Import SessionLocal untuk membuat sesi database dari file db.py
from app.database.db import SessionLocal, init_db
# Import model User untuk query dan pembuatan data
from app.models.models import User


def seed_superadmin():
    """
    Membuat user superadmin pertama kali jika belum ada di database.

    Fungsi ini akan mengecek keberadaan user dengan role 'superadmin'.
    Jika tidak ditemukan, fungsi ini akan membuat satu user superadmin
    dengan username dan password default.
    """
    # Menggunakan 'with' statement untuk memastikan sesi database (db)
    # ditutup secara otomatis setelah blok ini selesai, bahkan jika terjadi error.
    with SessionLocal() as db:
        # 1. Mengecek apakah user dengan role 'superadmin' sudah ada
        stmt = select(User).where(User.role == 'superadmin')
        existing_superadmin = db.execute(stmt).scalars().first()

        if existing_superadmin:
            # Jika sudah ada, tampilkan pesan dan tidak melakukan apa-apa
            print("✅ Superadmin sudah ada di database.")
        else:
            # 2. Jika belum ada, buat user superadmin baru
            print("👤 Superadmin tidak ditemukan, membuat user baru...")

            # Password default dalam bentuk teks biasa
            password_plain = "admin123"
            # Ubah password menjadi bytes, karena bcrypt bekerja dengan bytes
            password_bytes = password_plain.encode('utf-8')

            # Generate salt dan hash password menggunakan bcrypt
            salt = bcrypt.gensalt()
            hashed_password = bcrypt.hashpw(password_bytes, salt)

            # Buat instance model User dengan data yang sudah disiapkan
            new_superadmin = User(
                username="superadmin",
                password_hash=hashed_password.decode('utf-8'), # Simpan hash sebagai string di DB
                role="superadmin",
                nama_lengkap="Administrator BPRS",
                is_active=True
            )

            # Tambahkan user baru ke sesi dan commit (simpan permanen) ke database
            db.add(new_superadmin)
            db.commit()

            # 3. Tampilkan pesan sukses beserta kredensial default
            print("\n🎉 Berhasil membuat user superadmin default!")
            print("   =======================================")
            print(f"   Username: {new_superadmin.username}")
            print(f"   Password: {password_plain}")
            print("   =======================================")
            print("   Harap segera ganti password setelah login pertama kali.")


# Blok ini memungkinkan file dijalankan sebagai script mandiri
# untuk melakukan seeding data awal.
# Contoh penggunaan di terminal: python -m app.database.seed
if __name__ == '__main__':
    print("Memulai proses seeding data awal...")
    
    # Panggil init_db() terlebih dahulu untuk memastikan semua tabel sudah ada
    print("Memastikan semua tabel sudah dibuat...")
    init_db()
    
    # Jalankan fungsi seeding untuk superadmin
    seed_superadmin()
    
    print("\nProses seeding selesai.")