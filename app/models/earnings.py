"""Wallet & payouts — docs/database-schema.md § 8."""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import LedgerEntryType, PayoutMethodType, PayoutStatus


class ListenerWallet(Base):
    __tablename__ = "listener_wallets"

    listener_id = Column(
        UUID(as_uuid=True),
        ForeignKey("listener_profiles.user_id", ondelete="CASCADE"),
        primary_key=True,
    )
    available_balance = Column(Numeric(12, 2), nullable=False, server_default="0")
    pending_balance = Column(Numeric(12, 2), nullable=False, server_default="0")
    lifetime_earned = Column(Numeric(12, 2), nullable=False, server_default="0")
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class PayoutMethod(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "payout_methods"

    listener_id = Column(
        UUID(as_uuid=True),
        ForeignKey("listener_profiles.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    type = Column(
        Enum(PayoutMethodType, name="payout_method_type", create_type=False),
        nullable=False,
    )
    is_default = Column(Boolean, nullable=False, server_default="false")
    account_holder_name = Column(String(120), nullable=True)
    bank_name = Column(String(120), nullable=True)
    iban_or_account = Column(String(64), nullable=True)
    swift_code = Column(String(32), nullable=True)
    paypal_email = Column(String(255), nullable=True)
    label = Column(String(120), nullable=False)

    __table_args__ = (Index("ix_payout_methods_listener_id", "listener_id"),)


class Payout(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "payouts"

    listener_id = Column(
        UUID(as_uuid=True),
        ForeignKey("listener_profiles.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    payout_method_id = Column(
        UUID(as_uuid=True),
        ForeignKey("payout_methods.id", ondelete="RESTRICT"),
        nullable=False,
    )
    amount = Column(Numeric(12, 2), nullable=False)
    status = Column(
        Enum(PayoutStatus, name="payout_status", create_type=False),
        nullable=False,
    )
    method_label = Column(String(120), nullable=False)
    reference = Column(String(64), nullable=True)
    requested_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    processed_at = Column(DateTime(timezone=True), nullable=True)
    failure_reason = Column(Text, nullable=True)

    __table_args__ = (Index("ix_payouts_listener_id", "listener_id"),)


class WalletLedgerEntry(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "wallet_ledger_entries"

    listener_id = Column(
        UUID(as_uuid=True),
        ForeignKey("listener_profiles.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    type = Column(
        Enum(LedgerEntryType, name="ledger_entry_type", create_type=False),
        nullable=False,
    )
    amount = Column(Numeric(12, 2), nullable=False)
    balance_after = Column(Numeric(12, 2), nullable=False)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    payout_id = Column(
        UUID(as_uuid=True),
        ForeignKey("payouts.id", ondelete="SET NULL"),
        nullable=True,
    )
    idempotency_key = Column(String(64), nullable=False, unique=True)
    note = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_wallet_ledger_entries_listener_created", "listener_id", "created_at"),
    )
