from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.ai.embeddings import cosine_similarity, embed_text
from app.api.serializers import document_to_dict, invoice_to_dict
from app.database import get_db
from app.models import Document, DocumentEmbedding, ExtractedInvoice

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("")
def search(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
):
    """Keyword search across filename, invoice number, supplier, customer."""
    like = f"%{q}%"
    docs = db.scalars(
        select(Document)
        .outerjoin(ExtractedInvoice, ExtractedInvoice.document_id == Document.id)
        .options(selectinload(Document.invoice))
        .where(
            or_(
                Document.filename.ilike(like),
                ExtractedInvoice.invoice_number.ilike(like),
                ExtractedInvoice.supplier_name.ilike(like),
                ExtractedInvoice.customer_name.ilike(like),
            )
        )
        .limit(100)
    ).all()


@router.get("/semantic")
def semantic_search(
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Semantic search over document embeddings. Returns docs ranked by cosine similarity."""
    try:
        query_vec = embed_text(q)
    except RuntimeError as exc:
        raise HTTPException(503, str(exc))

    rows = db.execute(
        select(DocumentEmbedding, Document)
        .join(Document, Document.id == DocumentEmbedding.document_id)
        .options(selectinload(Document.invoice))
    ).all()

    scored = []
    for emb, doc in rows:
        score = cosine_similarity(query_vec, emb.embedding)
        scored.append((score, doc))
    scored.sort(key=lambda x: x[0], reverse=True)

    return [
        {**document_to_dict(doc, db), "similarity": round(score, 4)}
        for score, doc in scored[:limit]
        if score > 0.0
    ]
    return [document_to_dict(d, db) for d in docs]
