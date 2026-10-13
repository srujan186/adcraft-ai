"""P0-2: the agent answers from live campaign data through Claude, and never states facts without it.

The plan's verify case is a draft with no pixel, no creative, no audiences and manual bidding
at a $3 max CPM. The LLM is replaced by a fake client so these tests check what we *send*
(the live context) and how we handle what comes back, without spending on real calls.
"""
import asyncio
import json
from types import SimpleNamespace

import pytest
from sqlalchemy import select

import app.services.agent as agent
from app.core.config import settings
from app.models.agent import AgentProposal
from app.models.campaign import Strategy
from app.models.inventory import Channel, ChannelCategory
from tests.conftest import TestSessionLocal, signup

# Floors $8 … $30 → median $19, cheapest $8. A $3 max CPM is below all of them.
FLOORS_USD = [8, 12, 19, 24, 30]


def _channels():
    async def go():
        async with TestSessionLocal() as db:
            db.add_all([Channel(name=f"Channel {i}", category=ChannelCategory.entertainment,
                                reach_households=1_000_000, base_cpm_micros=usd * 1_000_000)
                        for i, usd in enumerate(FLOORS_USD)])
            await db.commit()
    asyncio.run(go())


_ACCOUNT: dict[str, str] = {}  # auth header -> account id, for calling build_context directly


def _signup(client, email, company="Acme"):
    s = signup(client, email, company)
    _ACCOUNT[s["headers"]["Authorization"]] = s["account_id"]
    return s["headers"]


def _draft(client, email="ctx@acme.io", *, pixel=False):
    h = _signup(client, email)
    _channels()
    adv = client.post("/api/v1/advertisers", headers=h, json={
        "name": "Nimbus", "industry": "ecommerce", "timezone": "America/New_York"}).json()["id"]
    if pixel:
        client.post(f"/api/v1/advertisers/{adv}/pixel", headers=h, json={"install_method": "manual"})
    camp = client.post("/api/v1/campaigns", headers=h, json={
        "advertiser_id": adv, "name": "Spring push", "goal": "sales", "kpi": "cpp"}).json()
    sid = camp["strategies"][0]["id"]
    r = client.patch(f"/api/v1/strategies/{sid}", headers=h, json={
        "bidding_mode": "manual", "max_cpm_micros": 3_000_000})
    assert r.status_code == 200, r.text
    return h, camp["id"], sid


def _context(client, h, cid):
    async def go():
        async with TestSessionLocal() as db:
            return await agent.build_context(db, _ACCOUNT[h["Authorization"]], {"campaign_id": cid, "section": "audience"})
    return asyncio.run(go())


def _ask(client, h, cid, message, thread=None):
    if thread is None:
        thread = client.post("/api/v1/agent/threads", headers=h,
                             json={"context": {"campaign_id": cid, "section": "audience"}}).json()["id"]
    r = client.post(f"/api/v1/agent/threads/{thread}/messages", headers=h, json={"message": message})
    assert r.status_code == 200, r.text
    return thread, r.json()


# ── fake Claude ────────────────────────────────────────────────────────────────
class FakeClaude:
    def __init__(self, *responses):
        self.calls: list[dict] = []
        self._responses = list(responses)
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))

    async def _create(self, **kwargs):
        self.calls.append(kwargs)
        r = self._responses.pop(0) if self._responses else _text("OK")
        if isinstance(r, Exception):
            raise r
        return r


def _text(t, stop="end_turn"):
    return SimpleNamespace(stop_reason=stop, content=[SimpleNamespace(type="text", text=t)])


def _tool(name, args, preface="Here's the change I'd make."):
    return SimpleNamespace(stop_reason="tool_use", content=[
        SimpleNamespace(type="text", text=preface),
        SimpleNamespace(type="tool_use", id="toolu_1", name=name, input=args),
    ])


@pytest.fixture()
def claude(monkeypatch):
    monkeypatch.setattr(settings, "anthropic_api_key", "sk-test")
    fake = FakeClaude()
    monkeypatch.setattr(agent, "_client", lambda: fake)
    return fake


