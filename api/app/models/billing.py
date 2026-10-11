"""Billing: transactions, payment methods, invoices, coupons (docs/02 §Billing)."""
from __future__ import annotations

import datetime as dt
import enum
import uuid

from sqlalchemy import BigInteger, Boolean, Date, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, uuid_pk


class TxnType(str, enum.Enum):
    topup = "topup"
    spend = "spend"
    refund = "refund"
    coupon = "coupon"
    referral_credit = "referral_credit"


def _enum(e, name):
    return Enum(e, name=name, values_callable=lambda x: [m.value for m in x])


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = uuid_pk()
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), index=True)
    type: Mapped[TxnType] = mapped_column(_enum(TxnType, "txn_type"))
    amount_micros: Mapped[int] = mapped_column(BigInteger)  # signed
    balance_after_micros: Mapped[int] = mapped_column(BigInteger)
    ref: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default="now()")


class PaymentMethod(TimestampMixin, Base):
    __tablename__ = "payment_methods"

    id: Mapped[uuid.UUID] = uuid_pk()
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(40), default="fake")
    provider_ref: Mapped[str] = mapped_column(String(120))
    brand: Mapped[str] = mapped_column(String(40))
    last4: Mapped[str] = mapped_column(String(4))
    exp_month: Mapped[int] = mapped_column(Integer)
    exp_year: Mapped[int] = mapped_column(Integer)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[uuid.UUID] = uuid_pk()
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), index=True)
    period_start: Mapped[dt.date] = mapped_column(Date)
    period_end: Mapped[dt.date] = mapped_column(Date)
    amount_micros: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String(20), default="paid")
    pdf_key: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default="now()")


class Coupon(Base):
    __tablename__ = "coupons"

    id: Mapped[uuid.UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    amount_micros: Mapped[int] = mapped_column(BigInteger)
    expires_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    max_redemptions: Mapped[int] = mapped_column(Integer, default=1)


class CouponRedemption(Base):
    __tablename__ = "coupon_redemptions"

    coupon_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("coupons.id", ondelete="CASCADE"), primary_key=True)
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), primary_key=True)
    at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default="now()")


class HoldoutHousehold(Base):
    __tablename__ = "holdout_households"

    campaign_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"), primary_key=True)
    household_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("households.id", ondelete="CASCADE"), primary_key=True)
