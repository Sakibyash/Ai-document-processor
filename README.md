# AI Document Processor Backend

A backend service for intelligent document intake, extraction, validation, and retrieval. It accepts invoice and document uploads in multiple formats, processes them asynchronously, extracts structured data using LLM-powered parsing, validates financial correctness with Python rules, and provides searchable APIs for downstream review and correction workflows.

## Overview

This project is designed for document-heavy workflows where accuracy and traceability matter. The backend handles:

- File ingestion for PDF, image, spreadsheet, text, and document exports
- OCR and text extraction from scanned or semi-structured sources
- Structured invoice extraction using an LLM
- Financial validation and duplicate detection
- Search and comparison across stored document data
- Human correction workflows with re-validation
- Background pipeline execution for long-running tasks

The system is implemented primarily in FastAPI and uses Celery + Redis to offload processing from the request thread.

## Core backend capabilities

### 1. Document ingestion
- Upload documents through the API
- Store files in a persistent storage directory
- Track document metadata and processing status
- Reject unsupported or oversized files with structured validation

### 2. Extraction pipeline
- Detect file type via processor layer
- Extract raw content from PDF, image, CSV, Excel, or text inputs
- Normalize extracted content before LLM parsing
- Convert unstructured content into structured invoice entities and line items

### 3. AI-assisted data extraction
- Uses LLM prompting to convert text into structured extraction objects
- Enforces schema-based output expectations
- Keeps raw extraction payloads available for diagnostics and auditability

### 4. Validation and quality assurance
- Performs arithmetic checks using Decimal-based logic to avoid floating-point precision issues
- Detects duplicate or near-duplicate invoices using normalized comparison rules
- Logs validation errors with severity levels and reconciliation statuses

### 5. Search and review
- Query documents and invoice records through REST endpoints
- Search by keyword and semantic relevance
- Compare related documents or extracted invoice records
- Allow review and correction of extracted values by users

## Backend architecture

The backend follows a modular service-oriented structure:

```text
API Layer
  -> Upload / Document / Search / Correction endpoints
      -> Business logic and DB access
          -> Processor layer (PDF, image, Excel, text, etc.)
              -> AI extraction service
                  -> Validation layer
                      -> Database persistence
                          -> Celery task orchestration
```

### Request lifecycle

1. Client uploads a file to the FastAPI app.
2. The file is saved to local storage and a document record is created.
3. A Celery task is queued for asynchronous processing.
4. The worker detects the file type and extracts raw text or OCR output.
5. The LLM extracts invoice data into a structured JSON schema.
6. Validation rules verify totals, fields, and duplicates.
7. The results are persisted and exposed through API endpoints.
8. Frontend or review tools can patch values and trigger re-validation.

## Tech stack

### Runtime and API
- FastAPI
- Pydantic + Pydantic Settings
- SQLAlchemy 2.0
- Uvicorn

### Background processing
- Celery
- Redis
- Async task execution for long-running extraction and validation work

### Document processing
- PyMuPDF for PDF handling
- Pillow for image processing
- Tesseract OCR
- pandas for tabular document parsing
- openpyxl, xlrd, python-docx for Office and spreadsheet files

### AI and embeddings
- OpenAI API
- LLM-based extraction workflows
- Embedding generation support for search and semantic retrieval

### Storage and persistence
- SQLite by default for local development
- PostgreSQL-ready configuration for production deployments
- pgvector-compatible deployment pattern for future vector search

## Repository structure

```text
backend/
  app/
    ai/
      embeddings.py
      extraction.py
      prompts.py
    api/
      corrections.py
      documents.py
      search.py
      serializers.py
      uploads.py
    processors/
      base.py
      excel_processor.py
      image_processor.py
      pdf_processor.py
      text_processor.py
    validation/
      cross_verify.py
      duplicate.py
      financial.py
    workers/
      celery_app.py
      pipeline.py
    config.py
    database.py
    main.py
    models.py
    schemas.py
  tests/
    conftest.py
    test_api.py
    test_duplicate.py
    test_embeddings.py
    test_extraction_merge.py
    test_financial.py
    test_processors.py
    test_prompts.py
```

## Configuration