# ── live context ───────────────────────────────────────────────────────────────
def test_context_describes_the_plan_draft(client):
    h, cid, sid = _draft(client)
    ctx = _context(client, h, cid)

    assert ctx["campaign"]["name"] == "Spring push"
    assert ctx["campaign"]["goal"] == "sales" and ctx["campaign"]["status"] == "draft"
    assert ctx["tracking"]["pixel"] == "none"
    assert ctx["tracking"]["events_seen_last_7_days"] == []
    assert ctx["audiences"]["usable"] == []

    (s,) = ctx["strategies"]
    assert s["id"] == sid
    assert s["bidding"] == {"mode": "manual", "max_cpm": "$3.00"}
    assert s["creatives"] == []
    assert s["audiences"]["include"] == []
    assert s["estimate"]["deliverability"] in {"insufficient", "limited", "good", "excellent"}

    assert ctx["inventory"]["median_cpm_floor"] == "$19.00"
    assert ctx["inventory"]["cheapest_cpm_floor"] == "$8.00"

    codes = {i["code"] for i in ctx["validation_issues"]}
    assert {"MISSING_TRACKING", "NO_CREATIVE", "MANUAL_CPM_BELOW_FLOOR"} <= codes

    m = ctx["metrics_last_14_days"]
    assert m["impressions"] == 0 and m["spend"] == "$0.00"
    assert ctx["open_recommendations"] == []


def test_audiences_under_1000_households_are_not_usable(client):
    # A fresh pixel creates Visitors/Leads/Purchasers with 0 matched households.
    h, cid, _ = _draft(client, "small@acme.io", pixel=True)
    ctx = _context(client, h, cid)
    assert ctx["tracking"]["pixel"] != "none"
    assert ctx["audiences"]["usable"] == []
    too_small = {a["name"] for a in ctx["audiences"]["too_small"]}
    assert {"Visitors", "Leads", "Purchasers"} <= too_small


def test_context_ignores_another_accounts_campaign(client):
    _, theirs, _ = _draft(client, "owner@acme.io")
    h = _signup(client, "intruder@acme.io", "Other")
    ctx = _context(client, h, theirs)
    assert "campaign" not in ctx and "strategies" not in ctx


# ── no key: no facts ───────────────────────────────────────────────────────────
def test_without_a_key_the_agent_states_no_facts(client, monkeypatch):
    monkeypatch.setattr(settings, "anthropic_api_key", None)
    h, cid, _ = _draft(client, "nokey@acme.io", pixel=True)
    _, r = _ask(client, h, cid, "What audience should I target?")

    a = r["answer"]
    assert "isn't available" in a
    for claim in ("Visitors", "Purchasers", "highest-intent", "$", "your campaign"):
        assert claim not in a
    assert r["proposal"] is None
    assert r["help"] and all(x["href"].startswith("/help/") for x in r["help"])
    assert any("audience" in x["title"].lower() for x in r["help"])


def test_llm_failure_shows_the_notice_not_canned_facts(client, claude):
    claude._responses = [RuntimeError("upstream 529")]
    h, cid, _ = _draft(client, "down@acme.io", pixel=True)
    _, r = _ask(client, h, cid, "What audience should I target?")
    assert "isn't available" in r["answer"] and "Visitors" not in r["answer"]
    assert r["help"]


# ── what we send to Claude ─────────────────────────────────────────────────────
def test_request_carries_live_context(client, claude):
    claude._responses = [_text("**Short answer**\nYour max CPM is $3.00.")]
    h, cid, sid = _draft(client, "shape@acme.io")
    _, r = _ask(client, h, cid, "what is my max CPM and is it too low?")
    assert r["answer"].startswith("**Short answer**")
    assert r["help"] == []

    (call,) = claude.calls
    assert call["model"] == "claude-opus-5-5"
    assert call["thinking"] == {"type": "adaptive"}
    assert call["output_config"]["effort"] in {"low", "medium", "high"}
    assert call["max_tokens"] >= 16000
    assert call["betas"] == ["server-side-fallback-2026-07-01"]
    assert call["fallbacks"] == "default"

    # system prompt is constant (cacheable); the live data rides in the user turn
    assert call["system"] == agent.SYSTEM_PROMPT
    assert "$3.00" not in call["system"]
    last = call["messages"][-1]
    assert last["role"] == "user"
    body = "".join(b["text"] for b in last["content"])
    assert "what is my max CPM and is it too low?" in body
    ctx = json.loads(body.split("<context>")[1].split("</context>")[0])
    assert ctx["strategies"][0]["bidding"]["max_cpm"] == "$3.00"
    assert ctx["inventory"]["median_cpm_floor"] == "$19.00"
    assert ctx["tracking"]["pixel"] == "none"


