import locale
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

# Import dari library reportlab
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

# Import model dari aplikasi
from app.models.models import Account, Transaction, User

# Atur locale ke Indonesia untuk format mata uang Rupiah dan tanggal
try:
    locale.setlocale(locale.LC_ALL, 'id_ID.UTF-8')
except locale.Error:
    locale.setlocale(locale.LC_ALL, 'Indonesian_indonesia.1252')

# Definisikan ukuran kertas custom untuk slip (setengah A4 portrait / A5)
A5_PORTRAIT = (148.5 * mm, 210 * mm)


def generate_slip_transaksi(transaction: Transaction, save_path: str) -> bool:
    """
    Membuat file PDF untuk slip bukti transaksi.
    Menggunakan Canvas untuk layout dengan posisi absolut.

    :param transaction: Objek Transaction yang datanya akan dicetak.
    :param save_path: Path lengkap untuk menyimpan file PDF.
    :return: True jika berhasil, atau melempar Exception jika gagal.
    """
    try:
        # Inisialisasi Canvas dengan ukuran kertas dan nama file
        c = canvas.Canvas(save_path, pagesize=A5_PORTRAIT)

        # Definisikan margin dan dimensi halaman untuk mempermudah positioning
        width, height = A5_PORTRAIT
        margin = 10 * mm

        # Posisi Y dimulai dari atas (dikurangi margin)
        y_pos = height - margin

        # --- 1. Header ---
        c.setFont('Helvetica-Bold', 16)
        c.drawCentredString(width / 2.0, y_pos, "BANK MINI SMK")
        y_pos -= 6 * mm

        c.setFont('Helvetica', 11)
        c.drawCentredString(width / 2.0, y_pos, "[Nama Sekolah]")
        y_pos -= 8 * mm

        # --- 2. Garis Pemisah Atas ---
        c.line(margin, y_pos, width - margin, y_pos)
        y_pos -= 8 * mm

        # --- 3. Detail Transaksi ---
        c.setFont('Helvetica-Bold', 14)
        c.drawCentredString(width / 2.0, y_pos, f"BUKTI {transaction.jenis.upper()}")
        y_pos -= 10 * mm

        # Menggunakan layout 2 kolom untuk detail
        c.setFont('Helvetica', 10)
        label_x = margin
        value_x = margin + 40 * mm
        line_height = 6 * mm

        # Nomor Slip
        c.drawString(label_x, y_pos, "Nomor Slip")
        c.drawString(value_x, y_pos, f": SLIP-{transaction.id:06d}")
        y_pos -= line_height

        # Waktu
        waktu_str = transaction.waktu_transaksi.strftime('%d %B %Y, %H:%M')
        c.drawString(label_x, y_pos, "Tanggal/Waktu")
        c.drawString(value_x, y_pos, f": {waktu_str}")
        y_pos -= line_height

        # Nomor Rekening
        c.drawString(label_x, y_pos, "Nomor Rekening")
        c.drawString(value_x, y_pos, f": {transaction.account.nomor_rekening}")
        y_pos -= line_height

        # Nama Nasabah
        c.drawString(label_x, y_pos, "Nama Nasabah")
        c.drawString(value_x, y_pos, f": {transaction.account.nama_nasabah}")
        y_pos -= line_height

        # Kelas Nasabah
        c.drawString(label_x, y_pos, "Kelas")
        c.drawString(value_x, y_pos, f": {transaction.account.kelas_nasabah}")
        y_pos -= line_height * 1.5  # Beri jarak lebih

        # Jumlah
        c.setFont('Helvetica-Bold', 11)
        jumlah_str = locale.currency(transaction.jumlah, grouping=True, symbol='Rp ')
        c.drawString(label_x, y_pos, "Jumlah")
        c.drawString(value_x, y_pos, f": {jumlah_str}")
        y_pos -= line_height

        # Saldo Akhir
        saldo_akhir_str = locale.currency(transaction.saldo_akhir, grouping=True, symbol='Rp ')
        c.drawString(label_x, y_pos, "Saldo Akhir")
        c.drawString(value_x, y_pos, f": {saldo_akhir_str}")
        y_pos -= line_height

        c.setFont('Helvetica', 10)  # Kembali ke font normal

        # Keterangan
        c.drawString(label_x, y_pos, "Keterangan")
        c.drawString(value_x, y_pos, f": {transaction.keterangan or '-'}")
        y_pos -= line_height

        # Teller
        c.drawString(label_x, y_pos, "Teller")
        c.drawString(value_x, y_pos, f": {transaction.teller.nama_lengkap}")
        y_pos -= 10 * mm

        # --- 4. Garis Pemisah Bawah ---
        c.line(margin, y_pos, width - margin, y_pos)
        y_pos -= 15 * mm

        # --- 5. Area Tanda Tangan ---
        # Posisi kolom tanda tangan
        col1_x = width * 0.30
        col2_x = width * 0.70

        # Label di bawah garis
        c.drawCentredString(col1_x, y_pos, "Teller")
        c.drawCentredString(col2_x, y_pos, "Nasabah")
        y_pos += 2 * mm  # Naik sedikit untuk garis

        # Garis tanda tangan
        line_len = 30 * mm
        c.line(col1_x - line_len / 2, y_pos, col1_x + line_len / 2, y_pos)
        c.line(col2_x - line_len / 2, y_pos, col2_x + line_len / 2, y_pos)

        # --- 6. Footer ---
        c.setFont('Helvetica-Oblique', 8)
        c.drawCentredString(width / 2.0, margin / 2, "Dokumen ini dicetak otomatis oleh sistem Bank Mini SMK")

        # Simpan file PDF
        c.showPage()
        c.save()
        return True
    except Exception as e:
        # Jika terjadi error, lempar exception agar bisa ditangani oleh pemanggil
        raise Exception(f"Gagal membuat slip PDF: {e}")


