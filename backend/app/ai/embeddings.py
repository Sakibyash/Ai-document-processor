"""Text embeddings for semantic search. Supports Gemini (default) and OpenAI."""
import math

import httpx
from openai import OpenAI

from app.config import settings

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"


def embed_text(text: str) -> list[float]:
    if settings.llm_provider == "gemini":
        return _gemini_embed(text)
    return _openai_embed(text)


def _gemini_embed(text: str) -> list[float]:
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured")
    url = f"{GEMINI_API_BASE}/models/{settings.gemini_embedding_model}:embedContent"
    payload = {"model": f"models/{settings.gemini_embedding_model}", "content": {"parts": [{"text": text[:8000]}]}}
    resp = httpx.post(url, params={"key": settings.gemini_api_key}, json=payload, timeout=60)
    if resp.status_code != 200:
        raise RuntimeError(f"Gemini embedding error {resp.status_code}: {resp.text[:500]}")
    return resp.json()["embedding"]["values"]


def _openai_embed(text: str) -> list[float]:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    client = OpenAI(api_key=settings.openai_api_key)
    resp = client.embeddings.create(model=settings.openai_embedding_model, input=text[:8000])
    return resp.data[0].embedding


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
