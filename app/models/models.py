from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Numeric,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

# Import 'Base' dari file db.py agar semua model yang dibuat di sini
# terdaftar dalam metadata SQLAlchemy dan bisa dibuat tabelnya oleh init_db().
from app.database.db import Base


# --- Model-model Tabel ---


class User(Base):
    """
    Model untuk tabel 'user'.
    Menyimpan data pengguna aplikasi seperti superadmin, admin, dan siswa (teller).
    """
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # 'superadmin', 'admin', 'siswa'
    nama_lengkap: Mapped[str] = mapped_column(String(100), nullable=False)
    # NIP untuk admin/guru, NIS untuk siswa, kosong untuk superadmin
    nomor_induk: Mapped[Optional[str]] = mapped_column(String(30), nullable=True, unique=True)
    # Tingkat kelas siswa, angka 1-12, opsional (misal untuk pegawai sekolah yang bukan siswa)
    kelas: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    # Kolom untuk mencatat siapa yang membuat user ini (self-referencing foreign key).
    # Nullable=True karena superadmin pertama dibuat oleh sistem, bukan oleh user lain.
    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("user.id"), nullable=True)

    # --- Kolom untuk Soft Delete ---
    # Data tidak dihapus permanen dari database, hanya ditandai is_deleted=True.
    # Ini penting untuk keperluan audit dan menjaga integritas data historis.
    # Data yang sudah di-soft-delete tidak akan muncul lagi di operasional harian.
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    deleted_by: Mapped[Optional[int]] = mapped_column(ForeignKey("user.id"), nullable=True)

    # --- Relationships (relasi ke tabel lain) ---
    # Satu User bisa memiliki banyak log login
    login_logs: Mapped[List["LoginLog"]] = relationship(back_populates="user")
    # Relationship self-referencing untuk mendapatkan objek User yang membuat user ini.
    creator: Mapped[Optional["User"]] = relationship(remote_side=[id], foreign_keys=[created_by])
    # Relationship self-referencing untuk mendapatkan objek User yang melakukan soft delete.
    deleter: Mapped[Optional["User"]] = relationship(remote_side=[id], foreign_keys=[deleted_by])

    # Satu User (admin/siswa) bisa membuat banyak rekening
    created_accounts: Mapped[List["Account"]] = relationship(
        back_populates="creator", foreign_keys="Account.created_by"
    )
    # Satu User (siswa/teller) bisa memproses banyak transaksi
    transactions_processed: Mapped[List["Transaction"]] = relationship(
        back_populates="teller", foreign_keys="Transaction.teller_id"
    )

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}')>"


class LoginLog(Base):
    """
    Model untuk tabel 'login_log'.
    Mencatat riwayat login dan logout setiap pengguna untuk audit.
    """
    __tablename__ = "login_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    login_time: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    logout_time: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Relationship ke tabel User (setiap log milik satu user)
    user: Mapped["User"] = relationship(back_populates="login_logs")


class Account(Base):
    """
    Model untuk tabel 'account'.
    Menyimpan data rekening nasabah simulasi.
    """
    __tablename__ = "account"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    nomor_rekening: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    nama_nasabah: Mapped[str] = mapped_column(String(100), nullable=False)
    # NIS siswa pemilik rekening. Terpisah dari nomor_rekening.
    # Tidak unik untuk antisipasi 1 siswa punya >1 rekening.
    nis_nasabah: Mapped[Optional[str]] = mapped_column(String(30), nullable=True, index=True)
    # Tingkat kelas nasabah, angka 1-12, OPSIONAL karena nasabah bisa juga pegawai sekolah bukan siswa
    kelas_nasabah: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    saldo: Mapped[float] = mapped_column(Numeric(15, 2), default=0.0, nullable=False)
    created_by: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    # --- Kolom untuk Soft Delete ---
    # Data tidak dihapus permanen, hanya ditandai sebagai 'deleted' untuk audit.
    # Rekening yang sudah di-soft-delete tidak akan muncul lagi di operasional harian.
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    deleted_by: Mapped[Optional[int]] = mapped_column(ForeignKey("user.id"), nullable=True)

    # Relationship ke User (siapa yang membuat rekening)
    creator: Mapped["User"] = relationship(back_populates="created_accounts", foreign_keys=[created_by])
    # Relationship ke User (siapa yang menghapus rekening)
    deleter: Mapped[Optional["User"]] = relationship(foreign_keys=[deleted_by])

    # Relationship ke Transaction (semua transaksi di rekening ini)
    transactions: Mapped[List["Transaction"]] = relationship(back_populates="account")


class Transaction(Base):
    """
    Model untuk tabel 'transaction'.
    Mencatat setiap transaksi yang terjadi (setor, tarik, transfer).
    """
    __tablename__ = "transaction"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("account.id"), nullable=False)
    jenis: Mapped[str] = mapped_column(String(20), nullable=False)  # 'setor', 'tarik', 'transfer'
    jumlah: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    saldo_akhir: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    teller_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    waktu_transaksi: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    keterangan: Mapped[Optional[str]] = mapped_column(String(255))

    # Relationship ke Account
    account: Mapped["Account"] = relationship(back_populates="transactions")
    # Relationship ke User (siapa teller yang memproses)
    teller: Mapped["User"] = relationship(back_populates="transactions_processed", foreign_keys=[teller_id])
    # Relationship ke JournalEntry
    journal_entries: Mapped[List["JournalEntry"]] = relationship(back_populates="transaction")


class JournalEntry(Base):
    """
    Model untuk tabel 'journal_entry'.
    Mencatat jurnal akuntansi (debit/kredit) untuk setiap transaksi.
    Ini penting untuk laporan keuangan dan buku besar.
    """
    __tablename__ = "journal_entry"

    id: Mapped[int] = mapped_column(primary_key=True)
    transaction_id: Mapped[int] = mapped_column(ForeignKey("transaction.id"), nullable=False)
    akun: Mapped[str] = mapped_column(String(50), nullable=False)  # Contoh: 'Kas', 'Tabungan Nasabah'
    debit: Mapped[float] = mapped_column(Numeric(15, 2), default=0.0)
    kredit: Mapped[float] = mapped_column(Numeric(15, 2), default=0.0)
    waktu: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    # Relationship ke Transaction
    transaction: Mapped["Transaction"] = relationship(back_populates="journal_entries")