def test_prior_turns_are_sent_as_history(client, claude):
    claude._responses = [_text("First answer."), _text("Second answer.")]
    h, cid, _ = _draft(client, "history@acme.io")
    thread, _ = _ask(client, h, cid, "first question")
    _ask(client, h, cid, "second question", thread=thread)

    msgs = claude.calls[1]["messages"]
    assert [m["role"] for m in msgs] == ["user", "assistant", "user"]
    assert msgs[0]["content"] == "first question"
    assert msgs[1]["content"] == "First answer."


def test_refusal_is_handled(client, claude):
    claude._responses = [SimpleNamespace(stop_reason="refusal", content=[])]
    h, cid, _ = _draft(client, "refuse@acme.io")
    _, r = _ask(client, h, cid, "something odd")
    assert "can't help with that" in r["answer"]
    assert r["proposal"] is None


# ── proposals ──────────────────────────────────────────────────────────────────
def test_tool_call_becomes_a_reviewable_proposal(client, claude):
    h, cid, sid = _draft(client, "prop@acme.io")
    claude._responses = [_tool("propose_change", {
        "op": "update_strategy", "strategy_id": sid, "max_cpm_usd": 20, "summary": "Raise max CPM to $20"})]
    _, r = _ask(client, h, cid, "raise my max CPM to something that will deliver")

    assert r["proposal"] is not None
    assert "$20" in r["proposal"]["diff"]
    client.post(f"/api/v1/agent/proposals/{r['proposal']['id']}/apply", headers=h)
    s = next(x for x in client.get(f"/api/v1/campaigns/{cid}/strategies", headers=h).json() if x["id"] == sid)
    assert s["max_cpm_micros"] == 20_000_000


def test_tool_call_for_an_unknown_strategy_is_dropped(client, claude):
    h, cid, _ = _draft(client, "bogus@acme.io")
    claude._responses = [_tool("propose_change", {
        "op": "update_strategy", "strategy_id": "00000000-0000-0000-0000-000000000000", "budget_usd": 999})]
    _, r = _ask(client, h, cid, "change it")
    assert r["proposal"] is None
    assert r["answer"]  # the model's text still comes through


def test_apply_ignores_fields_outside_the_allow_list(client):
    h, cid, sid = _draft(client, "allow@acme.io")
    thread = client.post("/api/v1/agent/threads", headers=h, json={"context": {"campaign_id": cid}}).json()["id"]

    async def plant():
        async with TestSessionLocal() as db:
            s = await db.get(Strategy, sid)
            p = AgentProposal(thread_id=thread, account_id=s.account_id, diff="x", action={
                "op": "update_strategy", "id": sid,
                "patch": {"name": "renamed", "account_id": "00000000-0000-0000-0000-000000000000",
                          "budget_micros": 70_000_000}})
            db.add(p)
            await db.commit()
            return str(p.id)
    pid = asyncio.run(plant())
    client.post(f"/api/v1/agent/proposals/{pid}/apply", headers=h)

    async def read():
        async with TestSessionLocal() as db:
            return (await db.execute(select(Strategy).where(Strategy.id == sid))).scalar_one()
    s = asyncio.run(read())
    assert s.budget_micros == 70_000_000
    assert s.name != "renamed"


