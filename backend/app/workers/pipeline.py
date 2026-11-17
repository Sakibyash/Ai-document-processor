"""Background pipeline: text extraction -> LLM extraction -> validation -> DB."""
import logging

from app.database import SessionLocal
from app.models import (
    Document,
    DocumentEmbedding,
    DocumentStatus,
    ExtractedInvoice,
    LineItem,
    ProcessingHistory,
    Severity,
    ValidationError,
)
from app.processors.base import extract_text
from app.schemas import InvoiceExtraction
from app.validation import duplicate, financial
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


def _history(db, document_id: str, stage: str, status: str, detail: str | None = None):
    db.add(ProcessingHistory(document_id=document_id, stage=stage, status=status, detail=detail))
    db.commit()


def _save_invoice(db, document: Document, inv: InvoiceExtraction):
    invoice = ExtractedInvoice(
        document_id=document.id,
        document_type=inv.document_type,
        invoice_number=inv.invoice_number,
        invoice_date=inv.invoice_date,
        supplier_name=inv.supplier_name,
        customer_name=inv.customer_name,
        merchant_name=inv.merchant_name,
        transaction_date=inv.transaction_date,
        payment_method=inv.payment_method,
        currency=inv.currency,
        subtotal=inv.subtotal,
        tax=inv.tax,
        total=inv.total,
        raw_extraction=inv.model_dump(),
    )
    db.add(invoice)
    db.flush()
    for item in inv.line_items:
        db.add(
            LineItem(
                invoice_id=invoice.id,
                description=item.description,
                quantity=item.quantity,
                unit_price=item.unit_price,
                amount=item.amount,
            )
        )
    db.commit()
    return invoice


def _save_issues(db, document_id: str, invoice_id: str | None, issues):
    for issue in issues:
        db.add(
            ValidationError(
                document_id=document_id,
                invoice_id=invoice_id,
                field=issue.field,
                message=issue.message,
                severity=Severity(issue.severity),
            )
        )
    db.commit()


@celery_app.task(bind=True, max_retries=2)
def process_document(self, document_id: str):
    db = SessionLocal()
    document = db.get(Document, document_id)
    if not document:
        db.close()
        return {"error": "document not found"}

    try:
        document.status = DocumentStatus.processing
        db.commit()
        _history(db, document.id, "extract_text", "started")

        text = extract_text(document.storage_path, document.filename)
        _history(db, document.id, "extract_text", "completed", f"{len(text)} chars")

        _history(db, document.id, "ai_extraction", "started")
        from app.ai.extraction import extract_invoice

        inv = extract_invoice(text)
        _history(db, document.id, "ai_extraction", "completed")

        invoice = _save_invoice(db, document, inv)

        _history(db, document.id, "validation", "started")
        result = financial.validate_invoice(inv)
        _save_issues(db, document.id, invoice.id, result.issues)

        dupes = duplicate.find_duplicates(db, invoice)
        for d in dupes:
            db.add(
                ValidationError(
                    document_id=document.id,
                    invoice_id=invoice.id,
                    field="invoice_number",
                    message=f"Possible duplicate of invoice {d.invoice_number} (document {d.document_id})",
                    severity=Severity.warning,
                )
            )
        db.commit()
        _history(db, document.id, "validation", "completed", f"valid={result.valid}, duplicates={len(dupes)}")

        # Semantic search embedding (non-fatal if it fails)
        try:
            _history(db, document.id, "embedding", "started")
            from app.ai.embeddings import embed_text
            from app.config import settings as app_settings

            embed_source = (
                f"Invoice {inv.invoice_number or ''} from {inv.supplier_name or ''} to {inv.customer_name or ''}. "
                f"Date: {inv.invoice_date or ''}. Total: {inv.total or ''} {inv.currency or ''}. "
                f"{text[:4000]}"
            )
            vector = embed_text(embed_source)
            embed_model = (
                app_settings.gemini_embedding_model
                if app_settings.llm_provider == "gemini"
                else app_settings.openai_embedding_model
            )
            existing = db.query(DocumentEmbedding).filter_by(document_id=document.id).first()
            if existing:
                existing.embedding = vector
                existing.model = embed_model
            else:
                db.add(DocumentEmbedding(document_id=document.id, embedding=vector, model=embed_model))
            db.commit()
            _history(db, document.id, "embedding", "completed")
        except Exception as exc:
            db.rollback()
            logger.warning("Embedding failed for %s: %s", document_id, exc)
            _history(db, document.id, "embedding", "failed", str(exc)[:300])

        document.status = DocumentStatus.completed
        db.commit()
        return {"document_id": document_id, "valid": result.valid}

    except Exception as exc:
        logger.exception("Processing failed for document %s", document_id)
        db.rollback()
        document = db.get(Document, document_id)
        if document:
            document.status = DocumentStatus.failed
            document.error_message = str(exc)[:2000]
            db.commit()
            _history(db, document.id, "pipeline", "failed", str(exc)[:500])
        raise self.retry(exc=exc, countdown=10) if self.request.retries < self.max_retries else exc
    finally:
        db.close()
