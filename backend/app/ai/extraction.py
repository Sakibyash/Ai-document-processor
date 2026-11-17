"""LLM-based invoice extraction with structured output validation.

Supports Gemini (default) and OpenAI, selected via LLM_PROVIDER.
"""
import json
import logging

import httpx
from openai import OpenAI
from pydantic import ValidationError

from app.ai.prompts import build_prompt
from app.config import settings
from app.schemas import InvoiceExtraction

logger = logging.getLogger(__name__)

MAX_TEXT_CHARS = 60_000  # per-chunk prompt size
CHUNK_OVERLAP = 1_000    # chars of overlap between chunks to avoid splitting records
MAX_CHUNKS = 12          # ~720k chars coverage; bounds API cost for huge PDFs
GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"


def extract_invoice(text: str) -> InvoiceExtraction:
    """Extract invoice data, chunking large documents (e.g. 1000-page PDFs)
    into overlapping segments and merging the per-chunk results."""
    chunks = _chunk_text(text)
    results = [_extract_single(chunk) for chunk in chunks]
    if len(results) == 1:
        return results[0]
    return _merge_extractions(results)


def _chunk_text(text: str) -> list[str]:
    if len(text) <= MAX_TEXT_CHARS:
        return [text]
    chunks = []
    start = 0
    while start < len(text) and len(chunks) < MAX_CHUNKS:
        end = start + MAX_TEXT_CHARS
        chunks.append(text[start:end])
        start = end - CHUNK_OVERLAP
    return chunks


def _extract_single(text: str) -> InvoiceExtraction:
    if settings.llm_provider == "gemini":
        content = _gemini_generate(build_prompt(text, MAX_TEXT_CHARS))
    else:
        content = _openai_generate(build_prompt(text, MAX_TEXT_CHARS))
    return _parse(content)


_SCALAR_FIELDS = [
    "document_type", "invoice_number", "invoice_date", "supplier_name", "customer_name",
    "merchant_name", "transaction_date", "payment_method",
    "subtotal", "tax", "total", "currency",
]


def _merge_extractions(results: list[InvoiceExtraction]) -> InvoiceExtraction:
    """Merge per-chunk extractions: first non-null scalar wins, line items
    concatenated, missing/uncertain fields unioned."""
    merged: dict = {}
    for field in _SCALAR_FIELDS:
        for r in results:
            value = getattr(r, field)
            if value not in (None, "", "unknown"):
                merged[field] = value
                break
        else:
            merged[field] = getattr(results[0], field)

    line_items = []
    seen = set()
    for r in results:
        for item in r.line_items:
            key = (item.description, item.amount)
            if key not in seen:
                seen.add(key)
                line_items.append(item)

    missing = sorted({f for r in results for f in r.missing_fields})
    uncertain = sorted({f for r in results for f in r.uncertain_fields})

    return InvoiceExtraction(
        **merged,
        line_items=line_items,
        missing_fields=missing,
        uncertain_fields=uncertain,
    )


def _parse(content: str) -> InvoiceExtraction:
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM returned invalid JSON: {exc}") from exc

    try:
        return InvoiceExtraction.model_validate(data)
    except ValidationError as exc:
        logger.warning("LLM output failed schema validation: %s", exc)
        raise ValueError(f"LLM output failed schema validation: {exc}") from exc


def _gemini_generate(prompt: str) -> str:
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured")

    url = f"{GEMINI_API_BASE}/models/{settings.gemini_model}:generateContent"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0,
        },
    }
    resp = httpx.post(url, params={"key": settings.gemini_api_key}, json=payload, timeout=120)
    if resp.status_code != 200:
        raise RuntimeError(f"Gemini API error {resp.status_code}: {resp.text[:500]}")

    data = resp.json()
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as exc:
        raise ValueError(f"Unexpected Gemini response shape: {json.dumps(data)[:500]}") from exc


def _openai_generate(prompt: str) -> str:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    client = OpenAI(api_key=settings.openai_api_key)
    response = client.chat.completions.create(
        model=settings.openai_model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0,
    )
    return response.choices[0].message.content or "{}"
