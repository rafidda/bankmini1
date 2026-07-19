# File: app/views/shared/backup_restore.py
# Berisi widget UI untuk melakukan backup dan restore database.

from typing import Optional

from PySide2.QtCore import Qt
from PySide2.QtWidgets import (
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

# Import fungsi-fungsi dari controller backup_manager
from app.controllers.backup_manager import (
    backup_database,
    generate_backup_filename,
    restore_database,
)


class BackupRestoreWidget(QWidget):
    """
    Widget untuk menyediakan antarmuka backup dan restore database.
    Opsi restore dapat disembunyikan berdasarkan role user.
    """

    def __init__(self, can_restore: bool, parent: Optional[QWidget] = None):
        """
        Constructor.
        :param can_restore: Jika True, tombol dan opsi restore akan ditampilkan.
                            Jika False, hanya opsi backup yang ditampilkan.
        :param parent: Widget induk.
        """
        super().__init__(parent)
        self.can_restore = can_restore
        self.init_ui()

    def init_ui(self):
        """Menginisialisasi semua komponen antarmuka pengguna (UI)."""
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignTop) # Mulai dari atas

        # --- 1. Bagian Backup ---
        backup_group = QGroupBox("Backup Database")
        backup_layout = QVBoxLayout(backup_group)

        backup_desc = QLabel("Simpan salinan (backup) dari seluruh data aplikasi saat ini ke lokasi yang aman.")
        backup_desc.setWordWrap(True)
        self.backup_button = QPushButton("Backup Sekarang")

        backup_layout.addWidget(backup_desc)
        backup_layout.addWidget(self.backup_button)
        main_layout.addWidget(backup_group)

        # --- 2. Bagian Restore (Opsional) ---
        if self.can_restore:
            # Garis pemisah visual
            line = QFrame()
            line.setFrameShape(QFrame.HLine)
            line.setFrameShadow(QFrame.Sunken)
            main_layout.addWidget(line)

            restore_group = QGroupBox("Restore Database")
            restore_layout = QVBoxLayout(restore_group)

            restore_warning = QLabel(
                "<b>PERHATIAN:</b> Proses restore akan <b>MENGGANTI TOTAL</b> "
                "seluruh data yang ada saat ini dengan data dari file backup yang Anda pilih. "
                "Tindakan ini <b>TIDAK BISA DIBATALKAN</b>.<br><br>"
                "<i>Sebagai jaring pengaman, sistem akan secara otomatis membuat backup dari "
                "data saat ini sebelum proses restore dimulai.</i>"
            )
            restore_warning.setWordWrap(True)
            # Atur warna teks peringatan agar lebih menonjol
            restore_warning.setStyleSheet("color: #D32F2F; background-color: #FFEBEE; padding: 8px; border-radius: 4px;")

            self.restore_button = QPushButton("Restore dari File Backup")

            restore_layout.addWidget(restore_warning)
            restore_layout.addWidget(self.restore_button)
            main_layout.addWidget(restore_group)

        # --- 3. Label Status ---
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        main_layout.addStretch() # Dorong status label ke bawah
        main_layout.addWidget(self.status_label)

        # --- Hubungkan Signal ke Slot ---
        self.backup_button.clicked.connect(self.handle_backup)
        if self.can_restore:
            self.restore_button.clicked.connect(self.handle_restore)

    def handle_backup(self):
        """Menangani logika saat tombol 'Backup Sekarang' diklik."""
        self.status_label.setText("")
        default_filename = generate_backup_filename()

        # Buka dialog untuk memilih lokasi penyimpanan file backup
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Simpan Backup Database",
            default_filename,
            "Database Files (*.db);;All Files (*)"
        )

        # Jika user memilih lokasi (tidak menekan cancel)
        if save_path:
            try:
                backup_database(save_path)
                QMessageBox.information(
                    self, "Backup Berhasil",
                    f"Database berhasil di-backup ke:\n{save_path}"
                )
                self.status_label.setText(f"Backup terakhir berhasil pada {QDateTime.currentDateTime().toString('dd-MM-yyyy HH:mm:ss')}")
            except Exception as e:
                QMessageBox.critical(self, "Backup Gagal", f"Terjadi kesalahan saat melakukan backup:\n{e}")

    def handle_restore(self):
        """Menangani logika saat tombol 'Restore dari Backup' diklik."""
        self.status_label.setText("")

        # Buka dialog untuk memilih file backup yang akan di-restore
        source_path, _ = QFileDialog.getOpenFileName(
            self,
            "Pilih File Backup untuk Restore",
            "",
            "Database Files (*.db);;All Files (*)"
        )

        # Jika user memilih file
        if source_path:
            # Tampilkan pesan konfirmasi yang sangat tegas sebelum melanjutkan
            reply = QMessageBox.question(
                self,
                "Konfirmasi Restore",
                "Apakah Anda BENAR-BENAR yakin ingin me-restore data dari file ini?\n\n"
                "<b>SEMUA DATA SAAT INI AKAN HILANG DAN DIGANTIKAN.</b>\n\n"
                "Aplikasi perlu di-restart secara manual setelah proses ini selesai.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No  # Default pilihan adalah 'No'
            )

            if reply == QMessageBox.Yes:
                try:
                    restore_database(source_path)
                    QMessageBox.information(
                        self,
                        "Restore Berhasil",
                        "Proses restore berhasil diselesaikan.\n\n"
                        "<b>PENTING: Silakan TUTUP dan BUKA KEMBALI aplikasi ini</b> "
                        "untuk memuat data yang baru di-restore."
                    )
                    # Anda bisa menutup aplikasi secara paksa di sini jika mau,
                    # tapi meminta user lebih aman.
                    # QApplication.instance().quit()
                except Exception as e:
                    QMessageBox.critical(self, "Restore Gagal", f"Terjadi kesalahan saat melakukan restore:\n{e}")

# Tambahkan import QDateTime untuk status label
from PySide2.QtCore import QDateTime