# AI Document Processor Backend

A production-oriented backend for document intelligence, document ingestion, AI-powered extraction, validation, and retrieval. The service accepts invoices and other structured documents in multiple formats, extracts raw text using OCR and parser pipelines, structures the data with LLM-based extraction, validates financial correctness using deterministic Python checks, and exposes a REST API for review, correction, and search workflows.

## Purpose

This project is designed for document-heavy business workflows where quality, traceability, and operational reliability matter. The core backend responsibilities are:

- Ingesting uploaded files from the frontend or external clients
- Persisting metadata and storage artifacts while tracking processing status
- Detecting document type and routing to the appropriate extraction pipeline
- Extracting readable text from PDFs, scanned pages, spreadsheets, images, and text files
- Running LLM-based structural extraction to convert raw content into invoice data
- Validating totals, dates, and extracted values with Python logic
- Recording validation issues and processing history for later review
- Enabling correction workflows and document-level comparisons
- Supporting semantic and keyword search on extracted document content

## System design

The backend is implemented as a layered FastAPI application that separates API concerns, domain logic, processing, validation, and worker execution.

```text
Client / Frontend
      |
      v
FastAPI API Layer
      |
      +--> Upload endpoints
      +--> Document retrieval and status endpoints
      +--> Search and comparison endpoints
      +--> Correction and reprocessing endpoints
      |
      v
Application Services / Business Logic
      |
      +--> Document creation + metadata persistence
      +--> File storage and validation
      +--> Extraction orchestration
      +--> Validation and duplicate checks
      |
      v
Processing Layer
      +--> base document detection
      +--> PDF processor
      +--> image processor
      +--> Excel/CSV processor
      +--> text processor
      |
      v
AI Layer
      +--> prompt construction
      +--> LLM extraction
      +--> structured schema validation
      +--> embedding generation support
      |
      v
Persistence Layer
      +--> SQLAlchemy models
      +--> SQLite for local/dev
      +--> PostgreSQL-ready configuration
      |
      v
Worker Layer
      +--> Celery task queue
      +--> Redis broker
      +--> background document processing
```

## Core processing pipeline

The backend follows a deterministic extraction pipeline designed for reliability and traceability:

1. Upload the file through the FastAPI API.
2. Validate filename, extension, and file size.
3. Save the file into a per-document storage directory.
4. Create a `Document` record with metadata and initial status.
5. Enqueue a Celery task for asynchronous processing.
6. Worker resolves the file type and selects the appropriate processor.
7. Extract raw content using PDF text extraction, OCR, or tabular parsers.
8. Build a prompt with extracted text and required schema constraints.
9. Call the LLM to return structured invoice data in JSON form.
10. Persist extracted invoice fields and line items to the database.
11. Apply validation checks for totals, missing fields, duplicates, and anomalies.
12. Update document status from `processing` to `completed` or `failed`.
13. Expose the result through search and document detail endpoints.

## Architectural principles

### 1. Async-first execution model
Long-running processing is decoupled from the HTTP request lifecycle. Uploads return immediately while the Celery worker handles OCR, parsing, and model inference.

### 2. Deterministic validation over model trust
The model is treated as a generator of candidate structured data, not as the final authority. Financial logic is enforced in Python using explicit checks and decimal-safe calculations.

### 3. Schema-driven extraction
Structured outputs are generated against known invoice-style schemas. This reduces uncontrolled or malformed output and makes downstream validation easier.

### 4. Auditability
The system stores:
- source file location
- extracted text
- raw extraction JSON
- validation errors
- processing history
- correction metadata

This makes the pipeline reviewable and debuggable.

### 5. Human-in-the-loop correction
Users can patch extracted values via API endpoints, re-run validation, and ensure the extracted output aligns with real source documents.

## Technology stack

### API layer
- FastAPI
- Pydantic v2
- Pydantic Settings
- Uvicorn

### Persistence
- SQLAlchemy 2.0
- SQLite for local development and tests
- PostgreSQL-ready design for production workloads
- JSON storage patterns suited for structured extraction payloads

