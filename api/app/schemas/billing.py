from __future__ import annotations

import datetime as dt
import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.models.billing import TxnType


class BalanceOut(BaseModel):
    balance_micros: int
    currency: str = "USD"


class TopupRequest(BaseModel):
    amount_micros: int = Field(gt=0)
    payment_method_id: uuid.UUID | None = None


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    type: TxnType
    amount_micros: int
    balance_after_micros: int
    ref: dict
    created_at: dt.datetime


class PaymentMethodCreate(BaseModel):
    number: str = Field(min_length=12, max_length=19)
    exp_month: int = Field(ge=1, le=12)
    exp_year: int = Field(ge=2024, le=2099)
    is_default: bool = True


class PaymentMethodOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    brand: str
    last4: str
    exp_month: int
    exp_year: int
    is_default: bool


class CouponRedeem(BaseModel):
    code: str
