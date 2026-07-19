# test_pdf.py
# Script SEMENTARA untuk test fungsi generate PDF secara standalone (tanpa GUI).
# Jalankan dengan: python test_pdf.py
# Setelah selesai testing, file ini boleh dihapus.

from datetime import datetime

from app.database.db import SessionLocal
from app.models.models import Transaction
from app.controllers.pdf_generator import generate_slip_transaksi, generate_laporan_rekap
from sqlalchemy import select
from sqlalchemy.orm import joinedload

with SessionLocal() as db:
    # Ambil 1 transaksi paling baru untuk test slip
    stmt = (
        select(Transaction)
        .options(joinedload(Transaction.account), joinedload(Transaction.teller))
        .order_by(Transaction.id.desc())
        .limit(1)
    )
    latest_transaction = db.execute(stmt).scalars().first()

    if not latest_transaction:
        print("❌ Tidak ada data transaksi di database. Lakukan 1 transaksi dulu lewat aplikasi.")
    else:
        print(f"📄 Membuat slip untuk transaksi ID {latest_transaction.id}...")
        try:
            generate_slip_transaksi(latest_transaction, "test_slip.pdf")
            print("✅ Slip berhasil dibuat: test_slip.pdf")
        except Exception as e:
            print(f"❌ Gagal membuat slip: {e}")

        # Ambil beberapa transaksi untuk test laporan rekap
        stmt_all = (
            select(Transaction)
            .options(joinedload(Transaction.account), joinedload(Transaction.teller))
            .order_by(Transaction.waktu_transaksi.desc())
            .limit(10)
        )
        transactions = db.execute(stmt_all).scalars().all()

        print(f"📄 Membuat laporan rekap dari {len(transactions)} transaksi terakhir...")
        try:
            generate_laporan_rekap(
                transactions,
                tanggal_mulai=datetime(2026, 1, 1),
                tanggal_akhir=datetime.now(),
                save_path="test_laporan.pdf",
                dicetak_oleh="Test Script"
            )
            print("✅ Laporan berhasil dibuat: test_laporan.pdf")
        except Exception as e:
            print(f"❌ Gagal membuat laporan: {e}")