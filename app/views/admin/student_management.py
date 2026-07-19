# File: app/views/admin/student_management.py
# Berisi widget untuk admin (guru pembina) mengelola data siswa (teller).
#
# --- PENJELASAN ARSITEKTUR ---
# Widget ini sengaja dibuat terpisah dari UserManagementWidget (untuk superadmin)
# untuk menerapkan pemisahan hak akses yang ketat. Admin (guru pembina) hanya
# boleh melihat, membuat, mengedit, dan menonaktifkan user dengan role 'siswa'.
# Mereka tidak boleh melihat atau mengubah data sesama admin atau superadmin.
# Pembatasan ini diimplementasikan di level query database (`.where(User.role == 'siswa')`)
# untuk memastikan tidak ada data sensitif yang bocor ke widget ini.

import bcrypt
from datetime import datetime
from PySide2.QtCore import Qt
from PySide2.QtWidgets import (
    QCheckBox,
    QFrame,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
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
from sqlalchemy.orm import joinedload

# Import komponen database dan model
from app.database.db import SessionLocal
from app.models.models import User


class StudentManagementWidget(QWidget):
    """
    Widget untuk manajemen user dengan role 'siswa' (CRUD).
    Menampilkan daftar siswa dalam tabel dan menyediakan form untuk menambah/mengedit.
    """

    def __init__(self, current_user_id: int):
        super().__init__()
        self.current_user_id = current_user_id
        self.selected_user_id = None  # Menyimpan ID siswa yang sedang dipilih
        self.init_ui()
        self.load_students()

    def init_ui(self):
        """Menginisialisasi semua komponen antarmuka pengguna (UI)."""
        main_layout = QHBoxLayout(self)

        # --- Bagian KIRI: Tabel Siswa ---
        table_group = QGroupBox("Daftar Siswa (Teller)")
        table_layout = QVBoxLayout(table_group)

        self.show_deleted_checkbox = QCheckBox("Tampilkan yang Dihapus")
        filter_layout = QHBoxLayout()
        filter_layout.addStretch()
        filter_layout.addWidget(self.show_deleted_checkbox)
        table_layout.addLayout(filter_layout)

        self.student_table = QTableWidget()
        self.student_table.setColumnCount(9)
        self.student_table.setHorizontalHeaderLabels(
            ["ID", "Username", "Nama Lengkap", "Nomor Induk (NIS)", "Kelas", "Status", "Tanggal Dihapus", "Dihapus Oleh", "Dibuat Oleh"]
        )
        self.student_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.student_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.student_table.setSelectionMode(QTableWidget.SingleSelection)
        self.student_table.verticalHeader().setVisible(False)

        table_layout.addWidget(self.student_table)

        # --- Bagian KANAN: Form Tambah/Edit Siswa ---
        self.form_group = QGroupBox("Tambah Siswa Baru")
        form_layout = QFormLayout(self.form_group)
        form_layout.setLabelAlignment(Qt.AlignRight)

        # Tombol untuk kembali ke mode "Tambah Baru" secara eksplisit, selalu terlihat.
        self.add_new_button = QPushButton("+ Tambah Siswa Baru")
        form_layout.addRow(self.add_new_button)

        # Garis pemisah visual untuk memisahkan tombol dari field input.
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        form_layout.addRow(line)

        self.username_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.nama_lengkap_input = QLineEdit()
        self.nomor_induk_input = QLineEdit()
        self.nomor_induk_input.setPlaceholderText("NIS siswa wajib diisi")
        self.kelas_input = QLineEdit()
        self.is_active_checkbox = QCheckBox("Aktif")

        self.save_button = QPushButton("Tambah Siswa")
        self.delete_button = QPushButton("Hapus Siswa")
        self.restore_button = QPushButton("Aktifkan Kembali")
        self.cancel_button = QPushButton("Batal Edit")

        action_button_layout = QHBoxLayout()
        action_button_layout.addWidget(self.save_button)
        action_button_layout.addWidget(self.delete_button)
        action_button_layout.addWidget(self.restore_button)

        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)

        form_layout.addRow("Username:", self.username_input)
        form_layout.addRow("Password:", self.password_input)
        form_layout.addRow("Nama Lengkap:", self.nama_lengkap_input)
        form_layout.addRow("Nomor Induk (NIS):", self.nomor_induk_input)
        form_layout.addRow("Kelas:", self.kelas_input)
        form_layout.addRow("Status:", self.is_active_checkbox)
        form_layout.addRow(action_button_layout)
        form_layout.addRow(self.cancel_button)
        form_layout.addRow(self.status_label)

        main_layout.addWidget(table_group, 3)
        main_layout.addWidget(self.form_group, 2)

        self.add_new_button.clicked.connect(self.reset_form_state)
        self.show_deleted_checkbox.stateChanged.connect(self.load_students)
        self.student_table.cellClicked.connect(self.handle_table_click)
        self.save_button.clicked.connect(self.handle_save_student)
        self.delete_button.clicked.connect(self.handle_delete_student)
        self.restore_button.clicked.connect(self.handle_restore_student)
        self.cancel_button.clicked.connect(self.reset_form_state)

        self.reset_form_state()

    def load_students(self):
        """Mengambil data siswa dari database dan menampilkannya di tabel."""
        self.student_table.setRowCount(0)

        with SessionLocal() as db:
            # Query dasar SELALU memfilter role='siswa'
            stmt = select(User).where(User.role == 'siswa').options(joinedload(User.creator), joinedload(User.deleter))

            if not self.show_deleted_checkbox.isChecked():
                stmt = stmt.where(User.is_deleted == False)

            stmt = stmt.order_by(User.id)
            students = db.execute(stmt).scalars().all()

            for row, student in enumerate(students):
                self.student_table.insertRow(row)
                self.student_table.setItem(row, 0, QTableWidgetItem(str(student.id)))
                self.student_table.setItem(row, 1, QTableWidgetItem(student.username))
                self.student_table.setItem(row, 2, QTableWidgetItem(student.nama_lengkap))
                self.student_table.setItem(row, 3, QTableWidgetItem(student.nomor_induk or "-"))
                self.student_table.setItem(row, 4, QTableWidgetItem(student.kelas or "-"))

                status_item = QTableWidgetItem()
                if student.is_deleted:
                    status_item.setText("Dihapus")
                    status_item.setForeground(Qt.red)
                else:
                    status_item.setText("Aktif" if student.is_active else "Tidak Aktif")
                status_item.setTextAlignment(Qt.AlignCenter)
                self.student_table.setItem(row, 5, status_item)

                # Kolom 6: Tanggal Dihapus
                deleted_at_str = student.deleted_at.strftime('%d/%m/%Y %H:%M') if student.deleted_at else "-"
                self.student_table.setItem(row, 6, QTableWidgetItem(deleted_at_str))

                # Kolom 7: Dihapus Oleh
                deleter_name = student.deleter.nama_lengkap if student.deleter else "-"
                self.student_table.setItem(row, 7, QTableWidgetItem(deleter_name))

                # Kolom 8: Dibuat Oleh
                creator_name = student.creator.nama_lengkap if student.creator else "Sistem"
                self.student_table.setItem(row, 8, QTableWidgetItem(creator_name))

        self.student_table.resizeColumnsToContents()
        self.student_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.student_table.horizontalHeader().setSectionResizeMode(8, QHeaderView.Stretch)

    def handle_table_click(self, row, column):
        """Mengisi form saat baris tabel diklik (masuk ke mode edit)."""
        user_id_item = self.student_table.item(row, 0)
        if not user_id_item: return

        self.selected_user_id = int(user_id_item.text())

        with SessionLocal() as db:
            student = db.get(User, self.selected_user_id)
            if not student or student.role != 'siswa':
                self.reset_form_state()
                return

            self.username_input.setText(student.username)
            self.username_input.setEnabled(False)
            self.password_input.clear()
            self.password_input.setPlaceholderText("Kosongkan jika tidak ingin diubah")
            self.nama_lengkap_input.setText(student.nama_lengkap)
            self.nomor_induk_input.setText(student.nomor_induk or "")
            self.kelas_input.setText(student.kelas or "")
            self.is_active_checkbox.setChecked(student.is_active)

            if student.is_deleted:
                self.form_group.setTitle("Detail Siswa (Dihapus)")
                self.nama_lengkap_input.setEnabled(False)
                self.password_input.setEnabled(False)
                self.nomor_induk_input.setEnabled(False)
                self.kelas_input.setEnabled(False)
                self.is_active_checkbox.setEnabled(False)
                self.save_button.setEnabled(False)
                self.delete_button.setEnabled(False)
                self.restore_button.setVisible(True)
                self.cancel_button.setVisible(True)
                self.status_label.setText("Siswa ini telah dihapus (read-only).")
            else:
                self.form_group.setTitle("Edit Data Siswa")
                self.nama_lengkap_input.setEnabled(True)
                self.password_input.setEnabled(True)
                self.nomor_induk_input.setEnabled(True)
                self.kelas_input.setEnabled(True)
                self.is_active_checkbox.setEnabled(True)
                self.save_button.setEnabled(True)
                self.save_button.setText("Update Siswa")
                self.delete_button.setEnabled(True)
                self.restore_button.setVisible(False)
                self.cancel_button.setVisible(True)
                self.status_label.setText("")

    def handle_save_student(self):
        """Logika untuk menambah atau mengupdate data siswa."""
        self.status_label.setText("")
        self.status_label.setStyleSheet("")

        nama_lengkap = self.nama_lengkap_input.text().strip()
        password = self.password_input.text()
        nomor_induk = self.nomor_induk_input.text().strip() or None
        kelas = self.kelas_input.text().strip() or None
        is_active = self.is_active_checkbox.isChecked()

        if not all([nama_lengkap, nomor_induk]):
            self.status_label.setText("Nama Lengkap dan Nomor Induk (NIS) wajib diisi.")
            self.status_label.setStyleSheet("color: red;")
            return

        with SessionLocal() as db:
            # Validasi keunikan nomor induk (global)
            stmt_nis = select(User).where(User.nomor_induk == nomor_induk)
            if self.selected_user_id:
                stmt_nis = stmt_nis.where(User.id != self.selected_user_id)
            
            existing_user_by_nis = db.execute(stmt_nis).scalars().first()
            if existing_user_by_nis:
                # Jika mode tambah baru dan NIS ditemukan pada user yang sudah dihapus, beri pesan khusus.
                if self.selected_user_id is None and existing_user_by_nis.is_deleted:
                    self.status_label.setText(
                        "NIS ini pernah dipakai oleh siswa yang sudah dihapus.\n"
                        "Centang 'Tampilkan yang Dihapus' dan aktifkan kembali akun tersebut."
                    )
                else:
                    self.status_label.setText("Nomor Induk (NIS) sudah digunakan oleh user lain.")
                self.status_label.setStyleSheet("color: red;")
                return

            # --- MODE UPDATE ---
            if self.selected_user_id:
                student_to_update = db.get(User, self.selected_user_id)
                if not student_to_update:
                    self.status_label.setText("Siswa tidak ditemukan untuk diupdate.")
                    return

                student_to_update.nama_lengkap = nama_lengkap
                student_to_update.nomor_induk = nomor_induk
                student_to_update.kelas = kelas
                student_to_update.is_active = is_active

                if password:
                    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                    student_to_update.password_hash = hashed_password

                db.commit()
                self.status_label.setText(f"Data siswa '{student_to_update.username}' berhasil diupdate.")
                self.status_label.setStyleSheet("color: green;")

            # --- MODE TAMBAH BARU ---
            else:
                username = self.username_input.text().strip()
                if not all([username, password]):
                    self.status_label.setText("Username dan Password wajib diisi untuk siswa baru.")
                    return

                # Validasi keunikan username
                existing_user_by_username = db.execute(select(User).where(User.username == username)).scalars().first()
                if existing_user_by_username:
                    if existing_user_by_username.is_deleted:
                        self.status_label.setText(
                            "Username ini pernah dipakai oleh siswa yang sudah dihapus.\n"
                            "Centang 'Tampilkan yang Dihapus' dan aktifkan kembali akun tersebut."
                        )
                    else:
                        self.status_label.setText("Username sudah digunakan.")
                    
                    self.status_label.setStyleSheet("color: red;")
                    return

                hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                new_student = User(
                    username=username,
                    password_hash=hashed_password,
                    nama_lengkap=nama_lengkap,
                    role='siswa',  # Hardcoded
                    nomor_induk=nomor_induk,
                    kelas=kelas,
                    is_active=True,
                    created_by=self.current_user_id
                )
                db.add(new_student)
                db.commit()
                self.status_label.setText(f"Siswa '{username}' berhasil ditambahkan.")
                self.status_label.setStyleSheet("color: green;")

            self.load_students()
            self.reset_form_state()

    def handle_delete_student(self):
        """Logika untuk soft-delete siswa yang dipilih."""
        if self.selected_user_id is None:
            return

        with SessionLocal() as db:
            student_to_delete = db.get(User, self.selected_user_id)
            if not student_to_delete:
                self.reset_form_state()
                return

            reply = QMessageBox.question(
                self, "Konfirmasi Hapus Siswa",
                f"Apakah Anda yakin ingin menghapus siswa '{student_to_delete.nama_lengkap}' dari daftar aktif?\n\n"
                "Data akan disembunyikan, namun riwayat transaksi dan data terkait lainnya akan tetap tersimpan untuk keperluan audit.",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                try:
                    student_to_delete.is_deleted = True
                    student_to_delete.deleted_at = datetime.now()
                    student_to_delete.deleted_by = self.current_user_id
                    student_to_delete.is_active = False

                    db.commit()

                    self.status_label.setText(f"Siswa '{student_to_delete.username}' berhasil dihapus.")
                    self.status_label.setStyleSheet("color: green;")
                    self.load_students()
                    self.reset_form_state()
                except Exception as e:
                    db.rollback()
                    QMessageBox.critical(self, "Error Database", f"Terjadi kesalahan saat menghapus siswa.\n\nError: {e}")

    def handle_restore_student(self):
        """Logika untuk mengaktifkan kembali siswa yang sudah di-soft-delete."""
        if self.selected_user_id is None:
            return

        with SessionLocal() as db:
            student_to_restore = db.get(User, self.selected_user_id)
            if not student_to_restore:
                self.reset_form_state()
                return

            reply = QMessageBox.question(
                self, "Konfirmasi Aktifkan Kembali",
                f"Aktifkan kembali siswa '{student_to_restore.nama_lengkap}'? Username dan Nomor Induk akan bisa digunakan lagi.",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                try:
                    student_to_restore.is_deleted = False
                    student_to_restore.deleted_at = None
                    student_to_restore.deleted_by = None
                    student_to_restore.is_active = True
                    db.commit()
                    self.status_label.setText(f"Siswa '{student_to_restore.username}' berhasil diaktifkan kembali.")
                    self.status_label.setStyleSheet("color: green;")
                    self.load_students()
                    self.reset_form_state()
                except Exception as e:
                    db.rollback()
                    QMessageBox.critical(self, "Error Database", f"Terjadi kesalahan saat mengaktifkan siswa.\n\nError: {e}")

    def reset_form_state(self):
        """Mengembalikan form ke state awal (mode tambah baru)."""
        self.student_table.clearSelection()
        self.selected_user_id = None

        self.username_input.clear()
        self.password_input.clear()
        self.nama_lengkap_input.clear()
        self.nomor_induk_input.clear()
        self.kelas_input.clear()

        self.is_active_checkbox.setChecked(True)
        self.status_label.setText("")

        self.form_group.setTitle("Tambah Siswa Baru")
        self.username_input.setEnabled(True)
        self.nama_lengkap_input.setEnabled(True)
        self.password_input.setEnabled(True)
        self.nomor_induk_input.setEnabled(True)
        self.kelas_input.setEnabled(True)
        self.is_active_checkbox.setEnabled(True)
        self.password_input.setPlaceholderText("")
        self.save_button.setText("Tambah Siswa")
        self.save_button.setEnabled(True)
        self.delete_button.setEnabled(False)
        self.restore_button.setVisible(False)
        self.cancel_button.setVisible(False)