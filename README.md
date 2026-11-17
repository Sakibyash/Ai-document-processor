# AI-Powered Document Intelligence System

Upload invoices and receipts (PDF, images, Excel, CSV, TXT/MD, DOCX) in bulk → OCR/text extraction → LLM structured extraction → Python financial validation → searchable database with human-in-the-loop corrections.

## Stack

- **Backend**: FastAPI, SQLAlchemy, Celery + Redis, OpenAI API, PyMuPDF, Tesseract OCR, pandas
- **Frontend**: Next.js, Tailwind CSS
- **Database**: PostgreSQL (pgvector image; SQLite fallback for tests)
- **Infra**: Docker Compose

## Quick start

```bash
cp .env.example .env   # add your OPENAI_API_KEY
docker compose up --build
```

- Frontend: http://localhost:3000
- API docs: http://localhost:8000/docs

### Local development (without Docker)

```bash
cd backend
pip install -r requirements.txt
export DATABASE_URL=sqlite:///./docintel.db   # or your Postgres URL
export OPENAI_API_KEY=sk-...
uvicorn app.main:app --reload
# in another terminal:
celery -A app.workers.celery_app worker --loglevel=info
```

## Tests

```bash
cd backend
pip install -r requirements.txt
pytest
```

## API overview

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/uploads` | Upload a document (multipart `file`) |
| GET | `/api/documents` | List documents with status |
| GET | `/api/documents/{id}` | Detail: invoice, line items, validation issues, history |
| POST | `/api/documents/{id}/reprocess` | Re-run pipeline |
| GET | `/api/search?q=` | Keyword search |
| GET | `/api/search/semantic?q=` | Semantic search (embeddings + cosine similarity) |
| PATCH | `/api/invoices/{id}` | Correct extracted fields (re-validates) |
| POST | `/api/documents/{id}/verify/{other_id}` | Cross-document verification (PDF↔PDF, PDF↔Excel) |
| GET | `/api/invoices/{a}/compare/{b}` | Cross-document verification (invoice-level) |

## Project layout

See `docs/architecture.md` for the full design, `docs/evaluation.md` for the metrics template, and `docs/ai-disclosure.md` for the prompts and AI-assisted development disclosure.