The backend reads configuration from environment variables using Pydantic settings. Key configuration values include:

```env
DATABASE_URL=sqlite:///./docintel.db
REDIS_URL=redis://localhost:6379/0
LLM_PROVIDER=gemini
OPENAI_API_KEY=your_openai_key
OPENAI_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
GEMINI_API_KEY=your_gemini_key
GEMINI_MODEL=gemini-2.0-flash
STORAGE_DIR=./storage
MAX_UPLOAD_MB=50
```

### Environment notes
- SQLite is suitable for local development and tests.
- PostgreSQL is recommended for production or multi-user deployments.
- Redis must be available for Celery worker processing.

## Getting started

### Prerequisites
- Python 3.11+
- Redis server
- Optional: PostgreSQL
- Optional: Tesseract OCR installed on the system
- Optional: OpenAI or Gemini API credentials

### Install backend dependencies

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Run the backend locally

```bash
cd backend
export DATABASE_URL=sqlite:///./docintel.db
export REDIS_URL=redis://localhost:6379/0
export OPENAI_API_KEY=your_key
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Run the Celery worker

In a separate terminal:

```bash
cd backend
celery -A app.workers.celery_app worker --loglevel=info
```

### Run with Docker

From the project root:

```bash
docker compose up --build
```

This starts the application stack with the backend and related services configured for local development.

## API overview

The API is exposed under the `/api` namespace and is documented interactively at:

```text
http://localhost:8000/docs
```

### Core endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/health` | Health check for the backend service |
| POST | `/api/uploads` | Upload a file for processing |
| GET | `/api/documents` | List processed and pending documents |
| GET | `/api/documents/{id}` | Get detailed document extraction and validation information |
| POST | `/api/documents/{id}/reprocess` | Re-run processing for a document |
| GET | `/api/search?q=` | Query stored records by keyword |
| GET | `/api/search/semantic?q=` | Search by semantic similarity |
| PATCH | `/api/invoices/{id}` | Update extracted values and re-validate |
| POST | `/api/documents/{id}/verify/{other_id}` | Compare document contents across records |
| GET | `/api/invoices/{a}/compare/{b}` | Compare extracted invoice-level attributes |

## Key backend modules

### app.main
- Initializes the FastAPI application
- Configures CORS for the frontend origin
- Registers routers
- Creates database tables at startup
- Exposes the health endpoint

### app.api
- Contains endpoint logic for uploads, document retrieval, corrections, and search
- Handles HTTP validation and response serialization

### app.processors
- Detects and processes document formats
- Extracts raw data from PDFs, images, CSVs, Excel files, and text files
- Encapsulates source-specific parsing behavior

### app.ai
- Centralizes extraction prompts and response parsing
- Manages LLM calls and schema validation for structured output
- Supports embedding generation and semantic retrieval workflows

### app.validation
- Performs financial validation checks
- Detects duplicates and compare-style anomalies
- Produces warnings/errors on extracted data quality issues

### app.workers
- Defines the Celery app and task pipeline
- Manages asynchronous execution for file processing and validation

## Testing

This project includes backend unit and integration tests under the `tests/` folder.

Run the test suite with:

```bash
cd backend
pytest
```

Recommended test coverage areas:
- API behavior and document status flows
- Duplicate detection logic
- Financial validation calculations
- Extraction schema integrity
- OCR and processor edge cases
- Prompt and LLM integration reliability

## Operational notes

- Document processing is intentionally asynchronous to avoid blocking API requests.
- Failed tasks are surfaced through document status and history metadata.
- Validation rules are designed to be explicit and deterministic rather than relying on model judgment alone.
- The extraction layer is schema-driven, which reduces malformed or unstable data output.

## Recommended next steps

- Switch development database to PostgreSQL for production-like validation
- Add container health checks and monitoring for Redis/Celery workers
- Expand semantic search with persistent vector storage and indexing
- Harden document security checks, rate limits, and background retries
- Add observability logs and task metrics for auditability

## License

This project is intended for internal or team-based document processing workflows. Update licensing terms according to your organization or client requirements before public distribution.

## Documentation

Additional project documentation is available in:

- docs/architecture.md
- docs/evaluation.md
- docs/ai-disclosure.md
