"""Clean a demo environment down to the seeded demo account (P0-9).

`cleanup()` reports what it would delete; it deletes only with apply=True. Kept: the account the
demo user belongs to, plus any account a `keep_emails` user belongs to (the CLI adds ADMIN_EMAILS
so the owner keeps their own login). Users left with no account are deleted with it.
"""
from __future__ import annotations

import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.advertiser import Advertiser
from app.models.base import Base
from app.models.campaign import Campaign
from app.models.identity import Account, Membership, User
from app.models.intelligence import Elasticity


async def purge_account(db: AsyncSession, account_id: uuid.UUID) -> None:
    """Delete an account and every row it owns. Does not commit."""
    advertisers = (await db.execute(select(Advertiser.id).where(Advertiser.account_id == account_id))).scalars().all()
    if advertisers:  # keyed by advertiser, no FK
        await db.execute(delete(Elasticity).where(Elasticity.advertiser_id.in_(advertisers)))
    # High-volume tables (impressions, conversions, stats_daily, …) carry account_id without a
    # foreign key, so cascading from accounts would orphan them: clear every account_id table.
    for table in reversed(Base.metadata.sorted_tables):
        if "account_id" in table.c and table.name != "accounts":
            await db.execute(delete(table).where(table.c.account_id == account_id))
    await db.execute(delete(Account).where(Account.id == account_id))


async def _describe(db: AsyncSession, account: Account) -> dict:
    members = (await db.execute(
        select(User.email).join(Membership, Membership.user_id == User.id)
        .where(Membership.account_id == account.id).order_by(User.email))).scalars().all()
    advertisers = (await db.execute(
        select(Advertiser.name).where(Advertiser.account_id == account.id).order_by(Advertiser.name))).scalars().all()
    campaigns = (await db.execute(
        select(Campaign.name).where(Campaign.account_id == account.id).order_by(Campaign.name))).scalars().all()
    return {"id": str(account.id), "name": account.name, "created_at": account.created_at.isoformat(),
            "members": list(members), "advertisers": list(advertisers), "campaigns": list(campaigns)}


async def cleanup(db: AsyncSession, *, keep_emails: set[str], apply: bool, demo_email: str | None = None) -> dict:
    from app.services.demo import DEMO_EMAIL

    demo_email = (demo_email or DEMO_EMAIL).lower()
    keep = {e.strip().lower() for e in keep_emails if e.strip()} | {demo_email}
    kept_ids = set((await db.execute(
        select(Membership.account_id).join(User, User.id == Membership.user_id)
        .where(User.email.in_(keep)))).scalars().all())
    demo_ids = set((await db.execute(
        select(Membership.account_id).join(User, User.id == Membership.user_id)
        .where(User.email == demo_email))).scalars().all())

    accounts = (await db.execute(select(Account).order_by(Account.created_at))).scalars().all()
    report = {
        "keep": [await _describe(db, a) for a in accounts if a.id in kept_ids],
        "delete": [await _describe(db, a) for a in accounts if a.id not in kept_ids],
        "applied": False,
    }
    if not demo_ids:
        report["error"] = f"No demo account ({demo_email}). Run `seed-demo` first; nothing was deleted."
        return report
    if not apply:
        return report

    for a in accounts:
        if a.id not in kept_ids:
            await purge_account(db, a.id)
    await db.flush()
    orphans = select(Membership.id).where(Membership.user_id == User.id).exists()
    await db.execute(delete(User).where(~orphans, User.email.notin_(keep)))
    await db.commit()
    report["applied"] = True
    return report
