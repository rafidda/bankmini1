import locale
import os
from datetime import datetime, timedelta
from typing import List, Optional

from PySide2.QtCore import Qt, QDate
from PySide2.QtWidgets import (
    QComboBox,
    QDateEdit,
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
    QFileDialog,
)
from sqlalchemy import asc, select
from sqlalchemy.orm import joinedload

# Import komponen database dan model
from app.database.db import SessionLocal
from app.models.models import Account, Transaction, User
from app.controllers.pdf_generator import generate_buku_tabungan, generate_laporan_per_teller

# Atur locale ke Indonesia untuk format mata uang Rupiah
try:
    locale.setlocale(locale.LC_ALL, 'id_ID.UTF-8')
except locale.Error:
    locale.setlocale(locale.LC_ALL, 'Indonesian_indonesia.1252')


class TransactionHistoryWidget(QWidget):
    """
    Widget untuk menampilkan riwayat semua transaksi.
    Bisa menampilkan semua transaksi (untuk admin) atau hanya transaksi
    yang diinput oleh user tertentu (untuk siswa/teller).
    """

    def __init__(self, current_user_id: int, is_admin_view: bool = False):
        super().__init__()
        self.current_user_id = current_user_id
        self.is_admin_view = is_admin_view

        # Cache untuk menyimpan semua data transaksi dari DB, menghindari query berulang saat filter
        self.all_transactions: List[Transaction] = []
        # Cache untuk menyimpan hasil filter saat ini, untuk digunakan oleh fungsi cetak
        self.current_filtered_transactions: List[Transaction] = []

        self.init_ui()
        self.load_transactions()

    def init_ui(self):
        """Menginisialisasi semua komponen antarmuka pengguna (UI)."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # --- Grup Filter ---
        filter_group = QGroupBox("Filter Riwayat Transaksi")
        filter_layout = QHBoxLayout(filter_group)

        # Filter berdasarkan nama/no. rekening
        filter_layout.addWidget(QLabel("Cari (Nama/No. Rek):"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Ketik untuk mencari...")
        filter_layout.addWidget(self.search_input)

        # --- Filter Tanggal (BARU) ---
        filter_layout.addWidget(QLabel("Dari:"))
        self.filter_tanggal_mulai = QDateEdit()
        self.filter_tanggal_mulai.setCalendarPopup(True)
        self.filter_tanggal_mulai.setDisplayFormat("dd/MM/yyyy")
        # Default: 30 hari yang lalu
        self.filter_tanggal_mulai.setDate(QDate.currentDate().addDays(-30))
        filter_layout.addWidget(self.filter_tanggal_mulai)

        filter_layout.addWidget(QLabel("Sampai:"))
        self.filter_tanggal_akhir = QDateEdit()
        self.filter_tanggal_akhir.setCalendarPopup(True)
        self.filter_tanggal_akhir.setDisplayFormat("dd/MM/yyyy")
        # Default: hari ini
        self.filter_tanggal_akhir.setDate(QDate.currentDate())
        filter_layout.addWidget(self.filter_tanggal_akhir)

        self.reset_date_button = QPushButton("Reset Tanggal")
        filter_layout.addWidget(self.reset_date_button)

        # Filter berdasarkan teller (hanya untuk admin)
        self.teller_filter_combo = QComboBox()
        self.print_teller_report_button = QPushButton("Cetak Laporan Teller")
        if self.is_admin_view:
            filter_layout.addWidget(QLabel("Teller:"))
            filter_layout.addWidget(self.teller_filter_combo)
            filter_layout.addWidget(self.print_teller_report_button)
        else:
            self.teller_filter_combo.setVisible(False)
            self.print_teller_report_button.setVisible(False)

        filter_layout.addStretch()

        # Tombol Refresh
        self.refresh_button = QPushButton("Refresh Data")
        filter_layout.addWidget(self.refresh_button)

        # Tombol Cetak Buku Tabungan
        self.print_book_button = QPushButton("Cetak Buku Tabungan")
        filter_layout.addWidget(self.print_book_button)

        # --- Tabel Riwayat Transaksi ---
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(9)
        self.history_table.setHorizontalHeaderLabels([
            "ID Transaksi", "Waktu", "Nomor Rekening", "Nama Nasabah",
            "Jenis Transaksi", "Jumlah", "Saldo Akhir", "Diinput Oleh", "Keterangan"
        ])
        # Konfigurasi tabel agar read-only dan rapi
        self.history_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.history_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.history_table.setSelectionMode(QTableWidget.SingleSelection)
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.setAlternatingRowColors(True)

        # --- Gabungkan layout ---
        main_layout.addWidget(filter_group)
        main_layout.addWidget(self.history_table)

        # --- Hubungkan Signal ke Slot ---
        self.refresh_button.clicked.connect(self.load_transactions)
        self.search_input.textChanged.connect(self._apply_filters)
        # Hubungkan filter tanggal ke slot _apply_filters
        self.filter_tanggal_mulai.dateChanged.connect(self._apply_filters)
        self.filter_tanggal_akhir.dateChanged.connect(self._apply_filters)
        self.reset_date_button.clicked.connect(self._reset_date_filters)
        # Hubungkan filter teller
        self.teller_filter_combo.currentIndexChanged.connect(self._apply_filters)
        self.print_book_button.clicked.connect(self.handle_cetak_buku_tabungan)
        self.print_teller_report_button.clicked.connect(self.handle_cetak_laporan_teller)

    def _reset_date_filters(self):
        """Mengembalikan filter tanggal ke nilai default (30 hari terakhir)."""
        self.filter_tanggal_mulai.setDate(QDate.currentDate().addDays(-30))
        self.filter_tanggal_akhir.setDate(QDate.currentDate())

    def load_transactions(self):
        """
        Mengambil data transaksi terbaru dari database, menyimpannya di cache,
        dan memperbarui tampilan.
        """
        with SessionLocal() as db:
            # Buat query dasar untuk mengambil transaksi
            # Gunakan joinedload untuk eager loading, menghindari N+1 query
            stmt = select(Transaction).options(
                joinedload(Transaction.account),
                joinedload(Transaction.teller)
            )

            # Jika bukan admin, filter hanya transaksi yang dibuat oleh user ini
            if not self.is_admin_view:
                stmt = stmt.where(Transaction.teller_id == self.current_user_id)

            # Urutkan dari yang paling baru
            stmt = stmt.order_by(Transaction.waktu_transaksi.desc())

            # Eksekusi query dan simpan hasilnya di cache
            self.all_transactions = db.execute(stmt).scalars().all()

        # Jika admin, perbarui daftar teller di ComboBox
        if self.is_admin_view:
            self._populate_teller_filter()

        # Terapkan filter yang ada (atau tampilkan semua jika filter kosong)
        self._apply_filters()

    def _populate_teller_filter(self):
        """Mengisi ComboBox filter teller dengan data unik dari transaksi yang di-load."""
        self.teller_filter_combo.blockSignals(True)  # Cegah trigger sinyal saat mengisi
        current_selection = self.teller_filter_combo.currentData()
        self.teller_filter_combo.clear()
        self.teller_filter_combo.addItem("Semua Teller", userData=None)

        # Ambil nama teller unik dari data yang sudah di-load
        tellers = sorted(
            list(
                {
                    (trx.teller.id, trx.teller.nama_lengkap)
                    for trx in self.all_transactions if trx.teller
                }
            ),
            key=lambda x: x[1]  # urutkan berdasarkan nama
        )

        for teller_id, nama_lengkap in tellers:
            self.teller_filter_combo.addItem(nama_lengkap, userData=teller_id)

        # Kembalikan seleksi sebelumnya jika masih ada
        index = self.teller_filter_combo.findData(current_selection)
        if index != -1:
            self.teller_filter_combo.setCurrentIndex(index)

        self.teller_filter_combo.blockSignals(False)  # Aktifkan kembali sinyal

    def _apply_filters(self):
        """
        Menyaring data dari cache `self.all_transactions` berdasarkan input
        di search bar dan ComboBox, lalu menampilkan hasilnya di tabel.
        """
        search_text = self.search_input.text().lower().strip()
        selected_teller_id = self.teller_filter_combo.currentData()
        # Ambil tanggal dari QDateEdit dan konversi ke objek date Python
        start_date = self.filter_tanggal_mulai.date().toPython()
        end_date = self.filter_tanggal_akhir.date().toPython()

        # Mulai dengan semua transaksi yang sudah di-load
        filtered_transactions = self.all_transactions

        # 1. Filter berdasarkan teller (jika ada yang dipilih)
        if self.is_admin_view and selected_teller_id is not None:
            filtered_transactions = [
                trx for trx in filtered_transactions if trx.teller_id == selected_teller_id
            ]

        # 2. Filter berdasarkan rentang tanggal (inklusif)
        if start_date and end_date:
            # Pastikan start_date tidak lebih besar dari end_date
            if start_date > end_date:
                start_date, end_date = end_date, start_date # Tukar jika perlu

            filtered_transactions = [
                trx for trx in filtered_transactions if start_date <= trx.waktu_transaksi.date() <= end_date
            ]

        # 3. Filter berdasarkan teks pencarian (dengan cek null pada trx.account)
        if search_text:
            filtered_transactions = [
                trx for trx in filtered_transactions
                if (trx.account and (search_text in trx.account.nomor_rekening.lower() or
                                     search_text in trx.account.nama_nasabah.lower()))
            ]
        # Setelah semua filter diterapkan, perbarui tabel
        # Simpan hasil filter ke cache untuk digunakan oleh fungsi lain (misal: cetak)
        self.current_filtered_transactions = filtered_transactions
        self._populate_table(self.current_filtered_transactions)

    def _populate_table(self, transactions: List[Transaction]):
        """Mengisi QTableWidget dengan daftar transaksi yang diberikan."""
        self.history_table.setRowCount(0)  # Kosongkan tabel

        for row, trx in enumerate(transactions):
            self.history_table.insertRow(row)

            # Kolom 0: ID Transaksi
            self.history_table.setItem(row, 0, QTableWidgetItem(str(trx.id)))
            # Kolom 1: Waktu
            waktu_str = trx.waktu_transaksi.strftime('%d %b %Y, %H:%M')
            self.history_table.setItem(row, 1, QTableWidgetItem(waktu_str))
            # Kolom 2 & 3: Info Akun (dengan cek null)
            self.history_table.setItem(row, 2, QTableWidgetItem(trx.account.nomor_rekening if trx.account else "N/A"))
            self.history_table.setItem(row, 3, QTableWidgetItem(trx.account.nama_nasabah if trx.account else "N/A"))
            # Kolom 4: Jenis Transaksi
            # Menggunakan map untuk menampilkan label yang lebih deskriptif
            jenis_map = {
                'setor': 'Setor',
                'tarik': 'Tarik',
                'transfer_keluar': 'Transfer Keluar',
                'transfer_masuk': 'Transfer Masuk'
            }
            jenis_str = jenis_map.get(trx.jenis, trx.jenis.capitalize())
            self.history_table.setItem(row, 4, QTableWidgetItem(jenis_str))
            # Kolom 5: Jumlah (format Rupiah)
            jumlah_str = locale.currency(trx.jumlah, grouping=True, symbol='Rp ')
            jumlah_item = QTableWidgetItem(jumlah_str)
            jumlah_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.history_table.setItem(row, 5, jumlah_item)
            # Kolom 6: Saldo Akhir (format Rupiah)
            saldo_akhir_str = locale.currency(trx.saldo_akhir, grouping=True, symbol='Rp ')
            saldo_item = QTableWidgetItem(saldo_akhir_str)
            saldo_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.history_table.setItem(row, 6, saldo_item)
            # Kolom 7: Diinput Oleh (dengan cek null)
            teller_name = trx.teller.nama_lengkap if trx.teller else "N/A"
            self.history_table.setItem(row, 7, QTableWidgetItem(teller_name))
            # Kolom 8: Keterangan
            self.history_table.setItem(row, 8, QTableWidgetItem(trx.keterangan or "-"))

        # Atur lebar kolom agar sesuai konten
        self.history_table.resizeColumnsToContents()
        # Buat kolom nama nasabah dan keterangan mengisi sisa ruang
        self.history_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.history_table.horizontalHeader().setSectionResizeMode(8, QHeaderView.Stretch)

    def handle_cetak_buku_tabungan(self):
        """
        Memvalidasi data yang ditampilkan, mengambil data lengkap, dan memanggil
        fungsi untuk generate PDF buku tabungan.
        """
        # 1. Validasi: Cek data yang sedang ditampilkan di tabel
        if not self.current_filtered_transactions:
            QMessageBox.warning(self, "Aksi Ditolak", "Tidak ada data transaksi untuk dicetak.")
            return

        # Ambil semua nomor rekening unik dari hasil filter saat ini
        unique_account_ids = {trx.account_id for trx in self.current_filtered_transactions if trx.account_id}

        if len(unique_account_ids) != 1:
            QMessageBox.warning(
                self,
                "Aksi Ditolak",
                "Silakan cari dan pastikan hanya menampilkan riwayat SATU nomor rekening "
                "terlebih dahulu sebelum mencetak buku tabungan."
            )
            return

        # Jika valid, kita punya satu account_id
        target_account_id = unique_account_ids.pop()

        try:
            with SessionLocal() as db:
                # 2. Ambil data yang diperlukan dari database
                # Ambil objek Account
                account = db.get(Account, target_account_id)
                if not account:
                    raise Exception("Data rekening tidak ditemukan di database.")

                # Ambil SEMUA transaksi untuk rekening ini, urutkan dari LAMA ke BARU.
                # PERBAIKAN: Tambahkan options(joinedload(...)) untuk eager loading relasi
                # 'account' dan 'teller'. Ini mencegah LazyLoadError saat PDF generator
                # mengakses trx.teller.nama_lengkap setelah session ini ditutup.
                all_account_transactions = db.execute(
                    select(Transaction)
                    .options(joinedload(Transaction.account),
                             joinedload(Transaction.teller))
                    .where(Transaction.account_id == target_account_id)
                    .order_by(Transaction.waktu_transaksi.asc())  # PENTING: asc() untuk buku tabungan
                ).scalars().all()

                # Ambil nama user yang sedang login untuk dicantumkan di footer
                current_user = db.get(User, self.current_user_id)
                dicetak_oleh = current_user.nama_lengkap if current_user else "Sistem"

            # 3. Buka dialog simpan file
            default_filename = f"BukuTabungan_{account.nomor_rekening}.pdf"
            save_path, _ = QFileDialog.getSaveFileName(
                self,
                "Simpan Buku Tabungan",
                default_filename,
                "PDF Files (*.pdf)"
            )

            # Jika user tidak membatalkan dialog
            if save_path:
                # 4. Panggil generator PDF
                generate_buku_tabungan(
                    account=account,
                    transactions_list=all_account_transactions,
                    save_path=save_path,
                    dicetak_oleh=dicetak_oleh
                )

                # 5. Tampilkan pesan sukses dan tawarkan untuk membuka file
                reply = QMessageBox.information(
                    self, "Sukses",
                    f"Buku tabungan untuk rekening {account.nomor_rekening} berhasil dicetak.",
                    QMessageBox.Ok | QMessageBox.Open, QMessageBox.Ok
                )

                if reply == QMessageBox.Open:
                    os.startfile(save_path)

        except Exception as e:
            # Tangani semua kemungkinan error
            QMessageBox.critical(self, "Error", f"Gagal mencetak buku tabungan:\n{e}")

    def handle_cetak_laporan_teller(self):
        """
        Memvalidasi teller yang dipilih, mengambil data, dan memanggil
        fungsi untuk generate PDF laporan per teller.
        Hanya aktif jika is_admin_view True.
        """
        # 1. Validasi: Cek apakah teller spesifik sudah dipilih di dropdown
        selected_teller_id = self.teller_filter_combo.currentData()
        if selected_teller_id is None:
            QMessageBox.warning(
                self,
                "Aksi Ditolak",
                "Silakan pilih satu nama teller terlebih dahulu di dropdown filter sebelum mencetak laporan."
            )
            return

        try:
            with SessionLocal() as db:
                # 2. Ambil data yang diperlukan dari DB
                # Ambil objek User (teller) yang dipilih
                teller = db.get(User, selected_teller_id)
                if not teller:
                    raise Exception("Data teller tidak ditemukan di database.")

                # Ambil SEMUA transaksi untuk teller ini, urutkan dari LAMA ke BARU
                # Gunakan joinedload untuk relasi account agar tidak terjadi N+1 query
                all_teller_transactions = db.execute(
                    select(Transaction)
                    .options(joinedload(Transaction.account))
                    .where(Transaction.teller_id == selected_teller_id)
                    .order_by(Transaction.waktu_transaksi.asc())  # LAMA ke BARU
                ).scalars().all()

                # 3. Tentukan periode dan cek jika ada transaksi
                if not all_teller_transactions:
                    QMessageBox.information(self, "Informasi", f"Teller '{teller.nama_lengkap}' belum memiliki riwayat transaksi.")
                    return

                tanggal_mulai = all_teller_transactions[0].waktu_transaksi
                tanggal_akhir = datetime.now()

                # Ambil nama user yang sedang login untuk dicantumkan di footer
                current_user = db.get(User, self.current_user_id)
                dicetak_oleh = current_user.nama_lengkap if current_user else "Sistem"

            # 4. Buka dialog simpan file
            default_filename = f"LaporanTeller_{teller.username}.pdf"
            save_path, _ = QFileDialog.getSaveFileName(
                self, "Simpan Laporan Teller", default_filename, "PDF Files (*.pdf)"
            )

            if save_path:
                # 5. Panggil generator PDF
                generate_laporan_per_teller(
                    teller=teller, transactions_list=all_teller_transactions,
                    tanggal_mulai=tanggal_mulai, tanggal_akhir=tanggal_akhir,
                    save_path=save_path, dicetak_oleh=dicetak_oleh
                )

                # 6. Tampilkan pesan sukses dan tawarkan untuk membuka file
                reply = QMessageBox.information(
                    self, "Sukses", f"Laporan untuk teller {teller.nama_lengkap} berhasil dicetak.",
                    QMessageBox.Ok | QMessageBox.Open, QMessageBox.Ok
                )
                if reply == QMessageBox.Open:
                    os.startfile(save_path)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Gagal mencetak laporan teller:\n{e}")