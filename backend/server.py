# server.py
import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

# Import ALL routers
from routers.scrape   import router as scrape_router
from routers.generate import router as generate_router    # ← NEW

load_dotenv()

app = FastAPI(
    title="AdCraft AI",
    description="Generate video ads from any business URL",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL", "http://localhost:3000")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(scrape_router)
app.include_router(generate_router)    # ← NEW

@app.get("/api/health")
async def health_check():
    return {
        "status":  "ok",
        "message": "AdCraft AI is running 🚀"
    }

@app.get("/")
async def root():
    return {
        "message": "Welcome to AdCraft AI API",
        "docs":    "http://localhost:8000/docs"
    }