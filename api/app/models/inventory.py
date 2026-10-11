"""Seeded, global taxonomy & inventory (no account_id) — docs/02 §Inventory & taxonomy.

These tables are populated by `python -m app.cli seed` (deterministic RNG seed 42).
They intentionally omit created/updated timestamps (static reference data).
"""
from __future__ import annotations

import enum
import uuid

from sqlalchemy import BigInteger, Boolean, Enum, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, uuid_pk


class ChannelCategory(str, enum.Enum):
    entertainment = "entertainment"
    news = "news"
    sports = "sports"
    kids = "kids"
    movies = "movies"
    lifestyle = "lifestyle"
    music = "music"
    spanish = "spanish"
    fast = "fast"


class GeoType(str, enum.Enum):
    country = "country"
    state = "state"
    dma = "dma"
    city = "city"
    zip = "zip"
    county = "county"
    congressional_district = "congressional_district"


def _enum(e, name):
    return Enum(e, name=name, values_callable=lambda x: [m.value for m in x])


class Household(Base):
    __tablename__ = "households"
    __table_args__ = (Index("ix_households_interests", "interests", postgresql_using="gin"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    ip_hash: Mapped[str] = mapped_column(String(64))
    zip: Mapped[str] = mapped_column(String(10), index=True)
    dma_code: Mapped[str] = mapped_column(String(8), index=True)
    state: Mapped[str] = mapped_column(String(2), index=True)
    city: Mapped[str] = mapped_column(String(120))
    county: Mapped[str] = mapped_column(String(120))
    congressional_district: Mapped[str] = mapped_column(String(16))
    timezone: Mapped[str] = mapped_column(String(40))
    age_bucket: Mapped[str] = mapped_column(String(10))
    gender: Mapped[str] = mapped_column(String(10))
    income_bucket: Mapped[str] = mapped_column(String(12))
    education: Mapped[str] = mapped_column(String(16))
    family: Mapped[str] = mapped_column(String(20))
    homeowner: Mapped[bool] = mapped_column(Boolean)
    ethnicity_affinity: Mapped[str | None] = mapped_column(String(40))
    interests: Mapped[list[str]] = mapped_column(ARRAY(String))
    device_types: Mapped[list[str]] = mapped_column(ARRAY(String))
    # viewing propensity (×100 stored as int to avoid float money/metric drift elsewhere)
    propensity_x100: Mapped[int] = mapped_column(Integer, default=100)


class Channel(Base):
    __tablename__ = "channels"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(200), index=True)
    category: Mapped[ChannelCategory] = mapped_column(_enum(ChannelCategory, "channel_category"), index=True)
    publisher: Mapped[str | None] = mapped_column(String(200))
    reach_households: Mapped[int] = mapped_column(BigInteger)
    base_cpm_micros: Mapped[int] = mapped_column(BigInteger)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    logo_url: Mapped[str | None] = mapped_column(String(1000))


class InterestSegment(Base):
    __tablename__ = "interest_segments"

    id: Mapped[uuid.UUID] = uuid_pk()
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("interest_segments.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(200), index=True)
    reach_households: Mapped[int] = mapped_column(BigInteger)


class Geo(Base):
    __tablename__ = "geos"
    __table_args__ = (Index("ix_geos_type_code", "type", "code"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    type: Mapped[GeoType] = mapped_column(_enum(GeoType, "geo_type"), index=True)
    code: Mapped[str] = mapped_column(String(40), index=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("geos.id", ondelete="SET NULL"))
    households: Mapped[int] = mapped_column(BigInteger, default=0)


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = uuid_pk()
    domain: Mapped[str] = mapped_column(String(200), index=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    industry: Mapped[str] = mapped_column(String(60))
    size_bucket: Mapped[str] = mapped_column(String(20))


class CompanyHousehold(Base):
    __tablename__ = "company_households"

    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), primary_key=True
    )
    household_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("households.id", ondelete="CASCADE"), primary_key=True
    )
