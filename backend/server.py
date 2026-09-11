# server.py
import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import multiprocessing
multiprocessing.freeze_support()

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import os

from routers.scrape   import router as scrape_router
from routers.generate import router as generate_router

load_dotenv()

app = FastAPI(
    title="AdCraft AI",
    description="Generate video ads from any business URL",
    version="1.0.0"
)

# ── CORS ──────────────────────────────────────────────────────────────────────
# ALLOWED_ORIGINS in .env can be comma-separated for multiple origins, e.g.:
#   ALLOWED_ORIGINS=http://localhost:3000,http://152.x.x.x
_raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Validation errors ─────────────────────────────────────────────────────────
# FastAPI's default 422 body puts a *list of objects* in `detail`. Every other
# error this API returns puts a plain string there, and the frontend does
# `throw new Error(json.detail)` — which would render "[object Object]".
# Flatten it so one shape holds across the whole API.
@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    parts = []
    for err in exc.errors():
        # loc is like ("body", "duration") — the field name is the useful part.
        field = ".".join(str(x) for x in err.get("loc", []) if x != "body")
        msg   = err.get("msg", "invalid value")
        parts.append(f"{field}: {msg}" if field else msg)

    return JSONResponse(
        status_code=422,
        content={"detail": "; ".join(parts) or "Invalid request."},
    )


# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(scrape_router)
app.include_router(generate_router)

# ── Output directory ──────────────────────────────────────────────────────────
# Generated MP4s are served by GET /api/output/{filename} in routers/generate.py.
# A StaticFiles mount used to sit here too, but include_router() runs first so
# the router always won and the mount was dead — while silently implying the
# path-traversal checking StaticFiles does. The router handler does its own now.
_output_dir = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(_output_dir, exist_ok=True)

# ── Health / root ─────────────────────────────────────────────────────────────
@app.get("/api/health")
async def health_check():
    return {"status": "ok", "message": "AdCraft AI is running 🚀"}

@app.get("/")
async def root():
    return {"message": "Welcome to AdCraft AI API", "docs": "/docs"}
