import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from app.api import corrections, documents, search, uploads
from app.config import settings
from app.database import Base, engine

app = FastAPI(title="AI Document Intelligence", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(uploads.router)
app.include_router(documents.router)
app.include_router(search.router)
app.include_router(corrections.router)


@app.on_event("startup")
def startup():
    os.makedirs(settings.storage_dir, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    # Lightweight pgvector extension attempt (non-fatal if unavailable)
    if engine.dialect.name == "postgresql":
        try:
            with engine.begin() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        except Exception:
            pass


@app.get("/api/health")
def health():
    return {"status": "ok"}