### Background processing
- Celery
- Redis
- Eager fallback for local development environments when a broker is unavailable

### Document ingestion and parsing
- PyMuPDF for PDF text extraction
- Pillow for image handling
- Tesseract OCR for scanned and image-based documents
- pandas for CSV and Excel parsing
- openpyxl and xlrd for spreadsheet formats
- python-docx for DOCX input

### AI and retrieval
- OpenAI API support
- Gemini API support
- LLM-driven extraction and structured output parsing
- Embedding-ready architecture for semantic retrieval

## Data model

The backend stores a document-centric data model with supporting entities for extraction, validation, and history.

### Document
Represents the uploaded file and processing lifecycle:
- id
- filename
- content_type
- file_size
- storage_path
- extracted_text
- status
- error_message
- created_at
- updated_at

### ExtractedInvoice
Stores the normalized structured invoice result:
- document_id
- document_type
- invoice_number
- invoice_date
- supplier_name
- customer_name
- merchant_name
- transaction_date
- payment_method
- currency
- subtotal
- tax
- total
- raw_extraction
- corrected_by_user

### LineItem
Represents the invoice line entries extracted from the document.

### ValidationError
Tracks validation issues by severity and status:
- error
- warning
- info

### ProcessingHistory
Captures stage-by-stage execution details for auditing.

### DocumentEmbedding
Supports embedding-based features and future semantic search expansion.

## Repository layout

```text
backend/
  app/
    ai/
      __init__.py
      embeddings.py
      extraction.py
      prompts.py
    api/
      __init__.py
      corrections.py
      documents.py
      search.py
      serializers.py
      uploads.py
    processors/
      __init__.py
      base.py
      excel_processor.py
      image_processor.py
      pdf_processor.py
      text_processor.py
    validation/
      __init__.py
      cross_verify.py
      duplicate.py
      financial.py
    workers/
      __init__.py
      celery_app.py
      pipeline.py
    __init__.py
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

## Module responsibilities

### app.main
Initializes the FastAPI application, registers API routers, applies CORS configuration, and creates database tables at startup.

### app.config
Loads environment configuration from `.env` and defines application settings like database URL, Redis URL, model names, storage path, and file limits.

### app.database
Creates the SQLAlchemy engine and session factory, and exposes the database dependency used across routes.

### app.api.uploads
Handles file upload validation and dispatches jobs to the processing queue.

### app.api.documents
Provides document listing, detail retrieval, verification, and reprocessing endpoints.

### app.api.search
Exposes keyword and semantic search routes over indexed or persisted document metadata.

### app.api.corrections
Implements invoice correction and comparison logic for user-driven review workflows.

### app.processors
Contains format-specific parsing logic:
- PDF parsing with text extraction and OCR fallback
- image OCR pipelines
- spreadsheet extraction with pandas
- CSV, TXT, and DOCX parsing

### app.ai.extraction
Handles the LLM extraction calls and schema parsing of invoice data.

### app.ai.prompts
Defines prompt templates used to instruct the model for structured extraction.

### app.validation.financial
Runs deterministic arithmetic validations to check totals, taxes, and line-level consistency.

### app.validation.duplicate
Flags duplicate or near-duplicate documents using normalized invoice attributes.

### app.validation.cross_verify
Compares related documents and extracted records for discrepancy analysis.

### app.workers.pipeline
Coordinates the asynchronous document-processing job chain.

## Configuration

The application uses environment-based settings through `pydantic-settings`.

### Example configuration

```env
DATABASE_URL=sqlite:///./docintel.db
REDIS_URL=redis://localhost:6379/0
LLM_PROVIDER=gemini
OPENAI_API_KEY=your_openai_key
OPENAI_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
GEMINI_API_KEY=your_gemini_key
GEMINI_MODEL=gemini-2.0-flash
GEMINI_EMBEDDING_MODEL=gemini-embedding-001
STORAGE_DIR=./storage
MAX_UPLOAD_MB=50
```

### Configuration notes
- SQLite is adequate for local development and automated testing.
- PostgreSQL is the preferred production database for concurrency and reliability.
- Redis is required for Celery worker orchestration.
- OCR and model provider keys must be configured for production document processing.

## Local development setup

### Prerequisites
- Python 3.11+
- Redis server running locally
- Optional: PostgreSQL
- Optional: Tesseract OCR installed on the system
- API credentials for OpenAI or Gemini

### 1. Create a virtual environment

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
# Windows:
# .venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
export DATABASE_URL=sqlite:///./docintel.db
export REDIS_URL=redis://localhost:6379/0
export OPENAI_API_KEY=your_key
```

