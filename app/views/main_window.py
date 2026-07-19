from datetime import datetime

from PySide2.QtCore import Qt, Signal
from PySide2.QtWidgets import (
    QAction,
    QLabel,
    QMainWindow,
    QStackedWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
    QStatusBar,
)
from sqlalchemy import select

# Import komponen database dan model
from app.database.db import SessionLocal
from app.models.models import LoginLog
# Import widget manajemen user untuk role superadmin
from app.views.superadmin.user_management import UserManagementWidget
# Import widget pengaturan aplikasi untuk role superadmin
from app.views.superadmin.app_settings import AppSettingsWidget
# Import widget manajemen rekening untuk role admin
from app.views.admin.account_management import AccountManagementWidget
# Import widget manajemen siswa untuk role admin
from app.views.admin.student_management import StudentManagementWidget
# Import widget transaksi untuk role siswa
from app.views.siswa.transaction_window import TransactionWidget
# Import widget buka rekening untuk role siswa
from app.views.siswa.account_create import AccountCreateWidget
# Import widget riwayat transaksi yang akan digunakan bersama
from app.views.shared.transaction_history import TransactionHistoryWidget
# Import widget backup & restore
from app.views.shared.backup_restore import BackupRestoreWidget
# Import dialog ubah password
from app.views.shared.change_password import ChangePasswordDialog


