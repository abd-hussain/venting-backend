"""Rewards & invites — docs/database-schema.md § 9."""

import uuid

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import EarningsTier, InviteStatus, PointPurchaseStatus, RewardOfferKind


class RewardOffer(Base):
    __tablename__ = "reward_offers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(64), nullable=False, unique=True)
    kind = Column(
        Enum(RewardOfferKind, name="reward_offer_kind", create_type=False),
        nullable=False,
    )
    points_cost = Column(Integer, nullable=False)
    percent_off = Column(Integer, nullable=True)
    free_minutes = Column(Integer, nullable=True)
    min_tier = Column(
        Enum(EarningsTier, name="earnings_tier", create_type=False),
        nullable=True,
    )
    max_tier = Column(
        Enum(EarningsTier, name="earnings_tier", create_type=False),
        nullable=True,
    )
    is_welcome_gift = Column(Boolean, nullable=False, server_default="false")
    is_active = Column(Boolean, nullable=False, server_default="true")
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class RewardTrade(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "reward_trades"

    ventor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("ventor_profiles.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    offer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("reward_offers.id", ondelete="RESTRICT"),
        nullable=False,
    )
    points_spent = Column(Integer, nullable=False)
    is_welcome_gift = Column(Boolean, nullable=False, server_default="false")
    traded_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (Index("ix_reward_trades_ventor_id", "ventor_id"),)


class InviteCode(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "invite_codes"

    ventor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("ventor_profiles.user_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    code = Column(String(32), nullable=False, unique=True)
    invite_link = Column(Text, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    refreshed_at = Column(DateTime(timezone=True), nullable=True)


class InviteEvent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "invite_events"

    invite_code_id = Column(
        UUID(as_uuid=True),
        ForeignKey("invite_codes.id", ondelete="CASCADE"),
        nullable=False,
    )
    inviter_ventor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("ventor_profiles.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    invitee_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    invitee_display_name = Column(String(120), nullable=False)
    status = Column(
        Enum(InviteStatus, name="invite_status", create_type=False),
        nullable=False,
    )
    points_earned = Column(Integer, nullable=False, server_default="0")

    __table_args__ = (
        Index("ix_invite_events_inviter_status", "inviter_ventor_id", "status"),
    )


class PointPackage(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "point_packages"

    code = Column(String(64), nullable=False, unique=True)
    points = Column(Integer, nullable=False)
    price_usd = Column(Numeric(10, 2), nullable=False)
    bonus_percent = Column(Integer, nullable=True)
    sort_order = Column(Integer, nullable=False, server_default="0")
    is_active = Column(Boolean, nullable=False, server_default="true")

    __table_args__ = (Index("ix_point_packages_active_sort", "is_active", "sort_order"),)


class PointPurchase(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "point_purchases"

    ventor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("ventor_profiles.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    package_id = Column(
        UUID(as_uuid=True),
        ForeignKey("point_packages.id", ondelete="RESTRICT"),
        nullable=False,
    )
    package_code = Column(String(64), nullable=False)
    points_added = Column(Integer, nullable=False)
    price_usd = Column(Numeric(10, 2), nullable=False)
    payment_provider = Column(String(32), nullable=True)
    payment_reference = Column(String(128), nullable=True)
    status = Column(
        Enum(PointPurchaseStatus, name="point_purchase_status", create_type=False),
        nullable=False,
    )
    purchased_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_point_purchases_ventor_purchased", "ventor_id", "purchased_at"),
        UniqueConstraint("payment_reference", name="uq_point_purchases_payment_reference"),
    )
