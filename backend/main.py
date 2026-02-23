"""
Beacon Backend - FastAPI app.
Run from repo root: uvicorn backend.main:app --reload
"""
import os

from dotenv import load_dotenv

# Load .env from backend/ when run from repo root
_backend_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_backend_dir, ".env"))
load_dotenv()  # Also allow repo root .env

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers import match, conversations

app = FastAPI(title="Beacon API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        os.getenv("FRONTEND_ORIGIN", "http://localhost:3000"),
        "https://beacs.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(match.router)
app.include_router(conversations.router)


@app.get("/health")
def health():
    return {"status": "ok"}
