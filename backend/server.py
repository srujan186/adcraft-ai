# server.py
import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import multiprocessing
multiprocessing.freeze_support()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
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

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(scrape_router)
app.include_router(generate_router)

# ── Static video files ────────────────────────────────────────────────────────
# Serve generated MP4s at /api/output/<filename>
_output_dir = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(_output_dir, exist_ok=True)
app.mount("/api/output", StaticFiles(directory=_output_dir), name="output")

# ── Health / root ─────────────────────────────────────────────────────────────
@app.get("/api/health")
async def health_check():
    return {"status": "ok", "message": "AdCraft AI is running 🚀"}

@app.get("/")
async def root():
    return {"message": "Welcome to AdCraft AI API", "docs": "/docs"}
