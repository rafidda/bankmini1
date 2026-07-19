# File: app/views/shared/change_password.py

import bcrypt
from typing import Optional

from PySide2.QtCore import Qt
from PySide2.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

# Import komponen database dan model
from app.database.db import SessionLocal
from app.models.models import User


class ChangePasswordDialog(QDialog):
    """
    Dialog popup untuk memungkinkan user yang sedang login mengubah password mereka.
    """

    def __init__(self, current_user_id: int, parent: Optional[QWidget] = None):
        """
        Constructor.
        :param current_user_id: ID dari user yang sedang login.
        :param parent: Widget induk dari dialog ini.
        """
        super().__init__(parent)
        self.current_user_id = current_user_id
        self.init_ui()

    def init_ui(self):
        """Menginisialisasi semua komponen antarmuka pengguna (UI) untuk dialog."""
        # --- Konfigurasi Dialog ---
        self.setWindowTitle("Ubah Password")
        self.setModal(True)  # Membuat dialog ini modal (memblokir window utama)
        self.setMinimumWidth(400)

        # --- Layout Utama ---
        main_layout = QVBoxLayout(self)

        # --- Form Input ---
        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignRight)

        self.old_password_input = QLineEdit()
        self.old_password_input.setEchoMode(QLineEdit.Password)

        self.new_password_input = QLineEdit()
        self.new_password_input.setEchoMode(QLineEdit.Password)

        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setEchoMode(QLineEdit.Password)

        form_layout.addRow("Password Lama:", self.old_password_input)
        form_layout.addRow("Password Baru:", self.new_password_input)
        form_layout.addRow("Konfirmasi Password Baru:", self.confirm_password_input)

        # --- Label Status/Error ---
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: red;")

        # --- Tombol Aksi ---
        button_layout = QHBoxLayout()
        self.save_button = QPushButton("Simpan")
        self.cancel_button = QPushButton("Batal")
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.save_button)

        # --- Gabungkan semua ke layout utama ---
        main_layout.addLayout(form_layout)
        main_layout.addWidget(self.status_label)
        main_layout.addLayout(button_layout)

        # --- Hubungkan Signal ke Slot ---
        self.save_button.clicked.connect(self.handle_change_password)
        self.cancel_button.clicked.connect(self.reject)  # self.reject() adalah slot bawaan QDialog untuk menutup

    def handle_change_password(self):
        """
        Memvalidasi input dan memproses perubahan password ke database.
        """
        # Reset label status
        self.status_label.setText("")

        # Ambil semua input dari form
        old_password = self.old_password_input.text()
        new_password = self.new_password_input.text()
        confirm_password = self.confirm_password_input.text()

        # 1. Validasi field kosong
        if not all([old_password, new_password, confirm_password]):
            self.status_label.setText("Semua field harus diisi.")
            return

        # 2. Validasi konfirmasi password baru
        if new_password != confirm_password:
            self.status_label.setText("Konfirmasi password tidak cocok.")
            return

        # 3. Validasi panjang password baru
        if len(new_password) < 6:
            self.status_label.setText("Password baru minimal 6 karakter.")
            return

        # Proses interaksi dengan database
        with SessionLocal() as db:
            try:
                # Ambil data user yang sedang login
                user = db.get(User, self.current_user_id)
                if not user:
                    self.status_label.setText("Error: User tidak ditemukan.")
                    return

                # 4. Validasi password lama
                if not bcrypt.checkpw(old_password.encode('utf-8'), user.password_hash.encode('utf-8')):
                    self.status_label.setText("Password lama salah.")
                    return

                # 5. Validasi password baru tidak boleh sama dengan yang lama
                if bcrypt.checkpw(new_password.encode('utf-8'), user.password_hash.encode('utf-8')):
                    self.status_label.setText("Password baru tidak boleh sama dengan password lama.")
                    return

                # --- Semua validasi lolos, proses update ---
                # Hash password baru
                hashed_new_password = bcrypt.hashpw(
                    new_password.encode('utf-8'), bcrypt.gensalt()
                ).decode('utf-8')

                # Update hash di objek user dan commit ke database
                user.password_hash = hashed_new_password
                db.commit()

                # Tampilkan pesan sukses dan tutup dialog
                QMessageBox.information(self, "Sukses", "Password Anda telah berhasil diubah.")
                self.accept()  # Menutup dialog dengan status 'Accepted'

            except Exception as e:
                db.rollback()
                print(f"Error saat mengubah password: {e}")
                self.status_label.setText("Terjadi kesalahan pada sistem. Coba lagi nanti.")