### 4. Start the API

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Start the worker

In a separate terminal:

```bash
cd backend
celery -A app.workers.celery_app worker --loglevel=info
```

### 6. Start with Docker

From the project root:

```bash
docker compose up --build
```

## API contract

API routes are grouped under the `/api` namespace and are documented via FastAPI OpenAPI at:

```text
http://localhost:8000/docs
```

### Primary endpoints

| Method | Endpoint | Responsibility |
|---|---|---|
| GET | `/api/health` | Service health check |
| POST | `/api/uploads` | Upload a file and start processing |
| GET | `/api/documents` | List recent documents |
| GET | `/api/documents/{document_id}` | Fetch a full document detail view |
| POST | `/api/documents/{document_id}/reprocess` | Trigger reprocessing for a document |
| GET | `/api/search?q=` | Search documents by keyword |
| GET | `/api/search/semantic?q=` | Search by semantic relevance |
| PATCH | `/api/invoices/{id}` | Correct extracted invoice fields and revalidate |
| POST | `/api/documents/{document_id}/verify/{other_document_id}` | Compare two extracted records |
| GET | `/api/invoices/{a}/compare/{b}` | Compare invoice-level relationships |

## Example upload flow

```bash
curl -X POST "http://localhost:8000/api/uploads" \
  -H "accept: application/json" \
  -F "file=@sample_invoice.pdf"
```

Response includes a document record with an ID and status. The processing then runs asynchronously in the Celery worker.

## Validation and quality assurance

The validation layer tries to ensure result correctness without depending entirely on the LLM output.

### Financial validation
- checks subtotal, tax, and total consistency
- handles currency and numeric precision carefully
- catches arithmetic anomalies before exposing the result

### Duplicate detection
- normalizes invoice identifiers and supplier metadata
- compares totals, dates, and supplier attributes
- flags documents that appear to be repeated or near-duplicates

### Error logging
Validation issues are recorded as structured `ValidationError` entries with severity and resolution state.

## Testing

The project includes backend tests under the `tests/` directory.

Run the suite:

```bash
cd backend
pytest
```

Recommended validation areas:
- API endpoint behavior
- document lifecycle transitions
- financial arithmetic checks
- duplicate detection logic
- OCR and processor parsing correctness
- LLM extraction schema reliability
- prompt and output consistency

## Operational notes

- The system uses asynchronous processing to keep HTTP responses fast.
- Files are stored on disk per document to simplify debugging and recovery.
- Failed extraction flows mark documents as failed with an error message and processing history.
- The backend is designed to support reprocessing after corrected extraction or infrastructure recovery.
- The architecture supports future upgrades such as vector search, better document ranking, and broader document type coverage.

## Production-minded considerations

Before deployment to production, the team should consider:

- PostgreSQL instead of SQLite for multi-user workloads
- Redis and Celery monitoring and queue observability
- rate limiting and authentication for upload endpoints
- secure file handling and artifact retention policies
- retry strategies for model or OCR failures
- structured logging and request correlation IDs
- document processing quotas and concurrency limits

## Documentation

Additional project documentation is available in:

- docs/architecture.md
- docs/evaluation.md
- docs/ai-disclosure.md

## License

This project is intended for internal or team-based document processing workflows. Update licensing and distribution terms before public release or commercial reuse.
