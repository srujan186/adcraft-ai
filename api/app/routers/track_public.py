"""Public tracking surface: /px.js, /e ingest, /mmp postbacks (no auth)."""
from __future__ import annotations

import datetime as dt
import json
import uuid

from fastapi import APIRouter, Depends, Header, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_db
from app.models.tracking import App, AppStatus, EventSource
from app.models.tracking import Event as EventModel
from app.services.tracking import ingest_event

router = APIRouter(tags=["tracking-public"])

PX_JS = """(function(){
var ss=document.getElementsByTagName('script'),self=ss[ss.length-1];
var base=(self&&self.src?self.src.replace(/\\/px\\.js.*$/,''):location.origin);
var key=null;
function lmid(){try{var m=document.cookie.match(/_lm_id=([^;]+)/);if(m)return m[1];
var id=(window.crypto&&crypto.randomUUID?crypto.randomUUID():String(Math.random()));
document.cookie='_lm_id='+id+';max-age=31536000;path=/';return id;}catch(e){return 'anon';}}
var id=lmid();
function send(ev,props){if(!key)return;var body=JSON.stringify(Object.assign(
{k:key,ev:ev,url:location.href,ref:document.referrer,ts:Date.now(),lm_id:id},props||{}));
try{navigator.sendBeacon(base+'/e',new Blob([body],{type:'text/plain'}));}
catch(e){fetch(base+'/e',{method:'POST',body:body,keepalive:true});}}
function run(a){var c=a[0];if(c==='init')key=a[1];else if(c==='track')send(a[1],a[2]);}
var q=(window.lumen&&window.lumen.q)||[];window.lumen=function(){run(arguments);};
for(var i=0;i<q.length;i++)run(q[i]);
var p=history.pushState;history.pushState=function(){p.apply(this,arguments);send('page_view');};
window.addEventListener('popstate',function(){send('page_view');});
})();"""


@router.get("/px.js")
async def px_js() -> Response:
    return Response(content=PX_JS, media_type="application/javascript")


@router.post("/e", status_code=204)
async def ingest(
    request: Request,
    x_sim_household: str | None = Header(default=None, alias="X-Sim-Household"),
    db: AsyncSession = Depends(get_db),
) -> Response:
    try:
        payload = json.loads((await request.body()).decode() or "{}")
    except (ValueError, UnicodeDecodeError):
        return Response(status_code=204)
    key = payload.get("k")
    if key:
        client_ip = request.client.host if request.client else "0.0.0.0"
        await ingest_event(db, key, payload, x_sim_household, client_ip, request.headers.get("user-agent"))
    return Response(status_code=204)


@router.post("/mmp/{mmp}/{app_id}", status_code=204)
async def mmp_postback(
    mmp: str, app_id: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db)
) -> Response:
    app = await db.get(App, app_id)
    if app is None:
        return Response(status_code=204)
    try:
        payload = json.loads((await request.body()).decode() or "{}")
    except (ValueError, UnicodeDecodeError):
        payload = {}
    event = str(payload.get("event", "install"))
    now = dt.datetime.now(dt.timezone.utc)
    db.add(EventModel(
        ts=now, account_id=app.account_id, advertiser_id=app.advertiser_id, source=EventSource.mmp,
        event=event, revenue_micros=int(float(payload.get("revenue", 0)) * 1_000_000),
        order_id=payload.get("order_id"), raw=payload,
    ))
    app.last_postback_at = now
    app.status = AppStatus.connected
    await db.commit()
    return Response(status_code=204)
