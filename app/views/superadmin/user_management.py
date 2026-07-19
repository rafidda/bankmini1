import bcrypt
from datetime import datetime
from PySide2.QtCore import Qt
from PySide2.QtWidgets import (
    QCheckBox,
    QComboBox,
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
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

# Import komponen database dan model
from app.database.db import SessionLocal
from app.models.models import LoginLog, User


class UserManagementWidget(QWidget):
    """
    Widget untuk manajemen user (CRUD).
    Menampilkan daftar user dalam tabel dan menyediakan form untuk menambah user baru.
    """

    def __init__(self, current_user_id: int):
        super().__init__()
        self.current_user_id = current_user_id
        self.selected_user_id = None  # Menyimpan ID user yang sedang dipilih untuk diedit/dihapus
        self.init_ui()
        # Muat data user saat widget pertama kali dibuat
        self.load_users()


    def init_ui(self):
        """Menginisialisasi semua komponen antarmuka pengguna (UI)."""
        # --- Layout Utama ---
        main_layout = QHBoxLayout(self)

        # --- Bagian KIRI: Tabel User ---
        table_group = QGroupBox("Daftar User")
        table_layout = QVBoxLayout(table_group)

        # Checkbox untuk menampilkan user yang sudah dihapus (soft-delete)
        self.show_deleted_checkbox = QCheckBox("Tampilkan yang Dihapus")
        filter_layout = QHBoxLayout()
        filter_layout.addStretch()
        filter_layout.addWidget(self.show_deleted_checkbox)
        table_layout.addLayout(filter_layout)

        self.user_table = QTableWidget()
        self.user_table.setColumnCount(10)
        self.user_table.setHorizontalHeaderLabels(
            ["ID", "Username", "Nama Lengkap", "Role", "Nomor Induk", "Kelas", "Status", "Tanggal Dihapus", "Dihapus Oleh", "Dibuat Oleh"]
        )
        # Membuat tabel tidak bisa diedit langsung
        self.user_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.user_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.user_table.setSelectionMode(QTableWidget.SingleSelection)
        self.user_table.verticalHeader().setVisible(False)

        table_layout.addWidget(self.user_table)

        # --- Bagian KANAN: Form Tambah/Edit User ---
        self.form_group = QGroupBox("Tambah User Baru")
        # QFormLayout ideal untuk membuat form input
        form_layout = QFormLayout(self.form_group)
        form_layout.setLabelAlignment(Qt.AlignRight)

        # Tombol untuk kembali ke mode "Tambah Baru" secara eksplisit
        self.add_new_button = QPushButton("+ Tambah User Baru")
        form_layout.addRow(self.add_new_button)

        # Garis pemisah visual
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        form_layout.addRow(line)

        self.username_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.nama_lengkap_input = QLineEdit()
        self.role_combo = QComboBox()
        self.role_combo.addItems(["admin", "siswa", "superadmin"])
        self.nomor_induk_input = QLineEdit()
        self.nomor_induk_input.setPlaceholderText("NIP untuk admin, NIS untuk siswa")
        self.kelas_input = QLineEdit()
        self.kelas_input.setPlaceholderText("Kosongkan jika bukan siswa")
        self.is_active_checkbox = QCheckBox("Aktif")

        # Tombol-tombol aksi
        self.save_button = QPushButton("Tambah User")
        self.delete_button = QPushButton("Hapus User")
        self.restore_button = QPushButton("Aktifkan Kembali")
        self.cancel_button = QPushButton("Batal Edit")

        # Layout untuk tombol simpan dan hapus
        action_button_layout = QHBoxLayout()
        action_button_layout.addWidget(self.save_button)
        action_button_layout.addWidget(self.delete_button)
        action_button_layout.addWidget(self.restore_button)

        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)

        form_layout.addRow("Username:", self.username_input)
        form_layout.addRow("Password:", self.password_input)
        form_layout.addRow("Nama Lengkap:", self.nama_lengkap_input)
        form_layout.addRow("Role:", self.role_combo)
        form_layout.addRow("Nomor Induk (NIP/NIS):", self.nomor_induk_input)
        form_layout.addRow("Kelas:", self.kelas_input)
        form_layout.addRow("Status:", self.is_active_checkbox)
        form_layout.addRow(action_button_layout)
        form_layout.addRow(self.cancel_button)
        form_layout.addRow(self.status_label)

        # --- Gabungkan Bagian Kiri dan Kanan ke Layout Utama ---
        main_layout.addWidget(table_group, 3)  # Stretch factor 3 (sekitar 60%)
        main_layout.addWidget(self.form_group, 2)   # Stretch factor 2 (sekitar 40%)

        # --- Hubungkan Signal ke Slot ---
        self.add_new_button.clicked.connect(self.reset_form_state)
        self.show_deleted_checkbox.stateChanged.connect(self.load_users)
        self.user_table.cellClicked.connect(self.handle_table_click)
        self.save_button.clicked.connect(self.handle_save_user)
        self.delete_button.clicked.connect(self.handle_delete_user)
        self.restore_button.clicked.connect(self.handle_restore_user)
        self.cancel_button.clicked.connect(self.reset_form_state)

        # Atur state awal form ke mode "Tambah Baru"
        self.reset_form_state()

    def load_users(self):
        """Mengambil data semua user dari database dan menampilkannya di tabel."""
        self.user_table.setRowCount(0)  # Kosongkan tabel sebelum diisi ulang

        with SessionLocal() as db:
            # Query semua user, diurutkan berdasarkan ID.
            # Tambahkan joinedload untuk relasi 'creator' dan 'deleter' agar efisien.
            stmt = select(User).options(joinedload(User.creator), joinedload(User.deleter))

            # Filter berdasarkan status soft-delete jika checkbox tidak dicentang
            if not self.show_deleted_checkbox.isChecked():
                stmt = stmt.where(User.is_deleted == False)

            stmt = stmt.order_by(User.id)
            users = db.execute(stmt).scalars().all()

            for row, user in enumerate(users):
                self.user_table.insertRow(row)
                self.user_table.setItem(row, 0, QTableWidgetItem(str(user.id)))
                self.user_table.setItem(row, 1, QTableWidgetItem(user.username))
                self.user_table.setItem(row, 2, QTableWidgetItem(user.nama_lengkap))
                self.user_table.setItem(row, 3, QTableWidgetItem(user.role))
                self.user_table.setItem(row, 4, QTableWidgetItem(user.nomor_induk or "-"))
                self.user_table.setItem(row, 5, QTableWidgetItem(user.kelas or "-"))

                # Kolom 6: Status (menggabungkan is_deleted dan is_active)
                status_item = QTableWidgetItem()
                if user.is_deleted:
                    status_item.setText("Dihapus")
                    status_item.setForeground(Qt.red)
                else:
                    status_item.setText("Aktif" if user.is_active else "Tidak Aktif")
                status_item.setTextAlignment(Qt.AlignCenter)
                self.user_table.setItem(row, 6, status_item)

                # Kolom 7: Tanggal Dihapus
                deleted_at_str = user.deleted_at.strftime('%d/%m/%Y %H:%M') if user.deleted_at else "-"
                self.user_table.setItem(row, 7, QTableWidgetItem(deleted_at_str))

                # Kolom 8: Dihapus Oleh
                deleter_name = user.deleter.nama_lengkap if user.deleter else "-"
                self.user_table.setItem(row, 8, QTableWidgetItem(deleter_name))

                # Kolom 9: Dibuat Oleh
                creator_name = user.creator.nama_lengkap if user.creator else "Sistem (Seed Awal)"
                self.user_table.setItem(row, 9, QTableWidgetItem(creator_name))

        # Atur lebar kolom agar sesuai konten, kecuali kolom nama yang mengisi sisa ruang
        self.user_table.resizeColumnsToContents()
        self.user_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.user_table.horizontalHeader().setSectionResizeMode(9, QHeaderView.Stretch)

    def handle_table_click(self, row, column):
        """Mengisi form saat baris tabel diklik (masuk ke mode edit)."""
        # Ambil ID user dari kolom pertama (indeks 0)
        user_id_item = self.user_table.item(row, 0)
        if not user_id_item:
            return

        self.selected_user_id = int(user_id_item.text())

        with SessionLocal() as db:
            user = db.get(User, self.selected_user_id)
            if not user:
                self.reset_form_state()
                return

            # Isi form dengan data user yang dipilih
            self.username_input.setText(user.username)
            self.username_input.setEnabled(False)  # Username tidak bisa diubah
            self.password_input.clear()
            self.password_input.setPlaceholderText("Kosongkan jika tidak ingin diubah")
            self.nama_lengkap_input.setText(user.nama_lengkap)
            self.role_combo.setCurrentText(user.role)
            self.nomor_induk_input.setText(user.nomor_induk or "")
            self.kelas_input.setText(user.kelas or "")
            self.is_active_checkbox.setChecked(user.is_active)

            # Jika user sudah di-soft-delete, buat form read-only
            if user.is_deleted:
                self.form_group.setTitle("Detail User (Dihapus)")
                self.nama_lengkap_input.setEnabled(False)
                self.password_input.setEnabled(False)
                self.role_combo.setEnabled(False)
                self.nomor_induk_input.setEnabled(False)
                self.kelas_input.setEnabled(False)
                self.is_active_checkbox.setEnabled(False)
                self.save_button.setEnabled(False)
                self.delete_button.setEnabled(False) # Tidak bisa dihapus lagi
                self.restore_button.setVisible(True)
                self.cancel_button.setVisible(True)
                self.status_label.setText("User ini telah dihapus (read-only).")
            else:
                # Jika user aktif, UI normal untuk mode edit
                self.form_group.setTitle("Edit User")
                self.nama_lengkap_input.setEnabled(True)
                self.password_input.setEnabled(True)
                self.role_combo.setEnabled(True)
                self.kelas_input.setEnabled(True)
                self.is_active_checkbox.setEnabled(True)
                self.save_button.setEnabled(True)
                self.save_button.setText("Update User")
                self.delete_button.setEnabled(True)
                self.restore_button.setVisible(False)
                self.cancel_button.setVisible(True)
                self.status_label.setText("")

    def handle_save_user(self):
        """Logika untuk menambah atau mengupdate user, tergantung state."""
        # Reset label status
        self.status_label.setText("")
        self.status_label.setStyleSheet("")

        # --- MODE UPDATE ---
        if self.selected_user_id is not None:
            nama_lengkap = self.nama_lengkap_input.text().strip()
            password = self.password_input.text()  # Boleh kosong
            role = self.role_combo.currentText()
            nomor_induk = self.nomor_induk_input.text().strip() or None
            kelas = self.kelas_input.text().strip() or None
            is_active = self.is_active_checkbox.isChecked()

            if not nama_lengkap:
                self.status_label.setText("Nama Lengkap harus diisi.")
                self.status_label.setStyleSheet("color: red;")
                return

            # Validasi Nomor Induk wajib diisi untuk admin dan siswa
            if (role in ['admin', 'siswa']) and not nomor_induk:
                self.status_label.setText("Nomor Induk (NIP untuk admin, NIS untuk siswa) wajib diisi.")
                self.status_label.setStyleSheet("color: red;")
                return

            with SessionLocal() as db:
                # Validasi keunikan nomor induk (kecuali untuk diri sendiri)
                if nomor_induk:
                    stmt = select(User).where(
                        User.nomor_induk == nomor_induk,
                        User.id != self.selected_user_id
                    )
                    if db.execute(stmt).first():
                        self.status_label.setText("Nomor Induk sudah digunakan oleh user lain.")
                        self.status_label.setStyleSheet("color: red;")
                        return

                user_to_update = db.get(User, self.selected_user_id)
                if not user_to_update:
                    self.status_label.setText("User tidak ditemukan untuk diupdate.")
                    self.status_label.setStyleSheet("color: red;")
                    return

                # PROTEKSI BARU: Jangan sampai tidak ada superadmin aktif yang tersisa.
                if (user_to_update.role == 'superadmin' and user_to_update.is_active and
                        (role != 'superadmin' or not is_active)):
                    
                    count_stmt = select(func.count(User.id)).where(
                        User.role == 'superadmin',
                        User.is_active == True,
                        User.id != user_to_update.id
                    )
                    other_superadmins_count = db.execute(count_stmt).scalar_one()

                    if other_superadmins_count == 0:
                        QMessageBox.critical(self, "Aksi Ditolak", 
                                             "Tidak bisa mengubah role/menonaktifkan user ini karena merupakan "
                                             "satu-satunya superadmin aktif yang tersisa. Buat superadmin lain "
                                             "terlebih dahulu sebelum mengubah akun ini.")
                        return

                user_to_update.nama_lengkap = nama_lengkap
                user_to_update.role = role
                user_to_update.nomor_induk = nomor_induk
                user_to_update.kelas = kelas if role == 'siswa' else None
                user_to_update.is_active = is_active

                if password:
                    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                    user_to_update.password_hash = hashed_password

                db.commit()
                self.status_label.setText(f"Data user '{user_to_update.username}' berhasil diupdate.")
                self.status_label.setStyleSheet("color: green;")
                self.load_users()
                self.reset_form_state()
            return

        # --- MODE TAMBAH BARU ---
        username = self.username_input.text().strip()
        password = self.password_input.text()
        nama_lengkap = self.nama_lengkap_input.text().strip()
        role = self.role_combo.currentText()
        nomor_induk = self.nomor_induk_input.text().strip() or None
        kelas = self.kelas_input.text().strip() or None

        if not all([username, password, nama_lengkap]):
            self.status_label.setText("Username, Password, dan Nama harus diisi.")
            self.status_label.setStyleSheet("color: red;")
            return

        # Validasi Nomor Induk wajib diisi untuk admin dan siswa
        if (role in ['admin', 'siswa']) and not nomor_induk:
            self.status_label.setText("Nomor Induk (NIP untuk admin, NIS untuk siswa) wajib diisi.")
            self.status_label.setStyleSheet("color: red;")
            return

        with SessionLocal() as db:
            existing_user_by_username = db.execute(select(User).where(User.username == username)).scalars().first()
            if existing_user_by_username:
                if existing_user_by_username.is_deleted:
                    self.status_label.setText(
                        "Username ini pernah dipakai oleh user yang sudah dihapus.\n"
                        "Centang 'Tampilkan yang Dihapus' dan aktifkan kembali akun tersebut."
                    )
                else:
                    self.status_label.setText("Username sudah digunakan.")
                self.status_label.setStyleSheet("color: red;")
                return

            # Validasi keunikan nomor induk
            if nomor_induk:
                existing_user_by_nomor_induk = db.execute(select(User).where(User.nomor_induk == nomor_induk)).scalars().first()
                if existing_user_by_nomor_induk:
                    if existing_user_by_nomor_induk.is_deleted:
                        self.status_label.setText(
                            "Nomor Induk ini pernah dipakai oleh user yang sudah dihapus.\n"
                            "Centang 'Tampilkan yang Dihapus' dan aktifkan kembali akun tersebut."
                        )
                    else:
                        self.status_label.setText("Nomor Induk sudah digunakan oleh user lain.")
                    self.status_label.setStyleSheet("color: red;")
                    return

            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            new_user = User(
                username=username,
                password_hash=hashed_password,
                nama_lengkap=nama_lengkap,
                role=role,
                nomor_induk=nomor_induk,
                kelas=(kelas if role == 'siswa' else None),
                is_active=True,
                created_by=self.current_user_id
            )
            db.add(new_user)
            db.commit()

            self.status_label.setText(f"User '{username}' berhasil ditambahkan.")
            self.status_label.setStyleSheet("color: green;")
            self.load_users()
            self.reset_form_state()

    def handle_delete_user(self):
        """Logika untuk menghapus user yang dipilih, dengan validasi relasi data."""
        if self.selected_user_id is None:
            return

        with SessionLocal() as db:
            user_to_delete = db.get(User, self.selected_user_id)
            if not user_to_delete:
                self.reset_form_state()
                return

            # PROTEKSI BARU: Cek jika ini adalah superadmin aktif terakhir sebelum menghapus.
            if user_to_delete.role == 'superadmin':
                count_stmt = select(func.count(User.id)).where(
                    User.role == 'superadmin',
                    User.is_active == True,
                    User.id != user_to_delete.id
                )
                other_superadmins_count = db.execute(count_stmt).scalar_one()

                if other_superadmins_count == 0:
                    QMessageBox.critical(self, "Aksi Ditolak",
                                         "Tidak bisa menghapus satu-satunya superadmin aktif yang tersisa. "
                                         "Buat superadmin lain terlebih dahulu.")
                    return
            
            # Konfirmasi untuk soft-delete
            reply = QMessageBox.question(
                self, "Konfirmasi Hapus",
                f"Apakah Anda yakin ingin MENGHAPUS user '{user_to_delete.nama_lengkap}'?\n\n"
                "Data akan disembunyikan dari daftar aktif, namun riwayat tetap tersimpan untuk keperluan audit.",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                try:
                    # Lakukan soft-delete
                    user_to_delete.is_deleted = True
                    user_to_delete.deleted_at = datetime.now()
                    user_to_delete.deleted_by = self.current_user_id
                    user_to_delete.is_active = False  # Otomatis nonaktifkan juga

                    db.commit()

                    self.status_label.setText(f"User '{user_to_delete.username}' berhasil dihapus.")
                    self.status_label.setStyleSheet("color: green;")
                    self.load_users()
                    self.reset_form_state()
                except Exception as e:
                    db.rollback()
                    QMessageBox.critical(self, "Error Database", f"Terjadi kesalahan saat menghapus user (soft-delete).\n\nError: {e}")

    def handle_restore_user(self):
        """Logika untuk mengaktifkan kembali user yang sudah di-soft-delete."""
        if self.selected_user_id is None:
            return

        with SessionLocal() as db:
            user_to_restore = db.get(User, self.selected_user_id)
            if not user_to_restore:
                self.reset_form_state()
                return

            reply = QMessageBox.question(
                self, "Konfirmasi Aktifkan Kembali",
                f"Aktifkan kembali user '{user_to_restore.nama_lengkap}'? Username dan Nomor Induk akan bisa digunakan lagi.",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                try:
                    user_to_restore.is_deleted = False
                    user_to_restore.deleted_at = None
                    user_to_restore.deleted_by = None
                    user_to_restore.is_active = True
                    db.commit()
                    self.status_label.setText(f"User '{user_to_restore.username}' berhasil diaktifkan kembali.")
                    self.status_label.setStyleSheet("color: green;")
                    self.load_users()
                    self.reset_form_state()
                except Exception as e:
                    db.rollback()
                    QMessageBox.critical(self, "Error Database", f"Terjadi kesalahan saat mengaktifkan user.\n\nError: {e}")

    def reset_form_state(self):
        """Mengembalikan form ke state awal (mode tambah baru)."""
        self.user_table.clearSelection()
        self.selected_user_id = None

        # Kosongkan semua field
        self.username_input.clear()
        self.password_input.clear()
        self.nama_lengkap_input.clear()
        self.nomor_induk_input.clear()
        self.kelas_input.clear()

        # BUG FIX 1: Pastikan combo box kembali ke state awal
        self.role_combo.clear()
        self.role_combo.addItems(["admin", "siswa", "superadmin"])

        self.is_active_checkbox.setChecked(True)
        self.status_label.setText("")

        # Atur ulang UI ke mode tambah dan pastikan semua field yang relevan aktif
        self.form_group.setTitle("Tambah User Baru")
        self.username_input.setEnabled(True)
        self.nama_lengkap_input.setEnabled(True)
        self.password_input.setEnabled(True)
        self.role_combo.setEnabled(True)
        self.nomor_induk_input.setEnabled(True)
        self.kelas_input.setEnabled(True)
        self.is_active_checkbox.setEnabled(True)
        self.password_input.setPlaceholderText("")
        self.save_button.setText("Tambah User")
        self.save_button.setEnabled(True)
        self.delete_button.setEnabled(False)
        self.restore_button.setVisible(False)
        self.cancel_button.setVisible(False)