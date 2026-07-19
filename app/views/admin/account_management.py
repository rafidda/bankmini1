import locale
from datetime import datetime
from decimal import Decimal
from PySide2.QtCore import Qt
from PySide2.QtGui import QDoubleValidator
from PySide2.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QCheckBox,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy import select

# Import komponen database dan model
from app.database.db import SessionLocal
from app.models.models import Account

# Atur locale ke Indonesia untuk format mata uang Rupiah
try:
    locale.setlocale(locale.LC_ALL, 'id_ID.UTF-8')
except locale.Error:
    locale.setlocale(locale.LC_ALL, 'Indonesian_indonesia.1252')


class AccountManagementWidget(QWidget):
    """
    Widget untuk manajemen rekening nasabah (CRUD).
    Menampilkan daftar rekening dan menyediakan form untuk menambah/mengedit.
    """

    def __init__(self, current_user_id: int):
        super().__init__()
        self.current_user_id = current_user_id  # ID user admin/siswa yang login
        self.selected_account_id = None  # ID rekening yang sedang dipilih
        self.init_ui()
        self.load_accounts()

    def init_ui(self):
        """Menginisialisasi semua komponen antarmuka pengguna (UI)."""
        main_layout = QHBoxLayout(self)

        # --- Bagian KIRI: Tabel Rekening ---
        table_group = QGroupBox("Daftar Rekening Nasabah")
        table_layout = QVBoxLayout(table_group)

        # Checkbox untuk menampilkan yang dihapus
        self.show_deleted_checkbox = QCheckBox("Tampilkan yang Dihapus")
        filter_layout = QHBoxLayout()
        filter_layout.addStretch()
        filter_layout.addWidget(self.show_deleted_checkbox)
        table_layout.addLayout(filter_layout)

        self.account_table = QTableWidget()
        self.account_table.setColumnCount(8)
        self.account_table.setHorizontalHeaderLabels(
            ["ID", "No. Rekening", "Nama Nasabah", "NIS Nasabah", "Kelas", "Saldo", "Status", "Tgl Dibuat"]
        )
        self.account_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.account_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.account_table.setSelectionMode(QTableWidget.SingleSelection)
        self.account_table.verticalHeader().setVisible(False)
        table_layout.addWidget(self.account_table)

        # --- Bagian KANAN: Form Tambah/Edit Rekening ---
        self.form_group = QGroupBox("Tambah Rekening Baru")
        form_layout = QFormLayout(self.form_group)
        form_layout.setLabelAlignment(Qt.AlignRight)

        self.nomor_rekening_input = QLineEdit()
        self.nama_nasabah_input = QLineEdit()
        self.nis_nasabah_input = QLineEdit()
        self.kelas_nasabah_input = QLineEdit()

        # Field Saldo Awal dengan validator angka
        self.saldo_awal_label = QLabel("Saldo Awal:")
        self.saldo_awal_input = QLineEdit()
        self.saldo_awal_input.setValidator(QDoubleValidator(0, 1000000000, 2))
        self.saldo_awal_input.setText("0")

        # Tombol-tombol aksi
        self.save_button = QPushButton("Tambah Rekening")
        self.delete_button = QPushButton("Tutup Rekening")
        self.cancel_button = QPushButton("Batal Edit")
        action_button_layout = QHBoxLayout()
        action_button_layout.addWidget(self.save_button)
        action_button_layout.addWidget(self.delete_button)

        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)

        form_layout.addRow("Nomor Rekening:", self.nomor_rekening_input)
        form_layout.addRow("Nama Nasabah:", self.nama_nasabah_input)
        form_layout.addRow("NIS Nasabah:", self.nis_nasabah_input)
        form_layout.addRow("Kelas Nasabah:", self.kelas_nasabah_input)
        form_layout.addRow(self.saldo_awal_label, self.saldo_awal_input)
        form_layout.addRow(action_button_layout)
        form_layout.addRow(self.cancel_button)
        form_layout.addRow(self.status_label)

        main_layout.addWidget(table_group, 3)
        main_layout.addWidget(self.form_group, 2)

        # --- Hubungkan Signal ke Slot ---
        self.show_deleted_checkbox.stateChanged.connect(self.load_accounts)
        self.account_table.cellClicked.connect(self.handle_table_click)
        self.save_button.clicked.connect(self.handle_save_account)
        self.delete_button.clicked.connect(self.handle_delete_account)
        self.cancel_button.clicked.connect(self.reset_form_state)

        self.reset_form_state()

    def load_accounts(self):
        """Mengambil data rekening dari database dan menampilkannya di tabel."""
        self.account_table.setRowCount(0)
        with SessionLocal() as db:
            stmt = select(Account)

            # Filter berdasarkan status soft-delete jika checkbox tidak dicentang
            if not self.show_deleted_checkbox.isChecked():
                stmt = stmt.where(Account.is_deleted == False)

            accounts = db.execute(stmt.order_by(Account.id.desc())).scalars().all()
            for row, acc in enumerate(accounts):
                self.account_table.insertRow(row)
                self.account_table.setItem(row, 0, QTableWidgetItem(str(acc.id)))
                self.account_table.setItem(row, 1, QTableWidgetItem(acc.nomor_rekening))
                self.account_table.setItem(row, 2, QTableWidgetItem(acc.nama_nasabah))
                self.account_table.setItem(row, 3, QTableWidgetItem(acc.nis_nasabah or "-"))
                self.account_table.setItem(row, 4, QTableWidgetItem(acc.kelas_nasabah))
                # Format saldo sebagai mata uang
                saldo_str = locale.currency(acc.saldo, grouping=True, symbol='Rp ')
                self.account_table.setItem(row, 5, QTableWidgetItem(saldo_str))

                # Kolom 6: Status (Aktif/Dihapus)
                status_item = QTableWidgetItem()
                if acc.is_deleted:
                    status_item.setText("Dihapus")
                    status_item.setForeground(Qt.red)
                else:
                    status_item.setText("Aktif")
                self.account_table.setItem(row, 6, status_item)

                # Format tanggal
                tgl_dibuat_str = acc.created_at.strftime('%d-%m-%Y %H:%M')
                self.account_table.setItem(row, 7, QTableWidgetItem(tgl_dibuat_str))

        self.account_table.resizeColumnsToContents()
        self.account_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)

    def handle_table_click(self, row, column):
        """Mengisi form saat baris tabel diklik (masuk ke mode edit)."""
        self.selected_account_id = int(self.account_table.item(row, 0).text())
        with SessionLocal() as db:
            acc = db.get(Account, self.selected_account_id)
            if not acc:
                self.reset_form_state()
                return

            self.nomor_rekening_input.setText(acc.nomor_rekening)
            self.nama_nasabah_input.setText(acc.nama_nasabah)
            self.nis_nasabah_input.setText(acc.nis_nasabah or "")
            self.kelas_nasabah_input.setText(acc.kelas_nasabah)

            # Jika rekening sudah di-soft-delete, buat form read-only
            if acc.is_deleted:
                self.form_group.setTitle("Detail Rekening (Dihapus)")
                self.nomor_rekening_input.setEnabled(False)
                self.nama_nasabah_input.setEnabled(False)
                self.nis_nasabah_input.setEnabled(False)
                self.kelas_nasabah_input.setEnabled(False)
                self.save_button.setEnabled(False)
                self.delete_button.setEnabled(False) # Tidak bisa dihapus lagi
                self.cancel_button.setVisible(True)
                self.status_label.setText("Rekening ini telah dihapus (read-only).")
            else:
                # Jika rekening aktif, UI normal untuk mode edit
                self.form_group.setTitle("Edit Rekening")
                self.nomor_rekening_input.setEnabled(True)
                self.nama_nasabah_input.setEnabled(True)
                self.nis_nasabah_input.setEnabled(True)
                self.kelas_nasabah_input.setEnabled(True)
                self.save_button.setEnabled(True)
                self.save_button.setText("Update Rekening")
                self.delete_button.setEnabled(True)
                self.cancel_button.setVisible(True)
                self.status_label.setText("")

            self.saldo_awal_label.setVisible(False) # Saldo awal selalu disembunyikan saat edit
            self.saldo_awal_input.setVisible(False)

    def handle_save_account(self):
        """Logika untuk menambah atau mengupdate rekening, tergantung state."""
        self.status_label.setText("")
        nomor_rekening = self.nomor_rekening_input.text().strip()
        nama_nasabah = self.nama_nasabah_input.text().strip()
        nis_nasabah = self.nis_nasabah_input.text().strip() or None
        kelas_nasabah = self.kelas_nasabah_input.text().strip()

        if not all([nomor_rekening, nama_nasabah, kelas_nasabah]):
            self.status_label.setText("Semua field harus diisi.")
            self.status_label.setStyleSheet("color: red;")
            return

        with SessionLocal() as db:
            # Cek duplikasi nomor rekening
            stmt = select(Account).where(Account.nomor_rekening == nomor_rekening)
            if self.selected_account_id:  # Jika mode edit, kecualikan diri sendiri
                stmt = stmt.where(Account.id != self.selected_account_id)
            if db.execute(stmt).first():
                self.status_label.setText("Nomor rekening sudah digunakan.")
                self.status_label.setStyleSheet("color: red;")
                return

            # --- MODE UPDATE ---
            if self.selected_account_id:
                acc_to_update = db.get(Account, self.selected_account_id)
                acc_to_update.nomor_rekening = nomor_rekening
                acc_to_update.nama_nasabah = nama_nasabah
                acc_to_update.nis_nasabah = nis_nasabah
                acc_to_update.kelas_nasabah = kelas_nasabah
                db.commit()
                self.status_label.setText("Data rekening berhasil diupdate.")
            # --- MODE TAMBAH BARU ---
            else:
                saldo_awal_str = self.saldo_awal_input.text().replace(',', '.')
                saldo_awal = float(saldo_awal_str) if saldo_awal_str else 0.0
                if saldo_awal < 0:
                    self.status_label.setText("Saldo awal tidak boleh negatif.")
                    self.status_label.setStyleSheet("color: red;")
                    return

                new_account = Account(
                    nomor_rekening=nomor_rekening, nama_nasabah=nama_nasabah,
                    nis_nasabah=nis_nasabah, kelas_nasabah=kelas_nasabah, saldo=saldo_awal,
                    created_by=self.current_user_id
                )
                db.add(new_account)
                db.commit()
                self.status_label.setText("Rekening baru berhasil ditambahkan.")

            self.status_label.setStyleSheet("color: green;")
            self.load_accounts()
            self.reset_form_state()

    def handle_delete_account(self):
        """Logika untuk menutup rekening yang dipilih (soft-delete), dengan validasi saldo."""
        if self.selected_account_id is None: return

        with SessionLocal() as db:
            # Ambil data terbaru dari DB untuk validasi
            acc_to_close = db.get(Account, self.selected_account_id)
            if not acc_to_close:
                self.reset_form_state()
                return

            # VALIDASI BARU: Saldo harus 0 sebelum rekening bisa ditutup.
            # Saldo dari model adalah tipe Decimal.
            if acc_to_close.saldo != Decimal('0'):
                saldo_str = locale.currency(acc_to_close.saldo, grouping=True, symbol='Rp ')
                QMessageBox.warning(self, "Tutup Rekening Ditolak",
                                     f"Rekening ini masih memiliki saldo {saldo_str}.\n\n"
                                     "Saldo harus 0 sebelum rekening bisa ditutup. Silakan proses Tarik "
                                     "Tunai atau Transfer terlebih dahulu untuk mengosongkan saldo rekening ini.")
                return

            # Konfirmasi untuk soft-delete (tutup rekening)
            reply = QMessageBox.question(self, "Konfirmasi Tutup Rekening",
                f"Yakin ingin MENUTUP rekening '{acc_to_close.nomor_rekening}' - {acc_to_close.nama_nasabah}?\n\n"
                "Rekening yang sudah ditutup tidak dapat digunakan lagi, namun riwayatnya tetap tersimpan untuk keperluan audit.",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

            if reply == QMessageBox.Yes:
                try:
                    # Lakukan soft-delete
                    acc_to_close.is_deleted = True
                    acc_to_close.deleted_at = datetime.now()
                    acc_to_close.deleted_by = self.current_user_id
                    db.commit()
                    self.status_label.setText(f"Rekening '{acc_to_close.nomor_rekening}' berhasil ditutup.")
                    self.status_label.setStyleSheet("color: green;")
                    self.load_accounts()
                    self.reset_form_state()
                except Exception as e:
                    db.rollback()
                    QMessageBox.critical(self, "Error Database", f"Gagal menutup rekening.\n\nError: {e}")

    def reset_form_state(self):
        """Mengembalikan form ke state awal (mode tambah baru)."""
        self.account_table.clearSelection()
        self.selected_account_id = None

        self.nomor_rekening_input.clear()
        self.nama_nasabah_input.clear()
        self.nis_nasabah_input.clear()
        self.kelas_nasabah_input.clear()
        self.saldo_awal_input.setText("0")
        self.status_label.setText("")

        # Tampilkan kembali field saldo awal
        self.saldo_awal_label.setVisible(True)
        self.saldo_awal_input.setVisible(True)

        # Atur ulang UI ke mode tambah
        self.form_group.setTitle("Tambah Rekening Baru")
        self.save_button.setText("Tambah Rekening")
        self.save_button.setEnabled(True)
        self.delete_button.setEnabled(False)
        self.cancel_button.setVisible(False)

        # Pastikan semua field input aktif kembali
        self.nomor_rekening_input.setEnabled(True)
        self.nama_nasabah_input.setEnabled(True)
        self.nis_nasabah_input.setEnabled(True)
        self.kelas_nasabah_input.setEnabled(True)