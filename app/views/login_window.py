import sys
from datetime import datetime

import bcrypt
from PySide2.QtCore import Qt, Signal
from PySide2.QtGui import QFont
from PySide2.QtWidgets import (
    QApplication,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy import select

# Import komponen database dan model dari modul lain
from app.database.db import SessionLocal
from app.models.models import LoginLog, User


class LoginWindow(QWidget):
    """
    Widget untuk window login.
    Meng-handle input username/password, verifikasi ke database,
    dan mengirimkan signal jika login berhasil.
    """
    # Definisikan custom signal yang akan dikirim saat login berhasil.
    # Signal ini akan membawa sebuah dictionary berisi data user yang login.
    login_success = Signal(dict)

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        """Menginisialisasi semua komponen antarmuka pengguna (UI)."""
        # --- Konfigurasi Window ---
        self.setWindowTitle("Bank Mini SMK")
        self.setFixedSize(400, 350)  # Ukuran window dibuat tetap agar rapi

        # --- Membuat Widget ---
        # 1. Judul
        title_label = QLabel("Bank Mini SMK - Login")
        font = QFont()
        font.setPointSize(16)
        font.setBold(True)
        title_label.setFont(font)
        title_label.setAlignment(Qt.AlignCenter)

        # 2. Input field
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")
        self.username_input.setMinimumWidth(250)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.Password)  # Sembunyikan teks password
        self.password_input.setMinimumWidth(250)

        # 3. Tombol Login
        self.login_button = QPushButton("Login")
        self.login_button.setMinimumWidth(250)

        # 4. Label untuk pesan error
        self.error_label = QLabel("")
        self.error_label.setAlignment(Qt.AlignCenter)
        # Atur warna teks error menjadi merah
        self.error_label.setStyleSheet("color: red;")

        # --- Membuat Layout ---
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)  # Pusatkan semua widget di tengah
        layout.setSpacing(15)  # Beri jarak antar widget

        # Menambahkan widget ke layout
        layout.addWidget(title_label)
        layout.addWidget(self.username_input)
        layout.addWidget(self.password_input)
        layout.addWidget(self.login_button)
        layout.addWidget(self.error_label)

        self.setLayout(layout)

        # --- Menghubungkan Signal dan Slot ---
        # Hubungkan tombol login ke fungsi handle_login
        self.login_button.clicked.connect(self.handle_login)
        # Hubungkan event 'returnPressed' (Enter) di input field ke fungsi handle_login
        self.username_input.returnPressed.connect(self.handle_login)
        self.password_input.returnPressed.connect(self.handle_login)

    def handle_login(self):
        """
        Fungsi yang dijalankan saat tombol 'Login' diklik.
        Mengambil data, memvalidasi, dan melakukan verifikasi ke database.
        """
        # Reset pesan error setiap kali tombol ditekan
        self.error_label.setText("")

        # 1. Ambil input dari QLineEdit
        username = self.username_input.text().strip()
        password = self.password_input.text()

        # 2. Validasi input dasar
        if not username or not password:
            self.error_label.setText("Username dan password harus diisi.")
            return

        # 3. Proses verifikasi ke database
        with SessionLocal() as db:
            try:
                # Cari user berdasarkan username
                stmt = select(User).where(User.username == username)
                user = db.execute(stmt).scalars().first()

                # Jika user tidak ditemukan atau password salah, beri pesan yang sama
                # untuk alasan keamanan (tidak membocorkan username mana yang valid).
                if not user or not bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
                    self.error_label.setText("Username atau password salah.")
                    return

                # Jika user ditemukan tapi tidak aktif
                if not user.is_active:
                    self.error_label.setText("Akun tidak aktif, hubungi admin.")
                    return

                # --- LOGIN BERHASIL ---
                print(f"Login berhasil untuk user: {user.username}")

                # a. Buat record baru di LoginLog
                new_log = LoginLog(user_id=user.id, login_time=datetime.now())
                db.add(new_log)
                db.commit()
                db.refresh(new_log)  # Refresh untuk mendapatkan ID jika perlu

                # b. Siapkan data user untuk dikirim via signal
                user_data = {
                    'id': user.id,
                    'username': user.username,
                    'role': user.role,
                    'nama_lengkap': user.nama_lengkap,
                    'login_log_id': new_log.id  # Kirim juga ID log login
                }

                # c. Emit signal 'login_success' dengan data user
                self.login_success.emit(user_data)

                # d. Tutup window login
                self.close()

            except Exception as e:
                # Tangani error database atau lainnya
                print(f"Terjadi error saat login: {e}")
                self.error_label.setText("Terjadi kesalahan pada sistem.")