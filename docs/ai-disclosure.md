# AI Prompts and AI-Assisted Development Disclosure

## LLM extraction prompt

The production extraction prompt lives in `backend/app/ai/prompts.py` (`INVOICE_EXTRACTION_PROMPT`). Key constraints it enforces:

- Never invent values — missing fields return `null` and are listed in `missing_fields`.
- Uncertain values are flagged in `uncertain_fields` rather than guessed.
- Original currency is preserved; no conversion.
- All line items are extracted.
- Output is constrained to JSON (`response_format={"type": "json_object"}`) and validated against the `InvoiceExtraction` Pydantic schema — invalid output fails the document rather than entering the database.

## Embeddings

Semantic search uses embeddings via `backend/app/ai/embeddings.py` — `gemini-embedding-001` by default (`LLM_PROVIDER=gemini`), or `text-embedding-3-small` when `LLM_PROVIDER=openai`. Invoice extraction similarly supports `gemini-2.0-flash` (default) or `gpt-4o-mini` via the same switch. Vectors are stored as JSON arrays in `document_embeddings` (cosine similarity computed in Python). On PostgreSQL deployments this can be migrated to a native `vector` column for indexed ANN search — the pgvector image is already used in `docker-compose.yml`.

## AI-assisted development disclosure

This project was developed with AI coding assistance (Cascade / Windsurf). All code was reviewed and tested by the candidate. Automated tests cover validation logic, duplicate detection, spreadsheet parsing, format detection, and API endpoints. Extraction accuracy claims in `docs/evaluation.md` are based on a labeled test dataset run against the real pipeline, not estimates.