# ── Groq (free tier) ───────────────────────────────────────────────────────────
class FakeGroq:
    def __init__(self, *responses):
        self.calls: list[dict] = []
        self._responses = list(responses)
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    async def _create(self, **kwargs):
        self.calls.append(kwargs)
        r = self._responses.pop(0) if self._responses else _g_text("OK")
        if isinstance(r, Exception):
            raise r
        return r


def _g_text(t):
    return SimpleNamespace(choices=[SimpleNamespace(
        finish_reason="stop", message=SimpleNamespace(content=t, tool_calls=None))])


def _g_tool(name, args, preface=None):
    call = SimpleNamespace(id="call_1", type="function",
                           function=SimpleNamespace(name=name, arguments=json.dumps(args)))
    return SimpleNamespace(choices=[SimpleNamespace(
        finish_reason="tool_calls", message=SimpleNamespace(content=preface, tool_calls=[call]))])


@pytest.fixture()
def groq(monkeypatch):
    monkeypatch.setattr(settings, "anthropic_api_key", None)
    monkeypatch.setattr(settings, "groq_api_key", "gsk_test")
    fake = FakeGroq()
    monkeypatch.setattr(agent, "_groq_client", lambda: fake)
    return fake


def test_groq_request_carries_live_context(client, groq):
    groq._responses = [_g_text("**Short answer**\nYour max CPM is $3.00.")]
    h, cid, _ = _draft(client, "groq@acme.io")
    assert client.get("/api/v1/agent/config", headers=h).json()["configured"] is True
    _, r = _ask(client, h, cid, "what is my max CPM and is it too low?")
    assert r["answer"].startswith("**Short answer**") and r["help"] == []

    (call,) = groq.calls
    assert call["model"] == "openai/gpt-oss-120b"
    assert call["reasoning_effort"] in {"low", "medium", "high"}
    assert call["tools"][0]["function"]["name"] == "propose_change"
    assert call["messages"][0] == {"role": "system", "content": agent.SYSTEM_PROMPT}
    last = call["messages"][-1]
    assert last["role"] == "user" and "what is my max CPM and is it too low?" in last["content"]
    ctx = json.loads(last["content"].split("<context>")[1].split("</context>")[0])
    assert ctx["strategies"][0]["bidding"]["max_cpm"] == "$3.00"
    assert ctx["inventory"]["cheapest_cpm_floor"] == "$8.00"
    assert ctx["tracking"]["pixel"] == "none"


def test_groq_tool_call_becomes_a_proposal(client, groq):
    h, cid, sid = _draft(client, "groqprop@acme.io")
    groq._responses = [_g_tool("propose_change", {"op": "update_strategy", "strategy_id": sid,
                                                  "bidding_mode": "automatic"})]
    groq._responses.append(_g_text("Switching to automatic bidding lets you win at market prices."))
    _, r = _ask(client, h, cid, "switch me to automatic bidding")
    assert r["proposal"] is not None and "automatic" in r["proposal"]["diff"]
    # the model sent only the tool call, so the result went back and it explained the change
    assert r["answer"] == "Switching to automatic bidding lets you win at market prices."
    second = groq.calls[1]
    assert second["tool_choice"] == "none"
    assert second["messages"][-1]["role"] == "tool" and "automatic" in second["messages"][-1]["content"]


def test_groq_failure_shows_the_notice(client, groq):
    groq._responses = [RuntimeError("429 rate limit")]
    h, cid, _ = _draft(client, "groqdown@acme.io")
    _, r = _ask(client, h, cid, "What audience should I target?")
    assert "isn't available" in r["answer"] and r["help"]


def test_groq_key_in_the_anthropic_variable_is_routed_to_groq(client, monkeypatch):
    monkeypatch.setattr(settings, "groq_api_key", None)
    monkeypatch.setattr(settings, "anthropic_api_key", "gsk_misplaced")
    fake = FakeGroq(_g_text("Routed to Groq."))
    monkeypatch.setattr(agent, "_groq_client", lambda: fake)
    h, cid, _ = _draft(client, "misplaced@acme.io")
    _, r = _ask(client, h, cid, "hi")
    assert r["answer"] == "Routed to Groq." and len(fake.calls) == 1
