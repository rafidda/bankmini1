# File: app/views/siswa/account_create.py
# Berisi widget untuk siswa (teller) membuka rekening nasabah baru.
#
# --- PENJELASAN ARSITEKTUR ---
# Widget ini sengaja dibuat sangat sederhana dan terbatas (create-only).
# Siswa hanya diberi wewenang untuk membuka rekening baru.
# Semua tindakan lain seperti mengedit data nasabah, melihat daftar lengkap rekening,
# atau menutup rekening, adalah wewenang Admin (guru pembina) atau Superadmin
# yang dilakukan melalui AccountManagementWidget.
# Pembatasan ini penting untuk menjaga kontrol dan keamanan data nasabah.

import locale
from decimal import Decimal, InvalidOperation
from typing import Optional

from PySide2.QtCore import Qt
from PySide2.QtGui import QDoubleValidator
from PySide2.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy import select

# Import komponen database dan model
from app.database.db import SessionLocal
from app.models.models import Account
# Import generator nomor rekening otomatis
from app.controllers.account_utils import generate_nomor_rekening

# Atur locale ke Indonesia untuk format mata uang Rupiah
try:
    locale.setlocale(locale.LC_ALL, 'id_ID.UTF-8')
except locale.Error:
    locale.setlocale(locale.LC_ALL, 'Indonesian_indonesia.1252')


class AccountCreateWidget(QWidget):
    """
    Widget sederhana untuk siswa membuat rekening nasabah baru.
    Hanya menyediakan fungsionalitas 'create'.
    """

    def __init__(self, current_user_id: int, parent: Optional[QWidget] = None):
        """
        Constructor.
        :param current_user_id: ID dari user siswa yang sedang login.
        :param parent: Widget induk.
        """
        super().__init__(parent)
        self.current_user_id = current_user_id
        self.init_ui()

    def init_ui(self):
        """Menginisialisasi semua komponen antarmuka pengguna (UI)."""
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignTop)

        # --- Grup Form Utama ---
        form_group = QGroupBox("Buka Rekening Nasabah Baru")
        form_layout = QFormLayout(form_group)
        form_layout.setLabelAlignment(Qt.AlignRight)

        # --- Field Input ---
        self.nama_nasabah_input = QLineEdit()
        self.nis_nasabah_input = QLineEdit()
        self.nis_nasabah_input.setPlaceholderText("Opsional")
        self.kelas_nasabah_input = QLineEdit()

        # --- Tombol Aksi dan Label Status ---
        self.create_button = QPushButton("Buka Rekening")
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)

        # --- Menambahkan widget ke form layout ---
        form_layout.addRow("Nama Nasabah:", self.nama_nasabah_input)
        form_layout.addRow("NIS Nasabah:", self.nis_nasabah_input)
        form_layout.addRow("Kelas Nasabah:", self.kelas_nasabah_input)
        form_layout.addRow(self.create_button)
        form_layout.addRow(self.status_label)

        main_layout.addWidget(form_group)

        # --- Hubungkan Signal ke Slot ---
        self.create_button.clicked.connect(self.handle_buka_rekening)

    def handle_buka_rekening(self):
        """
        Memvalidasi input dan memproses pembuatan rekening baru ke database.
        """
        self.status_label.setText("")
        self.status_label.setStyleSheet("")

        # Ambil semua input dari form
        nama_nasabah = self.nama_nasabah_input.text().strip()
        nis_nasabah = self.nis_nasabah_input.text().strip() or None
        kelas_nasabah = self.kelas_nasabah_input.text().strip()

        # 1. Validasi field wajib
        if not all([nama_nasabah, kelas_nasabah]):
            self.status_label.setText("Nama dan Kelas Nasabah wajib diisi.")
            self.status_label.setStyleSheet("color: red;")
            return

        # 2. Validasi ke database
        with SessionLocal() as db:
            try:
                # Generate nomor rekening baru secara otomatis
                nomor_rekening_baru = generate_nomor_rekening(db)

                # --- Semua validasi lolos, proses pembuatan rekening ---
                new_account = Account(
                    nomor_rekening=nomor_rekening_baru, nama_nasabah=nama_nasabah,
                    nis_nasabah=nis_nasabah, kelas_nasabah=kelas_nasabah,
                    saldo=Decimal('0'), created_by=self.current_user_id
                )
                db.add(new_account)
                db.commit()

                # Tampilkan pesan sukses dengan nomor rekening yang baru dibuat
                QMessageBox.information(
                    self, "Buka Rekening Berhasil",
                    f"Rekening baru berhasil dibuka:\n\n"
                    f"<b>Nomor Rekening: {nomor_rekening_baru}</b>\n\n"
                    f"Nama Nasabah: {nama_nasabah}\n"
                    f"Saldo saat ini: Rp 0. Silakan proses Setor Tunai di tab Transaksi untuk mengisi saldo rekening ini."
                )
                self._reset_form()

            except Exception as e:
                db.rollback()
                QMessageBox.critical(self, "Error Database", f"Gagal membuka rekening baru.\n\nError: {e}")

    def _reset_form(self):
        """Mengosongkan semua field input di form."""
        self.nama_nasabah_input.clear()
        self.nis_nasabah_input.clear()
        self.kelas_nasabah_input.clear()
        self.status_label.setText("")