def _footer_canvas(canvas, doc, dicetak_oleh: Optional[str]):
    """Helper untuk menggambar footer di setiap halaman laporan rekap."""
    canvas.saveState()
    canvas.setFont('Helvetica', 9)

    # Teks footer
    waktu_cetak = datetime.now().strftime('%d %B %Y, %H:%M:%S')
    footer_text = f"Dicetak pada: {waktu_cetak}"
    if dicetak_oleh:
        footer_text += f" oleh: {dicetak_oleh}"

    # Gambar teks di bagian bawah halaman
    canvas.drawString(doc.leftMargin, doc.bottomMargin - 15 * mm, footer_text)

    # Nomor halaman
    page_num_text = f"Halaman {doc.page}"
    canvas.drawRightString(doc.width + doc.leftMargin, doc.bottomMargin - 15 * mm, page_num_text)

    canvas.restoreState()


def generate_laporan_rekap(
    transactions_list: List[Transaction],
    tanggal_mulai: datetime,
    tanggal_akhir: datetime,
    save_path: str,
    dicetak_oleh: Optional[str] = None
) -> bool:
    """
    Membuat file PDF untuk laporan rekapitulasi transaksi.
    Menggunakan SimpleDocTemplate dan Platypus untuk layout dokumen.

    :param transactions_list: List objek Transaction yang akan ditampilkan.
    :param tanggal_mulai: Tanggal awal periode laporan.
    :param tanggal_akhir: Tanggal akhir periode laporan.
    :param save_path: Path lengkap untuk menyimpan file PDF.
    :param dicetak_oleh: Nama user yang mencetak laporan (opsional).
    :return: True jika berhasil, atau melempar Exception jika gagal.
    """
    try:
        doc = SimpleDocTemplate(save_path, pagesize=A4,
                                leftMargin=15*mm, rightMargin=15*mm,
                                topMargin=15*mm, bottomMargin=25*mm)

        story = []
        styles = getSampleStyleSheet()

        # --- 1. Judul Laporan ---
        story.append(Paragraph("LAPORAN REKAP TRANSAKSI", styles['h1']))
        story.append(Paragraph("BANK MINI SMK", styles['h2']))
        story.append(Paragraph("[Nama Sekolah]", styles['h3']))
        story.append(Spacer(1, 10 * mm))

        # --- 2. Periode Laporan ---
        periode_str = f"Periode: {tanggal_mulai.strftime('%d %B %Y')} s/d {tanggal_akhir.strftime('%d %B %Y')}"
        story.append(Paragraph(periode_str, styles['Normal']))
        story.append(Spacer(1, 5 * mm))

        # --- 3. Persiapan Data Tabel ---
        table_data = [
            ["No", "Waktu", "No. Rekening", "Nama Nasabah", "Jenis", "Jumlah (Rp)", "Saldo Akhir (Rp)", "Teller"]
        ]

        total_setor = Decimal('0.0')
        total_tarik = Decimal('0.0')
        total_transfer_keluar = Decimal('0.0')
        total_transfer_masuk = Decimal('0.0')

        # Map untuk mengubah jenis transaksi raw menjadi label yang mudah dibaca
        jenis_map = {
            'setor': 'Setor',
            'tarik': 'Tarik',
            'transfer_keluar': 'Transfer Keluar',
            'transfer_masuk': 'Transfer Masuk'
        }

        for i, trx in enumerate(transactions_list):
            table_data.append([
                i + 1,
                trx.waktu_transaksi.strftime('%d/%m/%y %H:%M'),
                trx.account.nomor_rekening,
                trx.account.nama_nasabah,
                jenis_map.get(trx.jenis, trx.jenis.capitalize()),  # Gunakan map untuk label
                locale.currency(trx.jumlah, grouping=True, symbol=''),
                locale.currency(trx.saldo_akhir, grouping=True, symbol=''),
                trx.teller.nama_lengkap
            ])

            # Kalkulasi total berdasarkan jenis transaksi baru
            if trx.jenis == 'setor':
                total_setor += Decimal(trx.jumlah)
            elif trx.jenis == 'tarik':
                total_tarik += Decimal(trx.jumlah)
            elif trx.jenis == 'transfer_keluar':
                total_transfer_keluar += Decimal(trx.jumlah)
            elif trx.jenis == 'transfer_masuk':
                total_transfer_masuk += Decimal(trx.jumlah)

        # --- 4. Tabel Utama ---
        col_widths = [10*mm, 25*mm, 30*mm, 45*mm, 20*mm, 25*mm, 25*mm, 30*mm]
        main_table = Table(table_data, colWidths=col_widths)
        main_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (2, 1), (3, -1), 'LEFT'), ('ALIGN', (7, 1), (7, -1), 'LEFT'),
            ('ALIGN', (5, 1), (6, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(main_table)
        story.append(Spacer(1, 8 * mm))

        # --- 5. Tabel Ringkasan Total ---
        summary_data = [
            ['Ringkasan Total', '', ''],
            ['Total Setor Tunai', ':', locale.currency(total_setor, grouping=True, symbol='Rp ')],
            ['Total Tarik Tunai', ':', locale.currency(total_tarik, grouping=True, symbol='Rp ')],
            ['Total Transfer Keluar', ':', locale.currency(total_transfer_keluar, grouping=True, symbol='Rp ')],
            ['Total Transfer Masuk', ':', locale.currency(total_transfer_masuk, grouping=True, symbol='Rp ')],
        ]
        summary_table = Table(summary_data, colWidths=[50*mm, 5*mm, 50*mm])
        summary_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (2, 1), (2, -1), 'RIGHT'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
        ]))
        story.append(summary_table)

        # --- 6. Build PDF dengan Footer ---
        footer_func = lambda canvas, doc: _footer_canvas(canvas, doc, dicetak_oleh)
        doc.build(story, onFirstPage=footer_func, onLaterPages=footer_func)

        return True
    except Exception as e:
        raise Exception(f"Gagal membuat laporan rekap PDF: {e}")


