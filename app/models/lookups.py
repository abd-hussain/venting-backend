"""Lookup & tag-link tables — docs/database-schema.md § 3."""

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class Language(Base):
    __tablename__ = "languages"

    id = Column(String(16), primary_key=True)
    name_en = Column(String(64), nullable=False)
    name_native = Column(String(64), nullable=False)
    name_ar = Column(String(64), nullable=False)
    flag_url = Column(Text, nullable=True)
    flag_emoji = Column(String(16), nullable=True)
    sort_order = Column(Integer, nullable=False, server_default="0")
    is_active = Column(Boolean, nullable=False, server_default="true")


class ComfortArea(Base):
    __tablename__ = "comfort_areas"

    id = Column(String(64), primary_key=True)
    name_en = Column(String(120), nullable=False)
    name_ar = Column(String(120), nullable=False)
    icon_emoji = Column(String(16), nullable=False, server_default="📌")
    icon_url = Column(Text, nullable=True)
    sort_order = Column(Integer, nullable=False, server_default="0")
    allows_custom_text = Column(Boolean, nullable=False, server_default="false")
    audience = Column(String(32), nullable=False, server_default="all")
    topic_group = Column(String(64), nullable=True)
    is_active = Column(Boolean, nullable=False, server_default="true")


class LifeExperience(Base):
    __tablename__ = "life_experiences"

    id = Column(String(64), primary_key=True)
    name_en = Column(String(120), nullable=False)
    name_ar = Column(String(120), nullable=False)
    sort_order = Column(Integer, nullable=False, server_default="0")
    is_active = Column(Boolean, nullable=False, server_default="true")
    image_url = Column(Text, nullable=True)


class Boundary(Base):
    __tablename__ = "boundaries"

    id = Column(String(64), primary_key=True)
    name_en = Column(String(120), nullable=False)
    name_ar = Column(String(120), nullable=False)
    icon_emoji = Column(String(16), nullable=False, server_default="🛡️")
    icon_url = Column(Text, nullable=True)
    sort_order = Column(Integer, nullable=False, server_default="0")
    allows_custom_text = Column(Boolean, nullable=False, server_default="false")
    is_active = Column(Boolean, nullable=False, server_default="true")
    image_url = Column(Text, nullable=True)


class VentorLanguage(Base):
    __tablename__ = "ventor_languages"

    ventor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("ventor_profiles.user_id", ondelete="CASCADE"),
        primary_key=True,
    )
    language_id = Column(
        String(16),
        ForeignKey("languages.id", ondelete="CASCADE"),
        primary_key=True,
    )


class VentorInterest(Base):
    __tablename__ = "ventor_interests"

    ventor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("ventor_profiles.user_id", ondelete="CASCADE"),
        primary_key=True,
    )
    comfort_area_id = Column(
        String(64),
        ForeignKey("comfort_areas.id", ondelete="CASCADE"),
        primary_key=True,
    )
    custom_text = Column(Text, nullable=True)


class ListenerLanguage(Base):
    __tablename__ = "listener_languages"

    listener_id = Column(
        UUID(as_uuid=True),
        ForeignKey("listener_profiles.user_id", ondelete="CASCADE"),
        primary_key=True,
    )
    language_id = Column(
        String(16),
        ForeignKey("languages.id", ondelete="CASCADE"),
        primary_key=True,
    )


class ListenerComfortArea(Base):
    __tablename__ = "listener_comfort_areas"

    listener_id = Column(
        UUID(as_uuid=True),
        ForeignKey("listener_profiles.user_id", ondelete="CASCADE"),
        primary_key=True,
    )
    comfort_area_id = Column(
        String(64),
        ForeignKey("comfort_areas.id", ondelete="CASCADE"),
        primary_key=True,
    )
    custom_text = Column(Text, nullable=True)


class ListenerLifeExperience(Base):
    __tablename__ = "listener_life_experiences"

    listener_id = Column(
        UUID(as_uuid=True),
        ForeignKey("listener_profiles.user_id", ondelete="CASCADE"),
        primary_key=True,
    )
    life_experience_id = Column(
        String(64),
        ForeignKey("life_experiences.id", ondelete="CASCADE"),
        primary_key=True,
    )
    custom_label = Column(String(120), nullable=True)


class ListenerBoundary(Base):
    __tablename__ = "listener_boundaries"

    listener_id = Column(
        UUID(as_uuid=True),
        ForeignKey("listener_profiles.user_id", ondelete="CASCADE"),
        primary_key=True,
    )
    boundary_id = Column(
        String(64),
        ForeignKey("boundaries.id", ondelete="CASCADE"),
        primary_key=True,
    )
    custom_text = Column(Text, nullable=True)
