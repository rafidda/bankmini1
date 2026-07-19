# main.py
# File ini adalah entry point utama untuk aplikasi GUI Bank Mini SMK.

import sys

from PySide2.QtWidgets import QApplication

# Import fungsi setup database dan seeding
from app.database.db import init_db
from app.database.seed import seed_superadmin

# Import window login
from app.views.login_window import LoginWindow
# Import window utama
from app.views.main_window import MainWindow


class AppController:
    """
    Class ini bertanggung jawab untuk mengelola alur window aplikasi.
    Ia tidak mewarisi dari QWidget, hanya class Python biasa untuk
    mengontrol logika navigasi antar window.
    """
    def __init__(self):
        # Atribut ini akan menyimpan referensi ke window yang sedang aktif.
        # Ini sangat penting untuk mencegah window ditutup otomatis oleh
        # garbage collector Python.
        self.login_window = None
        self.main_window = None

    def show_login(self):
        """Membuat dan menampilkan window login."""
        # Membuat instance baru dari LoginWindow
        self.login_window = LoginWindow()
        # Menghubungkan signal 'login_success' ke method 'show_main_window'
        self.login_window.login_success.connect(self.show_main_window)
        self.login_window.show()

    def show_main_window(self, user_data: dict):
        """Membuat dan menampilkan window utama setelah login berhasil."""
        # Membuat instance baru dari MainWindow, dengan data user yang login
        self.main_window = MainWindow(user_data)
        # Menghubungkan signal 'logout_requested' kembali ke method 'show_login'
        self.main_window.logout_requested.connect(self.show_login)
        self.main_window.show()


if __name__ == "__main__":
    # 1. Lakukan setup awal: buat database, tabel, dan user superadmin
    init_db()
    seed_superadmin()

    # 2. Inisialisasi aplikasi PySide2
    app = QApplication(sys.argv)

    # 3. Buat instance controller aplikasi
    controller = AppController()

    # 4. Mulai aplikasi dengan menampilkan window login
    controller.show_login()

    # 5. Jalankan event loop aplikasi
    sys.exit(app.exec_())