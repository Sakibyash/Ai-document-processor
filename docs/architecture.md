# Architecture

## Pipeline

```
Upload (FastAPI)
  → store file on disk, create Document row, enqueue Celery task
  → processors/base.py: detect format → extract raw text
      PDF: PyMuPDF text layer; OCR fallback (Tesseract) for scanned pages
      Images: Tesseract OCR
      Excel/CSV: pandas → CSV text
  → ai/extraction.py: prompt → OpenAI (json_object mode) → Pydantic InvoiceExtraction
  → persist ExtractedInvoice + LineItems
  → validation/financial.py: Decimal-based arithmetic checks
  → validation/duplicate.py: normalized invoice-number + supplier/total/date matching
  → ValidationError rows (error/warning/info)
  → Document.status = completed
```

Corrections (`PATCH /api/invoices/{id}`) update fields, mark `corrected_by_user`, replace line items, and re-run financial validation.

## Key design decisions

- **LLM extracts, Python validates.** The model never decides correctness; `validation/financial.py` uses `Decimal` to avoid float rounding errors.
- **Never invent data.** The prompt forbids hallucination; missing values are `null` and reported in `missing_fields`/`uncertain_fields`.
- **Async processing.** Upload returns immediately; Celery worker handles OCR + LLM latency. If the broker is unreachable the task runs eagerly (dev fallback).
- **Page-bounded OCR.** Scanned PDFs are OCR'd page-by-page with a cap (`MAX_OCR_PAGES`) rather than sending whole documents as images.
- **Text-bounded prompts.** Extracted text is truncated to 60k chars to stay within model context.

## Database schema

- `documents` — file metadata, status, storage path
- `extracted_invoices` — structured fields + `raw_extraction` JSON
- `line_items` — invoice line items
- `validation_errors` — field-level issues with severity and resolved flag
- `processing_history` — audit trail per stage

Postgres deployment uses the `pgvector/pgvector` image so embeddings can be added later without changing infra.

## API

REST endpoints under `/api/*`; interactive docs at `/docs`. See README table.

## Failure handling

- Unsupported types and oversize files rejected at upload (400/413).
- Pipeline exceptions mark the document `failed` with `error_message` and record history; Celery retries twice.
- LLM JSON/schema failures raise `ValueError` → document marked failed (visible in UI).