def generate_buku_tabungan(
    account: Account,
    transactions_list: List[Transaction],
    save_path: str,
    dicetak_oleh: Optional[str] = None
) -> bool:
    """
    Membuat file PDF buku tabungan untuk satu nasabah.
    Menggunakan SimpleDocTemplate dan Platypus.

    :param account: Objek Account nasabah.
    :param transactions_list: List objek Transaction yang sudah diurutkan (LAMA ke BARU).
    :param save_path: Path lengkap untuk menyimpan file PDF.
    :param dicetak_oleh: Nama user yang mencetak laporan (opsional).
    :return: True jika berhasil, atau melempar Exception jika gagal.
    """
    try:
        doc = SimpleDocTemplate(save_path, pagesize=A4,
                                leftMargin=15*mm, rightMargin=15*mm,
                                topMargin=15*mm, bottomMargin=25*mm)

        story = []
        styles = getSampleStyleSheet()
        # Pusatkan judul
        styles['h1'].alignment = 1
        styles['h2'].alignment = 1
        styles['h3'].alignment = 1

        # --- 1. Judul Laporan ---
        story.append(Paragraph("BUKU TABUNGAN", styles['h1']))
        story.append(Paragraph("BANK MINI SMK", styles['h2']))
        story.append(Paragraph("[Nama Sekolah]", styles['h3']))
        story.append(Spacer(1, 10 * mm))

        # --- 2. Info Nasabah (menggunakan tabel tanpa border agar rapi) ---
        info_data = [
            ['Nomor Rekening', ':', account.nomor_rekening],
            ['Nama Nasabah', ':', account.nama_nasabah],
            ['Kelas Nasabah', ':', account.kelas_nasabah or '-'],
        ]
        info_table = Table(info_data, colWidths=[35*mm, 5*mm, None])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 8 * mm))

        # --- 3. Persiapan Data Tabel Transaksi ---
        table_data = [
            ["No", "Tanggal", "Keterangan", "Diinput Oleh", "Debit (Rp)", "Kredit (Rp)", "Saldo (Rp)"]
        ]

        for i, trx in enumerate(transactions_list):
            debit_val = Decimal('0.0')
            kredit_val = Decimal('0.0')

            # --- Logika Penentuan Debit/Kredit dari sudut pandang NASABAH --
            # Kredit: Uang masuk ke rekening nasabah (Setor, Transfer masuk)
            # Debit: Uang keluar dari rekening nasabah (Tarik, Transfer keluar)
            if trx.jenis in ['setor', 'transfer_masuk']:
                kredit_val = trx.jumlah
            elif trx.jenis in ['tarik', 'transfer_keluar']:
                # Karena list transaksi sudah difilter untuk nasabah ini, semua jenis
                # 'tarik' dan 'transfer_keluar' adalah pengeluaran dari rekening ini.
                debit_val = trx.jumlah

            # Keterangan transaksi: gunakan keterangan yang ada, atau jenis transaksi jika kosong
            keterangan = trx.keterangan or trx.jenis.upper()

            # Ambil nama teller, pastikan relasi sudah di-load oleh pemanggil
            teller_name = trx.teller.nama_lengkap if trx.teller else 'N/A'

            table_data.append([
                i + 1,
                trx.waktu_transaksi.strftime('%d/%m/%Y'),
                Paragraph(keterangan, styles['Normal']),
                teller_name,
                locale.currency(debit_val, grouping=True, symbol=''),
                locale.currency(kredit_val, grouping=True, symbol=''),
                locale.currency(trx.saldo_akhir, grouping=True, symbol=''),
            ])

        # --- 4. Tabel Utama ---
        # Lebar kolom disesuaikan untuk 7 kolom agar muat di A4 Portrait
        col_widths = [10*mm, 20*mm, 45*mm, 30*mm, 25*mm, 25*mm, 25*mm]
        main_table = Table(table_data, colWidths=col_widths)
        main_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8), # Ukuran font header dikecilkan sedikit
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            # Align Keterangan dan Diinput Oleh ke kiri
            ('ALIGN', (2, 1), (3, -1), 'LEFT'),
            # Align Debit, Kredit, Saldo ke kanan
            ('ALIGN', (4, 1), (6, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(main_table)
        story.append(Spacer(1, 5 * mm))

        # --- 5. Baris Saldo Akhir ---
        if transactions_list:
            saldo_terakhir = transactions_list[-1].saldo_akhir
            saldo_akhir_str = locale.currency(saldo_terakhir, grouping=True, symbol='Rp ')

            saldo_akhir_data = [['SALDO AKHIR', saldo_akhir_str]]
            saldo_akhir_table = Table(saldo_akhir_data, colWidths=[None, 35*mm])
            saldo_akhir_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
            ]))
            story.append(saldo_akhir_table)

        # --- 6. Build PDF dengan Footer ---
        footer_func = lambda canvas, doc: _footer_canvas(canvas, doc, dicetak_oleh)
        doc.build(story, onFirstPage=footer_func, onLaterPages=footer_func)

        return True
    except Exception as e:
        raise Exception(f"Gagal membuat buku tabungan PDF: {e}")