class MainWindow(QMainWindow):
    """
    Window utama aplikasi yang menjadi kerangka dasar untuk semua role.
    Konten di dalamnya akan disesuaikan berdasarkan role user yang login.
    """
    # Definisikan signal yang akan dikirim saat user logout
    logout_requested = Signal()

    def __init__(self, user_data: dict):
        """
        Constructor untuk MainWindow.
        :param user_data: Dictionary berisi data user yang login.
        """
        super().__init__()
        # Simpan data user yang login untuk digunakan di seluruh window
        self.user_data = user_data
        self.init_ui()
        # Panggil method untuk memuat konten yang sesuai dengan role user
        self.load_content_by_role()

    def init_ui(self):
        """Menginisialisasi semua komponen antarmuka pengguna (UI)."""
        # --- Konfigurasi Window ---
        nama_lengkap = self.user_data.get('nama_lengkap', 'User')
        role = self.user_data.get('role', 'Unknown')
        self.setWindowTitle(f"Bank Mini SMK - {nama_lengkap} ({role})")
        self.resize(900, 600)

        # --- Membuat Menu Bar dan Aksi Logout ---
        menu_bar = self.menuBar()
        akun_menu = menu_bar.addMenu("&Akun")

        # Aksi untuk Ubah Password
        change_password_action = QAction("Ubah Password", self)
        change_password_action.triggered.connect(self.show_change_password_dialog)
        akun_menu.addAction(change_password_action)

        akun_menu.addSeparator()  # Pemisah visual di menu

        logout_action = QAction("Logout", self)
        logout_action.triggered.connect(self.handle_logout)
        akun_menu.addAction(logout_action)

        # --- Membuat Central Widget dan Layout Utama ---
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # --- Membuat Widget Konten ---
        # 1. Label selamat datang
        welcome_label = QLabel(f"Selamat datang, {nama_lengkap}")
        welcome_label.setStyleSheet("font-size: 16px; padding: 10px;")
        welcome_label.setAlignment(Qt.AlignLeft)

        # 2. Area konten utama
        # QStackedWidget ideal untuk mengganti-ganti tampilan (misal: dashboard, manajemen user, dll)
        self.content_area = QStackedWidget()

        # --- Menambahkan widget ke layout utama ---
        main_layout.addWidget(welcome_label)
        main_layout.addWidget(self.content_area)
        main_layout.setStretch(1, 1)  # Membuat content_area mengisi sisa ruang

        # --- Membuat Status Bar ---
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)
        status_bar.showMessage(f"User: {self.user_data.get('username')} | Role: {role}")

    def load_content_by_role(self):
        """
        Memasang widget yang sesuai ke dalam content_area berdasarkan role user.
        """
        role = self.user_data.get('role')
        user_id = self.user_data.get('id')

        if role == 'superadmin':
            # Superadmin mendapatkan akses ke semua fitur dalam bentuk tab
            tab_widget = QTabWidget()

            # Tab 1: Kelola User
            user_management_widget = UserManagementWidget(current_user_id=self.user_data['id'])
            tab_widget.addTab(user_management_widget, "Kelola User")

            # Tab 2: Riwayat Semua Transaksi
            history_widget = TransactionHistoryWidget(current_user_id=user_id, is_admin_view=True)
            tab_widget.addTab(history_widget, "Riwayat Semua Transaksi")

            # Tab 3: Backup & Restore
            backup_widget = BackupRestoreWidget(can_restore=True)
            tab_widget.addTab(backup_widget, "Backup & Restore")

            self.content_area.addWidget(tab_widget)
            self.content_area.setCurrentWidget(tab_widget)

        elif role == 'admin':
            # Admin mendapatkan akses dalam bentuk tab
            tab_widget = QTabWidget()

            # Tab 1: Kelola Siswa
            student_management_widget = StudentManagementWidget(current_user_id=user_id)
            tab_widget.addTab(student_management_widget, "Kelola Siswa")

            # Tab 2: Kelola Rekening Nasabah
            account_management_widget = AccountManagementWidget(current_user_id=user_id)
            tab_widget.addTab(account_management_widget, "Kelola Rekening Nasabah")

            # Tab 3: Riwayat Semua Transaksi
            history_widget = TransactionHistoryWidget(current_user_id=user_id, is_admin_view=True)
            tab_widget.addTab(history_widget, "Riwayat Semua Transaksi")

            # Tab 4: Backup & Restore
            backup_widget = BackupRestoreWidget(can_restore=True)
            tab_widget.addTab(backup_widget, "Backup & Restore")

            # Tab 5: Pengaturan (dipindahkan dari superadmin)
            settings_widget = AppSettingsWidget()
            tab_widget.addTab(settings_widget, "Pengaturan")

            self.content_area.addWidget(tab_widget)
            self.content_area.setCurrentWidget(tab_widget)

        elif role == 'siswa':
            # Siswa mendapatkan akses dalam bentuk tab
            tab_widget = QTabWidget()

            # Tab 1: Transaksi
            transaction_widget = TransactionWidget(current_user_id=user_id)
            tab_widget.addTab(transaction_widget, "Transaksi")

            # Tab 2: Buka Rekening Baru (BARU)
            account_create_widget = AccountCreateWidget(current_user_id=user_id)
            tab_widget.addTab(account_create_widget, "Buka Rekening Baru")

            # Tab 3: Riwayat Transaksi
            history_widget = TransactionHistoryWidget(current_user_id=user_id, is_admin_view=False)
            tab_widget.addTab(history_widget, "Riwayat Transaksi")

            # Tab 4: Backup & Restore (tanpa opsi restore)
            backup_widget = BackupRestoreWidget(can_restore=False)
            tab_widget.addTab(backup_widget, "Backup & Restore")

            self.content_area.addWidget(tab_widget)
            self.content_area.setCurrentWidget(tab_widget)

        else:
            # Untuk role 'siswa' atau role lain yang belum didefinisikan
            placeholder_label = QLabel(f"Dashboard untuk role '{role}' sedang dalam pengembangan.")
            placeholder_label.setAlignment(Qt.AlignCenter)
            font = placeholder_label.font()
            font.setPointSize(14)
            placeholder_label.setFont(font)
            self.content_area.addWidget(placeholder_label)

    def show_change_password_dialog(self):
        """Menampilkan dialog untuk mengubah password user yang sedang login."""
        # Buat instance dialog, berikan ID user saat ini dan window ini sebagai parent
        dialog = ChangePasswordDialog(current_user_id=self.user_data['id'], parent=self)
        dialog.exec_()  # Tampilkan dialog secara modal (blocking)

    def showEvent(self, event):
        """Dipanggil saat window akan ditampilkan, digunakan untuk memaksimalkan window."""
        self.showMaximized()
        super().showEvent(event)

    def handle_logout(self):
        """
        Fungsi yang dijalankan saat tombol 'Logout' diklik.
        Memperbarui log di database, mengirim signal, dan menutup window.
        """
        print(f"User '{self.user_data['username']}' melakukan logout.")

        # a. Update record LoginLog di database
        with SessionLocal() as db:
            login_log_id = self.user_data.get('login_log_id')
            if login_log_id:
                log_entry = db.get(LoginLog, login_log_id)
                if log_entry:
                    log_entry.logout_time = datetime.now()
                    db.commit()

        # b. Emit signal bahwa proses logout diminta
        self.logout_requested.emit()

        # c. Tutup window utama
        self.close()