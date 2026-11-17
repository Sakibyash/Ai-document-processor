from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.serializers import document_to_dict, invoice_to_dict, issue_to_dict
from app.database import get_db
from app.models import Document, ExtractedInvoice, ValidationError

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.get("")
def list_documents(db: Session = Depends(get_db)):
    docs = db.scalars(
        select(Document).options(selectinload(Document.invoice)).order_by(Document.created_at.desc()).limit(200)
    ).all()
    return [document_to_dict(d, db) for d in docs]


@router.get("/{document_id}")
def get_document(document_id: str, db: Session = Depends(get_db)):
    doc = db.scalar(
        select(Document)
        .options(selectinload(Document.invoice).selectinload(ExtractedInvoice.line_items))
        .where(Document.id == document_id)
    )
    if not doc:
        raise HTTPException(404, "Document not found")

    data = document_to_dict(doc, db)
    data["history"] = [
        {"stage": h.stage, "status": h.status, "detail": h.detail, "created_at": h.created_at.isoformat()}
        for h in doc.history
    ]
    issues = db.scalars(select(ValidationError).where(ValidationError.document_id == document_id)).all()
    data["validation_issues"] = [issue_to_dict(i) for i in issues]
    if doc.invoice:
        data["invoice"] = invoice_to_dict(doc.invoice)
    return data


@router.post("/{document_id}/verify/{other_document_id}")
def verify_documents(document_id: str, other_document_id: str, db: Session = Depends(get_db)):
    """Cross-document verification between two uploaded documents (e.g. PDF invoice
    vs Excel record). Resolves each document's extracted invoice automatically."""
    from app.api.corrections import compare_invoices
    from app.models import ExtractedInvoice

    a = db.scalar(select(ExtractedInvoice).where(ExtractedInvoice.document_id == document_id))
    b = db.scalar(select(ExtractedInvoice).where(ExtractedInvoice.document_id == other_document_id))
    if not a or not b:
        raise HTTPException(404, "One or both documents have no extracted invoice yet")
    return compare_invoices(a.id, b.id, db)


@router.post("/{document_id}/reprocess")
def reprocess_document(document_id: str, db: Session = Depends(get_db)):
    doc = db.get(Document, document_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    from app.workers.pipeline import process_document

    try:
        process_document.delay(doc.id)
    except Exception:
        process_document.apply(args=[doc.id])
    return {"status": "reprocessing", "document_id": doc.id}
