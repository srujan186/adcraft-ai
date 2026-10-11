"""Prepaid billing: balance, top-up, payment methods, transactions, coupons (account-scoped)."""
from __future__ import annotations

import secrets
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import Tenant, get_current_account, require_roles
from app.core.errors import AppError
from app.models.billing import Invoice, PaymentMethod, Transaction, TxnType
from app.models.identity import Role
from app.schemas.billing import (
    BalanceOut,
    CouponRedeem,
    PaymentMethodCreate,
    PaymentMethodOut,
    TopupRequest,
    TransactionOut,
)
from app.services.billing import redeem_coupon, topup

router = APIRouter(prefix="/billing", tags=["billing"])
_BILLING = require_roles(Role.owner, Role.admin)


def _brand(number: str) -> str:
    return {"4": "Visa", "5": "Mastercard", "3": "Amex", "6": "Discover"}.get(number[0], "Card")


@router.get("/balance", response_model=BalanceOut)
async def get_balance(tenant: Tenant = Depends(get_current_account)):
    return BalanceOut(balance_micros=tenant.account.balance_micros, currency=tenant.account.currency)


@router.get("/transactions", response_model=list[TransactionOut])
async def list_transactions(tenant: Tenant = Depends(get_current_account), db: AsyncSession = Depends(get_db)):
    rows = (
        await db.execute(
            select(Transaction).where(Transaction.account_id == tenant.account.id).order_by(Transaction.created_at.desc()).limit(200)
        )
    ).scalars().all()
    return [TransactionOut.model_validate(t) for t in rows]


@router.post("/topup", response_model=TransactionOut, status_code=201)
async def topup_balance(body: TopupRequest, tenant: Tenant = Depends(_BILLING), db: AsyncSession = Depends(get_db)):
    txn = await topup(db, tenant.account, body.amount_micros, body.payment_method_id)
    return TransactionOut.model_validate(txn)


@router.get("/payment-methods", response_model=list[PaymentMethodOut])
async def list_payment_methods(tenant: Tenant = Depends(get_current_account), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(PaymentMethod).where(PaymentMethod.account_id == tenant.account.id))).scalars().all()
    return [PaymentMethodOut.model_validate(p) for p in rows]


@router.post("/payment-methods", response_model=PaymentMethodOut, status_code=201)
async def add_payment_method(body: PaymentMethodCreate, tenant: Tenant = Depends(_BILLING), db: AsyncSession = Depends(get_db)):
    if body.is_default:
        await db.execute(update(PaymentMethod).where(PaymentMethod.account_id == tenant.account.id).values(is_default=False))
    pm = PaymentMethod(
        account_id=tenant.account.id, provider="fake", provider_ref="tok_" + secrets.token_hex(8),
        brand=_brand(body.number), last4=body.number[-4:], exp_month=body.exp_month,
        exp_year=body.exp_year, is_default=body.is_default,
    )
    db.add(pm)
    await db.commit()
    await db.refresh(pm)
    return PaymentMethodOut.model_validate(pm)


@router.delete("/payment-methods/{pm_id}", status_code=204)
async def delete_payment_method(pm_id: uuid.UUID, tenant: Tenant = Depends(_BILLING), db: AsyncSession = Depends(get_db)):
    pm = await db.get(PaymentMethod, pm_id)
    if pm is None or pm.account_id != tenant.account.id:
        raise AppError("NOT_FOUND", "Payment method not found", 404)
    await db.delete(pm)
    await db.commit()


@router.get("/receipts", response_model=list[TransactionOut])
async def list_receipts(tenant: Tenant = Depends(get_current_account), db: AsyncSession = Depends(get_db)):
    rows = (
        await db.execute(
            select(Transaction).where(Transaction.account_id == tenant.account.id, Transaction.type == TxnType.topup).order_by(Transaction.created_at.desc())
        )
    ).scalars().all()
    return [TransactionOut.model_validate(t) for t in rows]


@router.get("/invoices")
async def list_invoices(tenant: Tenant = Depends(get_current_account), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Invoice).where(Invoice.account_id == tenant.account.id))).scalars().all()
    return [{"id": str(i.id), "period_start": str(i.period_start), "period_end": str(i.period_end),
             "amount_micros": i.amount_micros, "status": i.status} for i in rows]


@router.post("/coupons/redeem", response_model=TransactionOut)
async def redeem(body: CouponRedeem, tenant: Tenant = Depends(_BILLING), db: AsyncSession = Depends(get_db)):
    txn = await redeem_coupon(db, tenant.account, body.code)
    return TransactionOut.model_validate(txn)
