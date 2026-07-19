import locale
from decimal import Decimal, InvalidOperation
from typing import Optional
from PySide2.QtCore import Qt
from PySide2.QtGui import QDoubleValidator
from PySide2.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QListWidget,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
    QListWidgetItem
)
from sqlalchemy import select

# Import komponen database dan model
from app.database.db import SessionLocal
from app.models.models import Account, JournalEntry, Transaction

# Atur locale ke Indonesia untuk format mata uang Rupiah
try:
    locale.setlocale(locale.LC_ALL, 'id_ID.UTF-8')
except locale.Error:
    locale.setlocale(locale.LC_ALL, 'Indonesian_indonesia.1252')


class TransactionWidget(QWidget):
    """
    Widget untuk siswa (teller) melakukan transaksi setor, tarik, dan transfer.
    """

    def __init__(self, current_user_id: int):
        super().__init__()
        self.current_user_id = current_user_id

        # Cache untuk menyimpan semua data rekening dari DB, menghindari query berulang
        self.all_accounts = []

        # State untuk menyimpan rekening yang dipilih di setiap tab
        self.selected_account_setor = None
        self.selected_account_tarik = None
        self.selected_account_sumber = None
        self.selected_account_tujuan = None

        self.init_ui()
        self.refresh_data_for_tab(0)  # Muat data untuk tab pertama

    def init_ui(self):
        """Menginisialisasi UI utama dengan QTabWidget."""
        main_layout = QVBoxLayout(self)
        tab_widget = QTabWidget()
        tab_widget.currentChanged.connect(self.refresh_data_for_tab)

        # Membuat dan menambahkan setiap tab
        self.setor_tab = self._create_setor_tab()
        self.tarik_tab = self._create_tarik_tab()
        self.transfer_tab = self._create_transfer_tab()

        tab_widget.addTab(self.setor_tab, "Setor Tunai")
        tab_widget.addTab(self.tarik_tab, "Tarik Tunai")
        tab_widget.addTab(self.transfer_tab, "Transfer")

        main_layout.addWidget(tab_widget)

    # --- Metode Pembuatan Tab ---

    def _create_setor_tab(self):
        """Membuat widget dan layout untuk tab Setor Tunai."""
        container = QWidget()
        main_vbox = QVBoxLayout(container)

        # --- Grup Pencarian Rekening ---
        search_group = QGroupBox("Pilih Rekening")
        search_layout = QVBoxLayout(search_group)
        self.setor_search_input = QLineEdit()
        self.setor_search_input.setPlaceholderText("Cari no. rekening atau nama nasabah...")
        self.setor_akun_list = QListWidget()
        search_layout.addWidget(self.setor_search_input)
        search_layout.addWidget(self.setor_akun_list)

        # --- Grup Detail Transaksi ---
        form_group = QGroupBox("Detail Transaksi")
        form_layout = QFormLayout(form_group)
        self.setor_saldo_label = QLabel("Rp 0")
        self.setor_jumlah_input = QLineEdit()
        self.setor_jumlah_input.setValidator(QDoubleValidator(0.01, 10**9, 2))
        self.setor_keterangan_input = QLineEdit()
        self.setor_button = QPushButton("Proses Setoran")
        self.setor_status_label = QLabel("")
        form_layout.addRow("Saldo Saat Ini:", self.setor_saldo_label)
        form_layout.addRow("Jumlah Setor:", self.setor_jumlah_input)
        form_layout.addRow("Keterangan:", self.setor_keterangan_input)
        form_layout.addRow(self.setor_button)
        form_layout.addRow(self.setor_status_label)

        main_vbox.addWidget(search_group)
        main_vbox.addWidget(form_group)

        # --- Hubungkan Signals ---
        self.setor_search_input.textChanged.connect(lambda text: self._filter_list_widget(text, self.setor_akun_list))
        self.setor_akun_list.currentItemChanged.connect(lambda current, prev: self._on_account_selected(current, 'setor', self.setor_saldo_label))
        self.setor_button.clicked.connect(self.handle_setor)

        return container

    def _create_tarik_tab(self):
        """Membuat widget dan layout untuk tab Tarik Tunai."""
        container = QWidget()
        main_vbox = QVBoxLayout(container)

        search_group = QGroupBox("Pilih Rekening")
        search_layout = QVBoxLayout(search_group)
        self.tarik_search_input = QLineEdit()
        self.tarik_search_input.setPlaceholderText("Cari no. rekening atau nama nasabah...")
        self.tarik_akun_list = QListWidget()
        search_layout.addWidget(self.tarik_search_input)
        search_layout.addWidget(self.tarik_akun_list)

        form_group = QGroupBox("Detail Transaksi")
        form_layout = QFormLayout(form_group)
        self.tarik_saldo_label = QLabel("Rp 0")
        self.tarik_jumlah_input = QLineEdit()
        self.tarik_jumlah_input.setValidator(QDoubleValidator(0.01, 10**9, 2))
        self.tarik_keterangan_input = QLineEdit()
        self.tarik_button = QPushButton("Proses Penarikan")
        self.tarik_status_label = QLabel("")
        form_layout.addRow("Saldo Saat Ini:", self.tarik_saldo_label)
        form_layout.addRow("Jumlah Tarik:", self.tarik_jumlah_input)
        form_layout.addRow("Keterangan:", self.tarik_keterangan_input)
        form_layout.addRow(self.tarik_button)
        form_layout.addRow(self.tarik_status_label)

        main_vbox.addWidget(search_group)
        main_vbox.addWidget(form_group)

        self.tarik_search_input.textChanged.connect(lambda text: self._filter_list_widget(text, self.tarik_akun_list))
        self.tarik_akun_list.currentItemChanged.connect(lambda current, prev: self._on_account_selected(current, 'tarik', self.tarik_saldo_label))
        self.tarik_button.clicked.connect(self.handle_tarik)

        return container

    def _create_transfer_tab(self):
        """Membuat widget dan layout untuk tab Transfer."""
        container = QWidget()
        main_vbox = QVBoxLayout(container)

        # --- Grup Pemilihan Akun (Sumber & Tujuan) ---
        selection_hbox = QHBoxLayout()
        sumber_group = QGroupBox("Dari Rekening")
        sumber_layout = QVBoxLayout(sumber_group)
        self.transfer_sumber_search = QLineEdit()
        self.transfer_sumber_search.setPlaceholderText("Cari no. rekening atau nama...")
        self.transfer_sumber_list = QListWidget()
        sumber_layout.addWidget(self.transfer_sumber_search)
        sumber_layout.addWidget(self.transfer_sumber_list)

        tujuan_group = QGroupBox("Ke Rekening")
        tujuan_layout = QVBoxLayout(tujuan_group)
        self.transfer_tujuan_search = QLineEdit()
        self.transfer_tujuan_search.setPlaceholderText("Cari no. rekening atau nama...")
        self.transfer_tujuan_list = QListWidget()
        tujuan_layout.addWidget(self.transfer_tujuan_search)
        tujuan_layout.addWidget(self.transfer_tujuan_list)

        selection_hbox.addWidget(sumber_group)
        selection_hbox.addWidget(tujuan_group)

        # --- Grup Detail Transfer ---
        details_group = QGroupBox("Detail Transfer")
        form_layout = QFormLayout(details_group)
        self.transfer_saldo_label = QLabel("Rp 0")
        self.transfer_jumlah_input = QLineEdit()
        self.transfer_jumlah_input.setValidator(QDoubleValidator(0.01, 10**9, 2))
        self.transfer_keterangan_input = QLineEdit()
        self.transfer_button = QPushButton("Proses Transfer")
        self.transfer_status_label = QLabel("")
        form_layout.addRow("Saldo Sumber:", self.transfer_saldo_label)
        form_layout.addRow("Jumlah Transfer:", self.transfer_jumlah_input)
        form_layout.addRow("Keterangan:", self.transfer_keterangan_input)
        form_layout.addRow(self.transfer_button)
        form_layout.addRow(self.transfer_status_label)

        main_vbox.addLayout(selection_hbox)
        main_vbox.addWidget(details_group)

        # --- Hubungkan Signals ---
        self.transfer_sumber_search.textChanged.connect(lambda text: self._filter_list_widget(text, self.transfer_sumber_list))
        self.transfer_tujuan_search.textChanged.connect(lambda text: self._filter_list_widget(text, self.transfer_tujuan_list))
        self.transfer_sumber_list.currentItemChanged.connect(lambda current, prev: self._on_account_selected(current, 'sumber', self.transfer_saldo_label))
        self.transfer_tujuan_list.currentItemChanged.connect(lambda current, prev: self._on_account_selected(current, 'tujuan', None)) # Tujuan tidak perlu update label saldo
        self.transfer_button.clicked.connect(self.handle_transfer)

        return container

    # --- Metode Helper UI dan Data ---

    def refresh_data_for_tab(self, index):
        """Memuat ulang data (daftar rekening) untuk tab yang aktif."""
        self._refresh_all_accounts_data()  # Selalu ambil data terbaru dari DB

        if index == 0:  # Tab Setor
            self._populate_list_widget(self.setor_akun_list, self.all_accounts)
        elif index == 1:  # Tab Tarik
            self._populate_list_widget(self.tarik_akun_list, self.all_accounts)
        elif index == 2:  # Tab Transfer
            self._populate_list_widget(self.transfer_sumber_list, self.all_accounts)
            self._populate_list_widget(self.transfer_tujuan_list, self.all_accounts)

    def _refresh_all_accounts_data(self):
        """Query semua rekening dari DB dan simpan di cache self.all_accounts."""
        with SessionLocal() as db:
            # Tambahkan filter untuk hanya menampilkan rekening yang aktif (tidak di-soft-delete)
            stmt = select(Account).where(Account.is_deleted == False).order_by(Account.nama_nasabah)
            self.all_accounts = db.execute(stmt).scalars().all()

    def _populate_list_widget(self, list_widget: QListWidget, accounts: list):
        """Mengisi QListWidget dengan daftar rekening dari list yang diberikan."""
        list_widget.clear()
        for acc in accounts:
            item_text = f"{acc.nomor_rekening} - {acc.nama_nasabah} ({acc.kelas_nasabah})"
            item = QListWidgetItem(item_text, list_widget)
            item.setData(Qt.UserRole, acc.id)  # Simpan ID di item data

    def _filter_list_widget(self, text: str, list_widget: QListWidget):
        """Menyaring item di QListWidget berdasarkan teks pencarian dari cache."""
        search_term = text.lower()
        filtered_accounts = [
            acc for acc in self.all_accounts
            if search_term in acc.nama_nasabah.lower() or search_term in acc.nomor_rekening
        ]
        self._populate_list_widget(list_widget, filtered_accounts)

    def _on_account_selected(self, item, context: str, balance_label: Optional[QLabel]):
        """Slot yang dipanggil saat item di QListWidget dipilih."""
        target_attr_map = {
            'setor': 'selected_account_setor',
            'tarik': 'selected_account_tarik',
            'sumber': 'selected_account_sumber',
            'tujuan': 'selected_account_tujuan',
        }
        target_attr = target_attr_map.get(context)

        if not item or not target_attr:
            setattr(self, target_attr, None)
            if balance_label: balance_label.setText("Rp 0")
            return

        account_id = item.data(Qt.UserRole)
        selected_account = next((acc for acc in self.all_accounts if acc.id == account_id), None)

        setattr(self, target_attr, selected_account)
        if selected_account and balance_label:
            balance_label.setText(locale.currency(selected_account.saldo, grouping=True, symbol='Rp '))

    def _reset_setor_form(self):
        """Mengosongkan form setor setelah transaksi."""
        self.setor_search_input.clear()
        self.setor_akun_list.clearSelection()
        self.selected_account_setor = None
        self.setor_saldo_label.setText("Rp 0")
        self.setor_jumlah_input.clear()
        self.setor_keterangan_input.clear()
        self.setor_status_label.setText("")

    def _reset_tarik_form(self):
        """Mengosongkan form tarik setelah transaksi."""
        self.tarik_search_input.clear()
        self.tarik_akun_list.clearSelection()
        self.selected_account_tarik = None
        self.tarik_saldo_label.setText("Rp 0")
        self.tarik_jumlah_input.clear()
        self.tarik_keterangan_input.clear()
        self.tarik_status_label.setText("")

    def _reset_transfer_form(self):
        """Mengosongkan form transfer setelah transaksi."""
        self.transfer_sumber_search.clear()
        self.transfer_tujuan_search.clear()
        self.transfer_sumber_list.clearSelection()
        self.transfer_tujuan_list.clearSelection()
        self.selected_account_sumber = None
        self.selected_account_tujuan = None
        self.transfer_saldo_label.setText("Rp 0")
        self.transfer_jumlah_input.clear()
        self.transfer_keterangan_input.clear()
        self.transfer_status_label.setText("")

    # --- Metode Pemrosesan Transaksi ---

    def handle_setor(self):
        """Logika untuk memproses transaksi setor tunai."""
        selected_account = self.selected_account_setor
        jumlah_str = self.setor_jumlah_input.text().replace(',', '.')
        keterangan = self.setor_keterangan_input.text().strip()

        if not selected_account:
            self.setor_status_label.setText("Silakan pilih rekening terlebih dahulu.")
            return
        if not jumlah_str:
            self.setor_status_label.setText("Jumlah harus diisi.")
            return

        try:
            # 1. Parse input sebagai Decimal, bukan float
            jumlah = Decimal(jumlah_str)
            if jumlah <= Decimal('0'):
                raise InvalidOperation
        except InvalidOperation:
            self.setor_status_label.setText("Jumlah harus berupa angka positif yang valid.")
            return

        with SessionLocal() as db:
            try:
                # Ambil rekening dari DB, gunakan with_for_update untuk lock baris
                acc = db.get(Account, selected_account.id, with_for_update=True)
                if not acc:
                    raise Exception("Rekening tidak ditemukan.")

                acc.saldo += jumlah  # Operasi Decimal
                saldo_akhir = acc.saldo

                # Buat record transaksi
                new_trx = Transaction(
                    account_id=acc.id, jenis='setor', jumlah=jumlah,
                    saldo_akhir=saldo_akhir, teller_id=self.current_user_id,
                    keterangan=keterangan
                )
                db.add(new_trx)
                db.flush()  # Kirim ke DB untuk mendapatkan trx ID

                # Buat Jurnal Debit-Kredit
                # 1. Kas bertambah (Debit)
                jurnal_kas = JournalEntry(transaction_id=new_trx.id, akun='Kas', debit=jumlah, kredit=0)
                # 2. Tabungan Nasabah bertambah (Kredit)
                jurnal_tabungan = JournalEntry(transaction_id=new_trx.id, akun=f'Tabungan Nasabah - {acc.nama_nasabah}', debit=0, kredit=jumlah)
                db.add_all([jurnal_kas, jurnal_tabungan])

                db.commit() # Commit semua perubahan

                QMessageBox.information(self, "Sukses", f"Setoran {locale.currency(jumlah, grouping=True)} ke rekening {acc.nomor_rekening} berhasil.\nSaldo akhir: {locale.currency(saldo_akhir, grouping=True)}")
                self._reset_setor_form()
                self.refresh_data_for_tab(0) # Refresh data dan UI

            except Exception as e:
                db.rollback()
                QMessageBox.critical(self, "Error", f"Transaksi gagal: {e}")

    def handle_tarik(self):
        """Logika untuk memproses transaksi tarik tunai."""
        selected_account = self.selected_account_tarik
        jumlah_str = self.tarik_jumlah_input.text().replace(',', '.')
        keterangan = self.tarik_keterangan_input.text().strip()

        if not selected_account:
            self.tarik_status_label.setText("Silakan pilih rekening terlebih dahulu.")
            return
        if not jumlah_str:
            self.tarik_status_label.setText("Jumlah harus diisi.")
            return


        try:
            # 2. Parse input sebagai Decimal
            jumlah = Decimal(jumlah_str)
            if jumlah <= Decimal('0'):
                raise InvalidOperation
        except InvalidOperation:
            self.tarik_status_label.setText("Jumlah harus berupa angka positif yang valid.")
            return

        with SessionLocal() as db:
            try:
                acc = db.get(Account, selected_account.id, with_for_update=True)
                if not acc:
                    raise Exception("Rekening tidak ditemukan.")

                # Validasi saldo mencukupi
                if acc.saldo < jumlah: # Perbandingan Decimal vs Decimal
                    raise Exception("Saldo tidak mencukupi untuk penarikan.")

                acc.saldo -= jumlah  # Operasi Decimal
                saldo_akhir = acc.saldo

                new_trx = Transaction(
                    account_id=acc.id, jenis='tarik', jumlah=jumlah,
                    saldo_akhir=saldo_akhir, teller_id=self.current_user_id,
                    keterangan=keterangan
                )
                db.add(new_trx)
                db.flush()

                # Buat Jurnal Debit-Kredit
                # 1. Tabungan Nasabah berkurang (Debit)
                jurnal_tabungan = JournalEntry(transaction_id=new_trx.id, akun=f'Tabungan Nasabah - {acc.nama_nasabah}', debit=jumlah, kredit=0)
                # 2. Kas berkurang (Kredit)
                jurnal_kas = JournalEntry(transaction_id=new_trx.id, akun='Kas', debit=0, kredit=jumlah)
                db.add_all([jurnal_tabungan, jurnal_kas])

                db.commit()

                QMessageBox.information(self, "Sukses", f"Penarikan {locale.currency(jumlah, grouping=True)} dari rekening {acc.nomor_rekening} berhasil.\nSaldo akhir: {locale.currency(saldo_akhir, grouping=True)}")
                self._reset_tarik_form()
                self.refresh_data_for_tab(1)

            except Exception as e:
                db.rollback()
                QMessageBox.critical(self, "Error", f"Transaksi gagal: {e}")

    def handle_transfer(self):
        """Logika untuk memproses transaksi transfer antar rekening."""
        acc_sumber = self.selected_account_sumber
        acc_tujuan = self.selected_account_tujuan
        jumlah_str = self.transfer_jumlah_input.text().replace(',', '.')
        keterangan = self.transfer_keterangan_input.text().strip()

        if not all([acc_sumber, acc_tujuan, jumlah_str]):
            self.transfer_status_label.setText("Rekening sumber, tujuan, dan jumlah harus diisi.")
            return

        if acc_sumber.id == acc_tujuan.id:
            self.transfer_status_label.setText("Rekening sumber dan tujuan tidak boleh sama.")
            return

        try:
            # 3. Parse input sebagai Decimal
            jumlah = Decimal(jumlah_str)
            if jumlah <= Decimal('0'):
                raise InvalidOperation
        except InvalidOperation:
            self.transfer_status_label.setText("Jumlah harus berupa angka positif yang valid.")
            return

        with SessionLocal() as db:
            try:
                # Lock kedua rekening untuk mencegah race condition
                acc_sumber = db.get(Account, acc_sumber.id, with_for_update=True)
                acc_tujuan = db.get(Account, acc_tujuan.id, with_for_update=True)

                if not acc_sumber or not acc_tujuan:
                    raise Exception("Rekening sumber atau tujuan tidak ditemukan.")

                if acc_sumber.saldo < jumlah: # Perbandingan Decimal vs Decimal
                    raise Exception("Saldo rekening sumber tidak mencukupi.")

                # Lakukan operasi saldo
                acc_sumber.saldo -= jumlah # Operasi Decimal
                acc_tujuan.saldo += jumlah

                # 1. Buat Transaction SISI PENGIRIM (transfer_keluar)
                keterangan_sumber_base = f"Transfer ke {acc_tujuan.nomor_rekening} - {acc_tujuan.nama_nasabah}"
                keterangan_sumber = f"{keterangan_sumber_base}. {keterangan}" if keterangan else keterangan_sumber_base

                trx_keluar = Transaction(
                    account_id=acc_sumber.id, jenis='transfer_keluar', jumlah=jumlah,
                    saldo_akhir=acc_sumber.saldo, teller_id=self.current_user_id,
                    keterangan=keterangan_sumber
                )
                db.add(trx_keluar)
                db.flush() # Penting untuk mendapatkan ID trx_keluar untuk jurnal

                # 2. Buat Transaction SISI PENERIMA (transfer_masuk)
                keterangan_tujuan_base = f"Transfer masuk dari {acc_sumber.nomor_rekening} - {acc_sumber.nama_nasabah}"
                keterangan_tujuan = f"{keterangan_tujuan_base}. {keterangan}" if keterangan else keterangan_tujuan_base

                trx_masuk = Transaction(
                    account_id=acc_tujuan.id,
                    jenis='transfer_masuk',
                    jumlah=jumlah,
                    saldo_akhir=acc_tujuan.saldo,
                    teller_id=self.current_user_id,
                    keterangan=keterangan_tujuan
                )
                db.add(trx_masuk)

                # 3. Buat Jurnal Debit-Kredit, kaitkan KEDUANYA ke ID transaksi keluar
                # 1. Tabungan Nasabah Sumber berkurang (Debit)
                jurnal_debit = JournalEntry(
                    transaction_id=trx_keluar.id,
                    akun=f'Tabungan Nasabah - {acc_sumber.nama_nasabah}',
                    debit=jumlah,
                    kredit=0
                )
                # 2. Tabungan Nasabah Tujuan bertambah (Kredit)
                jurnal_kredit = JournalEntry(
                    transaction_id=trx_keluar.id,
                    akun=f'Tabungan Nasabah - {acc_tujuan.nama_nasabah}',
                    debit=0,
                    kredit=jumlah
                )
                db.add_all([jurnal_debit, jurnal_kredit])

                db.commit()

                QMessageBox.information(self, "Sukses", f"Transfer {locale.currency(jumlah, grouping=True)} dari {acc_sumber.nomor_rekening} ke {acc_tujuan.nomor_rekening} berhasil.")
                self._reset_transfer_form()
                self.refresh_data_for_tab(2) # Refresh semua combo di tab transfer

            except Exception as e:
                db.rollback()
                QMessageBox.critical(self, "Error", f"Transaksi gagal: {e}")