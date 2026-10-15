# server.py
import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import multiprocessing
multiprocessing.freeze_support()

# The pipeline logs progress with emoji. When stdout is not UTF-8 — Windows with
# output redirected to a file, or a container with a C/POSIX locale — those
# prints raise UnicodeEncodeError from inside a request handler and turn a clean
# response into a broken one. Force UTF-8 rather than police every print.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import os

from routers.scrape   import router as scrape_router
from routers.generate import router as generate_router
from routers.media    import router as media_router

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
app.include_router(media_router)

# ── Output directory ──────────────────────────────────────────────────────────
# Generated MP4s are served by GET /api/output/{filename} in routers/generate.py.
# A StaticFiles mount used to sit here too, but include_router() runs first so
# the router always won and the mount was dead — while silently implying the
# path-traversal checking StaticFiles does. The router handler does its own now.
_output_dir = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(_output_dir, exist_ok=True)

# ── Asset check ───────────────────────────────────────────────────────────────
# The Kokoro weights and the music beds are git-lfs files. A checkout or Docker
# build without `git lfs pull` leaves ~130-byte pointer files in their place;
# Kokoro then fails to load, the audio step swallows the error, and every render
# is silent while still returning "status": "done". That is expensive to notice
# from the outside, so say it loudly once at boot.
_LFS_MAGIC = b"version https://git-lfs"


def _check_assets() -> None:
    base = os.path.dirname(os.path.abspath(__file__))
    required = [
        os.path.join(base, "models", "kokoro-v1.0.int8.onnx"),
        os.path.join(base, "models", "voices-v1.0.bin"),
    ]
    music_dir = os.path.join(base, "music")
    if os.path.isdir(music_dir):
        required += [
            os.path.join(music_dir, f)
            for f in os.listdir(music_dir)
            if f.lower().endswith(".mp3")
        ]

    missing, pointers = [], []
    for path in required:
        if not os.path.exists(path):
            missing.append(os.path.basename(path))
            continue
        try:
            with open(path, "rb") as fh:
                if fh.read(len(_LFS_MAGIC)) == _LFS_MAGIC:
                    pointers.append(os.path.basename(path))
        except OSError:
            missing.append(os.path.basename(path))

    if missing:
        print(f"[assets] MISSING: {', '.join(missing)}")
    if pointers:
        print(f"[assets] git-lfs POINTERS, not real files: {', '.join(pointers)}")
    if missing or pointers:
        print("[assets] Run `git lfs pull`. Until then renders will have no audio.")
    else:
        print(f"[assets] ok - {len(required)} media files present")


_check_assets()


# ── Health / root ─────────────────────────────────────────────────────────────
# HEAD too: uptime monitors (UptimeRobot) send HEAD and count a 405 as down.
@app.api_route("/api/health", methods=["GET", "HEAD"])
async def health_check():
    return {"status": "ok", "message": "AdCraft AI is running 🚀"}

@app.get("/")
async def root():
    return {"message": "Welcome to AdCraft AI API", "docs": "/docs"}