def generate_laporan_per_teller(
    teller: User,
    transactions_list: List[Transaction],
    tanggal_mulai: datetime,
    tanggal_akhir: datetime,
    save_path: str,
    dicetak_oleh: Optional[str] = None
) -> bool:
    """
    Membuat file PDF laporan transaksi yang diproses oleh seorang teller.
    Menggunakan SimpleDocTemplate dan Platypus.

    :param teller: Objek User (teller) yang laporannya dibuat.
    :param transactions_list: List objek Transaction yang sudah diurutkan (LAMA ke BARU).
    :param tanggal_mulai: Tanggal awal periode laporan.
    :param tanggal_akhir: Tanggal akhir periode laporan.
    :param save_path: Path lengkap untuk menyimpan file PDF.
    :param dicetak_oleh: Nama user yang mencetak laporan (opsional).
    :return: True jika berhasil, atau melempar Exception jika gagal.
    """
    try:
        doc = SimpleDocTemplate(save_path, pagesize=A4,
                                leftMargin=15*mm, rightMargin=15*mm,
                                topMargin=15*mm, bottomMargin=25*mm)

        story = []
        styles = getSampleStyleSheet()
        styles['h1'].alignment = 1
        styles['h2'].alignment = 1
        styles['h3'].alignment = 1

        # --- 1. Judul Laporan ---
        story.append(Paragraph("LAPORAN TRANSAKSI PER TELLER", styles['h1']))
        story.append(Paragraph("BANK MINI SMK", styles['h2']))
        story.append(Paragraph("[Nama Sekolah]", styles['h3']))
        story.append(Spacer(1, 8 * mm))

        # --- 2. Info Teller ---
        info_data = [
            ['Nama Lengkap', ':', teller.nama_lengkap],
            ['Kelas', ':', teller.kelas or '-'],
            ['Username', ':', teller.username],
        ]
        info_table = Table(info_data, colWidths=[35*mm, 5*mm, None])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 2 * mm))

        # --- 3. Periode Laporan ---
        periode_str = f"Periode: {tanggal_mulai.strftime('%d %B %Y')} s/d {tanggal_akhir.strftime('%d %B %Y')}"
        story.append(Paragraph(periode_str, styles['Normal']))
        story.append(Spacer(1, 5 * mm))

        # --- 4. Persiapan Data Tabel dan Ringkasan ---
        table_data = [
            ["No", "Tanggal", "No. Rekening", "Nama Nasabah", "Jenis", "Jumlah (Rp)", "Keterangan"]
        ]

        # Map untuk mengubah jenis transaksi raw menjadi label yang mudah dibaca
        jenis_map = {
            'setor': 'Setor',
            'tarik': 'Tarik',
            'transfer_keluar': 'Transfer Keluar',
            'transfer_masuk': 'Transfer Masuk'
        }

        count_setor, sum_setor = 0, Decimal('0.0')
        count_tarik, sum_tarik = 0, Decimal('0.0')
        count_transfer_keluar, sum_transfer_keluar = 0, Decimal('0.0')
        count_transfer_masuk, sum_transfer_masuk = 0, Decimal('0.0')

        for i, trx in enumerate(transactions_list):
            table_data.append([
                i + 1,
                trx.waktu_transaksi.strftime('%d/%m/%y %H:%M'),
                trx.account.nomor_rekening if trx.account else 'N/A',
                trx.account.nama_nasabah if trx.account else 'N/A',
                jenis_map.get(trx.jenis, trx.jenis.capitalize()),  # Gunakan map untuk label
                locale.currency(trx.jumlah, grouping=True, symbol=''),
                Paragraph(trx.keterangan or '-', styles['Normal'])
            ])

            # Kalkulasi total dan jumlah per jenis transaksi
            if trx.jenis == 'setor':
                count_setor += 1
                sum_setor += trx.jumlah
            elif trx.jenis == 'tarik':
                count_tarik += 1
                sum_tarik += trx.jumlah
            elif trx.jenis == 'transfer_keluar':
                count_transfer_keluar += 1
                sum_transfer_keluar += trx.jumlah
            elif trx.jenis == 'transfer_masuk':
                count_transfer_masuk += 1
                sum_transfer_masuk += trx.jumlah

        # --- 5. Tabel Utama ---
        col_widths = [10*mm, 25*mm, 30*mm, 40*mm, 20*mm, 25*mm, None]
        main_table = Table(table_data, colWidths=col_widths)
        main_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (2, 1), (3, -1), 'LEFT'), ('ALIGN', (6, 1), (6, -1), 'LEFT'),
            ('ALIGN', (5, 1), (5, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(main_table)
        story.append(Spacer(1, 8 * mm))

        # --- 6. Tabel Ringkasan Total ---
        total_count = count_setor + count_tarik + count_transfer_keluar + count_transfer_masuk
        summary_data = [
            ['Ringkasan Kinerja Teller', '', ''],
            ['Total Setor Tunai', ':', f"{count_setor} transaksi ({locale.currency(sum_setor, grouping=True, symbol='Rp ')})"],
            ['Total Tarik Tunai', ':', f"{count_tarik} transaksi ({locale.currency(sum_tarik, grouping=True, symbol='Rp ')})"],
            ['Total Transfer Keluar', ':', f"{count_transfer_keluar} transaksi ({locale.currency(sum_transfer_keluar, grouping=True, symbol='Rp ')})"],
            ['Total Transfer Masuk', ':', f"{count_transfer_masuk} transaksi ({locale.currency(sum_transfer_masuk, grouping=True, symbol='Rp ')})"],
            [None, None, None], # Baris kosong sebagai pemisah
            ['Total Transaksi Diproses', ':', f"{total_count} transaksi"],
        ]
        summary_table = Table(summary_data, colWidths=[50*mm, 5*mm, None])
        summary_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 6), (0, 6), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (2, 1), (2, 4), 'LEFT'),
            ('SPAN', (0, 5), (2, 5)), # Gabungkan sel untuk baris pemisah
            ('LINEABOVE', (0, 6), (2, 6), 0.5, colors.grey),
            ('TOPPADDING', (0, 6), (2, 6), 5),
        ]))
        story.append(summary_table)

        # --- 7. Build PDF dengan Footer ---
        footer_func = lambda canvas, doc: _footer_canvas(canvas, doc, dicetak_oleh)
        doc.build(story, onFirstPage=footer_func, onLaterPages=footer_func)

        return True
    except Exception as e:
        raise Exception(f"Gagal membuat laporan per teller PDF: {e}")