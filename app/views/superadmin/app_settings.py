# File: app/views/superadmin/app_settings.py
# Berisi widget untuk superadmin mengelola pengaturan global aplikasi.

from datetime import datetime
from PySide2.QtCore import Qt
from PySide2.QtGui import QIntValidator
from PySide2.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

# Import komponen database dan controller
from app.database.db import SessionLocal
from app.controllers.settings_manager import get_setting, set_setting

# Daftar nama bulan untuk ComboBox
NAMA_BULAN = [
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember"
]


class AppSettingsWidget(QWidget):
    """
    Widget untuk admin mengubah pengaturan aplikasi yang tersimpan
    di tabel 'settings'.
    """

    def __init__(self):
        super().__init__()
        self.init_ui()
        self.load_settings()

    def init_ui(self):
        """Menginisialisasi semua komponen antarmuka pengguna (UI)."""
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignTop)

        # --- Grup Form Utama ---
        form_group = QGroupBox("Pengaturan Tahun Ajaran & Penomoran Rekening")
        form_layout = QFormLayout(form_group)
        form_layout.setLabelAlignment(Qt.AlignRight)

        # --- Field BARU: Kode Custom Rekening ---
        self.kode_custom_input = QLineEdit()
        self.kode_custom_input.setMaxLength(2)
        self.kode_custom_input.setPlaceholderText("00")
        # Validator untuk membatasi input hanya angka 0-99
        self.kode_custom_input.setValidator(QIntValidator(0, 99, self))
        form_layout.addRow("Kode Custom Rekening:", self.kode_custom_input)

        # --- Label Penjelasan Kode Custom ---
        kode_custom_help = QLabel(
            "Kode 2 digit untuk membedakan cabang/kantor bank (akan dikoordinasikan dengan pihak bank). "
            "Kosongkan/isi '00' jika belum ditentukan."
        )
        kode_custom_help.setStyleSheet("font-size: 9px; color: grey;")
        kode_custom_help.setWordWrap(True)
        form_layout.addRow(kode_custom_help)

        # --- Field: Bulan Mulai Tahun Ajaran ---
        self.bulan_cutoff_combo = QComboBox()
        for i, nama_bulan in enumerate(NAMA_BULAN):
            self.bulan_cutoff_combo.addItem(nama_bulan, userData=i + 1)
        form_layout.addRow("Bulan Mulai Tahun Ajaran:", self.bulan_cutoff_combo)

        # --- Field BARU: Tahun Pratinjau (hanya untuk UI) ---
        self.tahun_pratinjau_spinbox = QSpinBox()
        self.tahun_pratinjau_spinbox.setRange(2020, 2100)
        self.tahun_pratinjau_spinbox.setValue(datetime.now().year)
        form_layout.addRow("Tahun Pratinjau:", self.tahun_pratinjau_spinbox)

        # --- Label Penjelasan ---
        help_label = QLabel(
            "Menentukan kapan tahun ajaran baru dimulai. Ini memengaruhi format otomatis nomor rekening nasabah baru."
        )
        help_label.setStyleSheet("font-size: 9px; color: grey;")
        help_label.setWordWrap(True)
        form_layout.addRow(help_label)

        # --- Label Pratinjau ---
        self.preview_label = QLabel("")
        self.preview_label.setStyleSheet(
            "font-size: 9px; background-color: #f0f0f0; "
            "border: 1px solid #ccc; padding: 5px; border-radius: 3px;"
        )
        self.preview_label.setWordWrap(True)
        self.preview_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        form_layout.addRow("Pratinjau Dampak:", self.preview_label)

        # --- Label Penjelasan Tambahan (BARU) ---
        catatan_label = QLabel(
            "<b>Catatan:</b> Field 'Tahun Pratinjau' di atas HANYA untuk simulasi/latihan melihat contoh, TIDAK disimpan ke sistem. "
            "Saat digunakan sungguhan, nomor rekening akan selalu dihitung otomatis berdasarkan TANGGAL ASLI saat rekening dibuka — "
            "jadi tahun ajaran akan otomatis lanjut sendiri setiap tahun tanpa perlu mengatur ulang atau menyimpan pengaturan ini kembali."
        )
        catatan_label.setStyleSheet("font-size: 9px; color: grey;")
        catatan_label.setWordWrap(True)
        # Tambahkan di baris baru, span kedua kolom
        form_layout.addRow(catatan_label)

        # --- Tombol Simpan dan Label Status ---
        self.save_button = QPushButton("Simpan Pengaturan")
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)

        form_layout.addRow(self.save_button)
        form_layout.addRow(self.status_label)

        main_layout.addWidget(form_group)

        # --- Hubungkan Signal ke Slot ---
        self.save_button.clicked.connect(self.handle_save_settings)
        # Hubungkan semua input yang relevan ke fungsi update pratinjau
        self.kode_custom_input.textChanged.connect(self._update_preview)
        self.bulan_cutoff_combo.currentIndexChanged.connect(self._update_preview)
        self.tahun_pratinjau_spinbox.valueChanged.connect(self._update_preview)

    def load_settings(self):
        """
        Memuat nilai pengaturan saat ini dari database dan menampilkannya di form.
        """
        self.status_label.setText("")
        with SessionLocal() as db:
            # 1. Muat Kode Custom Rekening, default '00'
            kode_custom_str = get_setting(db, 'kode_custom_rekening', '00')
            self.kode_custom_input.setText(kode_custom_str)

            # 2. Muat Bulan Cutoff, default '7' jika tidak ada
            bulan_str = get_setting(db, 'bulan_cutoff_tahun_ajaran', '7')
            try:
                bulan_int = int(bulan_str)
                # Pastikan nilai berada dalam rentang yang valid
                if not (1 <= bulan_int <= 12):
                    bulan_int = 7 # Fallback ke default jika nilai di DB tidak valid
            except (ValueError, TypeError):
                bulan_int = 7 # Fallback ke default jika nilai di DB tidak valid

            # 3. Atur nilai pada QComboBox tanpa memicu sinyal
            self.bulan_cutoff_combo.blockSignals(True)
            index = self.bulan_cutoff_combo.findData(bulan_int)
            if index != -1:
                self.bulan_cutoff_combo.setCurrentIndex(index)
            self.bulan_cutoff_combo.blockSignals(False)

            # Panggil _update_preview secara manual untuk menampilkan pratinjau awal
            self._update_preview()

    def handle_save_settings(self):
        """
        Mengambil nilai dari form dan menyimpannya ke database menggunakan
        fungsi set_setting.
        """
        # Ambil nilai dari kedua form yang akan disimpan
        bulan_cutoff_value = self.bulan_cutoff_combo.currentData()
        kode_custom_value = self.kode_custom_input.text().strip()

        # Sanitasi kode custom agar selalu 2 digit dengan leading zero jika perlu
        kode_custom_sanitized = kode_custom_value.zfill(2)

        with SessionLocal() as db:
            # Simpan kedua pengaturan ke database
            set_setting(db, 'bulan_cutoff_tahun_ajaran', str(bulan_cutoff_value))
            set_setting(db, 'kode_custom_rekening', kode_custom_sanitized)

        self.status_label.setText("Pengaturan berhasil disimpan.")
        self.status_label.setStyleSheet("color: green;")

        # Muat ulang pengaturan untuk memastikan form menampilkan data yang sudah disanitasi (misal: '1' menjadi '01')
        self.load_settings()

    def _update_preview(self):
        """Memperbarui label pratinjau berdasarkan bulan yang dipilih di ComboBox."""
        # Ambil nilai dari semua input yang relevan
        kode_custom = self.kode_custom_input.text().strip().zfill(2)
        bulan_cutoff = self.bulan_cutoff_combo.currentData()
        nama_bulan = self.bulan_cutoff_combo.currentText()
        tahun_pratinjau = self.tahun_pratinjau_spinbox.value()

        if not bulan_cutoff:
            self.preview_label.setText("")
            return

        def hitung_prefix_dan_ta(bulan: int, tahun: int, bulan_cutoff_ref: int):
            """Helper untuk menghitung prefix dan tahun ajaran."""
            tahun_mulai = tahun if bulan >= bulan_cutoff_ref else tahun - 1
            prefix = f"{str(tahun_mulai)[-2:]}{str(tahun_mulai + 1)[-2:]}"
            tahun_ajaran = f"{tahun_mulai}/{tahun_mulai + 1}"
            return prefix, tahun_ajaran

        # --- Logika BARU untuk menampilkan bulan sebelum dan saat cutoff ---
        # Tentukan bulan sebelum cutoff, tangani kasus Januari (bulan 1)
        if bulan_cutoff == 1:
            bulan_sebelumnya = 12
            tahun_untuk_bulan_sebelumnya = tahun_pratinjau - 1
        else:
            bulan_sebelumnya = bulan_cutoff - 1
            tahun_untuk_bulan_sebelumnya = tahun_pratinjau

        nama_bulan_sebelumnya = NAMA_BULAN[bulan_sebelumnya - 1]

        # Contoh 1: Bulan SEBELUM cutoff (masih tahun ajaran lama)
        prefix_1, ta_1 = hitung_prefix_dan_ta(bulan_sebelumnya, tahun_untuk_bulan_sebelumnya, bulan_cutoff)
        nomor_contoh_1 = f"{kode_custom}-{prefix_1}-0001"

        # Contoh 2: Bulan SAAT cutoff (sudah masuk tahun ajaran baru)
        prefix_2, ta_2 = hitung_prefix_dan_ta(bulan_cutoff, tahun_pratinjau, bulan_cutoff)
        nomor_contoh_2 = f"{kode_custom}-{prefix_2}-0001"

        preview_text = (
            f"Jika tahun ajaran dimulai bulan <b>{nama_bulan}</b>:<br>"
            f"&#8226; Rekening dibuka <b>{nama_bulan_sebelumnya} {tahun_untuk_bulan_sebelumnya}</b> &rarr; Tahun Ajaran {ta_1} &rarr; Nomor: <b>{nomor_contoh_1}</b><br>"
            f"&#8226; Rekening dibuka <b>{nama_bulan} {tahun_pratinjau}</b> &rarr; Tahun Ajaran {ta_2} &rarr; Nomor: <b>{nomor_contoh_2}</b><br>"
            f"<i>(Format: kode custom-tahun ajaran-nomor urut)</i>"
        )
        self.preview_label.setText(preview_text)