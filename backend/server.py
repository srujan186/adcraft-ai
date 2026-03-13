from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os 

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


@app.get("/api/health")
async def health_check():
    return{
        "status": "ok",
        "message": "AdCraft AI is running",
        "python_version":"3.11.9",
        "environment": os.getenv("NODE_ENV", "development")
    }

@app.get("/")
async def root():
    return{
        "message": "Welcome to AdCraft AI API",
        "docs": "http://localhost:8000/docs"
    }