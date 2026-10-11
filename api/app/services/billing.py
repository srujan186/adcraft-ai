"""Prepaid balance: top-up (FakePaymentProvider), coupon redeem, spend debit (used by M8)."""
from __future__ import annotations

import datetime as dt

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.billing import Coupon, CouponRedemption, Transaction, TxnType
from app.models.identity import Account


async def adjust_balance(db: AsyncSession, account: Account, amount_micros: int, txn_type: TxnType, ref: dict | None = None) -> Transaction:
    account.balance_micros = (account.balance_micros or 0) + amount_micros
    txn = Transaction(
        account_id=account.id, type=txn_type, amount_micros=amount_micros,
        balance_after_micros=account.balance_micros, ref=ref or {},
    )
    db.add(txn)
    return txn


async def topup(db: AsyncSession, account: Account, amount_micros: int, payment_method_id=None) -> Transaction:
    if amount_micros <= 0:
        raise AppError("INVALID_AMOUNT", "Top-up amount must be positive", 400)
    # FakePaymentProvider always succeeds in dev
    txn = await adjust_balance(db, account, amount_micros, TxnType.topup, {"payment_method_id": str(payment_method_id) if payment_method_id else None})
    await db.commit()
    await db.refresh(txn)
    return txn


async def redeem_coupon(db: AsyncSession, account: Account, code: str) -> Transaction:
    coupon = (await db.execute(select(Coupon).where(Coupon.code == code))).scalar_one_or_none()
    if coupon is None:
        raise AppError("INVALID_COUPON", "Coupon not found", 404)
    if coupon.expires_at and coupon.expires_at < dt.datetime.now(dt.timezone.utc):
        raise AppError("COUPON_EXPIRED", "This coupon has expired", 400)
    used = (await db.execute(select(func.count()).select_from(CouponRedemption).where(CouponRedemption.coupon_id == coupon.id))).scalar_one()
    if used >= coupon.max_redemptions:
        raise AppError("COUPON_EXHAUSTED", "This coupon has no remaining redemptions", 400)
    already = await db.get(CouponRedemption, {"coupon_id": coupon.id, "account_id": account.id})
    if already is not None:
        raise AppError("COUPON_ALREADY_USED", "You already redeemed this coupon", 400)

    db.add(CouponRedemption(coupon_id=coupon.id, account_id=account.id))
    txn = await adjust_balance(db, account, coupon.amount_micros, TxnType.coupon, {"code": code})
    await db.commit()
    await db.refresh(txn)
    return txn
