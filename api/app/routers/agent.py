"""Ask Agent endpoints (account-scoped). Messages return JSON (SSE is the prod transport)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import Tenant, get_current_account, require_roles
from app.core.errors import AppError
from app.models.agent import AgentMessage, AgentProposal, AgentThread, ProposalStatus
from app.models.campaign import Strategy
from app.models.identity import Role
from app.services.agent import answer, configured, suggested_questions

router = APIRouter(prefix="/agent", tags=["agent"])
_EDIT = require_roles(Role.owner, Role.admin, Role.member)


class ThreadCreate(BaseModel):
    context: dict = {}


class MessageCreate(BaseModel):
    message: str


@router.get("/config")
async def agent_config(tenant: Tenant = Depends(get_current_account)):
    return {"configured": configured()}


@router.get("/suggested-questions")
async def suggested(section: str | None = None, tenant: Tenant = Depends(get_current_account)):
    return {"questions": suggested_questions(section)}


@router.post("/threads", status_code=201)
async def create_thread(body: ThreadCreate, tenant: Tenant = Depends(get_current_account), db: AsyncSession = Depends(get_db)):
    t = AgentThread(account_id=tenant.account.id, user_id=tenant.user.id if tenant.user else None, context=body.context)
    db.add(t)
    await db.commit()
    await db.refresh(t)
    return {"id": str(t.id), "context": t.context}


@router.post("/threads/{thread_id}/messages")
async def post_message(thread_id: uuid.UUID, body: MessageCreate, tenant: Tenant = Depends(_EDIT), db: AsyncSession = Depends(get_db)):
    thread = await db.get(AgentThread, thread_id)
    if thread is None or thread.account_id != tenant.account.id:
        raise AppError("NOT_FOUND", "Thread not found", 404)

    db.add(AgentMessage(thread_id=thread.id, role="user", content={"text": body.message}))
    text, proposal_action = await answer(db, tenant.account.id, thread.context or {}, body.message)
    db.add(AgentMessage(thread_id=thread.id, role="assistant", content={"text": text}))

    proposal_out = None
    if proposal_action:
        prop = AgentProposal(
            thread_id=thread.id, account_id=tenant.account.id,
            action=proposal_action, diff=proposal_action.get("diff"),
        )
        db.add(prop)
        await db.flush()
        proposal_out = {"id": str(prop.id), "diff": prop.diff, "status": prop.status.value}
    await db.commit()
    return {"answer": text, "proposal": proposal_out}


@router.post("/proposals/{proposal_id}/apply")
async def apply_proposal(proposal_id: uuid.UUID, tenant: Tenant = Depends(_EDIT), db: AsyncSession = Depends(get_db)):
    prop = await db.get(AgentProposal, proposal_id)
    if prop is None or prop.account_id != tenant.account.id:
        raise AppError("NOT_FOUND", "Proposal not found", 404)
    action = prop.action or {}
    op = action.get("op")
    if op == "duplicate_strategy":
        src = await db.get(Strategy, action["id"])
        if src and src.account_id == tenant.account.id:
            db.add(Strategy(
                campaign_id=src.campaign_id, account_id=src.account_id, name=f"{src.name} (prospecting)",
                budget_type=src.budget_type, budget_micros=src.budget_micros, start_date=src.start_date,
                end_date=src.end_date, dayparting=src.dayparting, locations=src.locations,
                placement_mode=src.placement_mode, device_types=list(src.device_types or ["tv"]),
                bidding_mode=src.bidding_mode, position=src.position + 1,
            ))
    elif op in ("update_strategy", "update_campaign"):
        from app.models.campaign import Campaign

        target = await db.get(Strategy if op == "update_strategy" else Campaign, action["id"])
        if target is not None and getattr(target, "account_id", None) == tenant.account.id:
            for k, v in (action.get("patch") or {}).items():
                setattr(target, k, v)
    prop.status = ProposalStatus.applied
    await db.commit()
    return {"id": str(prop.id), "status": prop.status.value}


@router.post("/proposals/{proposal_id}/discard")
async def discard_proposal(proposal_id: uuid.UUID, tenant: Tenant = Depends(_EDIT), db: AsyncSession = Depends(get_db)):
    prop = await db.get(AgentProposal, proposal_id)
    if prop is None or prop.account_id != tenant.account.id:
        raise AppError("NOT_FOUND", "Proposal not found", 404)
    prop.status = ProposalStatus.discarded
    await db.commit()
    return {"id": str(prop.id), "status": prop.status.value}
