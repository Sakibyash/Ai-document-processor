from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.serializers import invoice_to_dict
from app.database import get_db
from app.models import ExtractedInvoice, LineItem, ValidationError
from app.validation import financial
from app.schemas import InvoiceExtraction, LineItemSchema

router = APIRouter(prefix="/api/invoices", tags=["corrections"])


class LineItemUpdate(BaseModel):
    description: str | None = None
    quantity: float | None = None
    unit_price: float | None = None
    amount: float | None = None


class InvoiceUpdate(BaseModel):
    document_type: str | None = None
    invoice_number: str | None = None
    invoice_date: str | None = None
    supplier_name: str | None = None
    customer_name: str | None = None
    merchant_name: str | None = None
    transaction_date: str | None = None
    payment_method: str | None = None
    subtotal: float | None = None
    tax: float | None = None
    total: float | None = None
    currency: str | None = None
    line_items: list[LineItemUpdate] | None = None


@router.patch("/{invoice_id}")
def correct_invoice(invoice_id: str, payload: InvoiceUpdate, db: Session = Depends(get_db)):
    """Human-in-the-loop correction of extracted fields. Re-runs validation after."""
    inv = db.scalar(
        select(ExtractedInvoice)
        .options(selectinload(ExtractedInvoice.line_items))
        .where(ExtractedInvoice.id == invoice_id)
    )
    if not inv:
        raise HTTPException(404, "Invoice not found")

    for field, value in payload.model_dump(exclude_unset=True, exclude={"line_items"}).items():
        setattr(inv, field, value)
    inv.corrected_by_user = True

    if payload.line_items is not None:
        # Replace line items wholesale (simplest correct semantics for MVP)
        for li in list(inv.line_items):
            db.delete(li)
        db.flush()
        for item in payload.line_items:
            db.add(
                LineItem(
                    invoice_id=inv.id,
                    description=item.description,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    amount=item.amount,
                )
            )

    db.commit()
    db.refresh(inv)

    # Re-validate with corrected values
    extraction = InvoiceExtraction(
        document_type=inv.document_type or "unknown",
        invoice_number=inv.invoice_number,
        invoice_date=inv.invoice_date,
        supplier_name=inv.supplier_name,
        customer_name=inv.customer_name,
        merchant_name=inv.merchant_name,
        transaction_date=inv.transaction_date,
        payment_method=inv.payment_method,
        subtotal=inv.subtotal,
        tax=inv.tax,
        total=inv.total,
        currency=inv.currency,
        line_items=[
            LineItemSchema(
                description=li.description,
                quantity=li.quantity,
                unit_price=li.unit_price,
                amount=li.amount,
            )
            for li in inv.line_items
        ],
    )
    result = financial.validate_invoice(extraction)
    # Mark old issues resolved, insert fresh ones
    old = db.scalars(select(ValidationError).where(ValidationError.invoice_id == inv.id)).all()
    for issue in old:
        issue.resolved = True
    for issue in result.issues:
        db.add(
            ValidationError(
                document_id=inv.document_id,
                invoice_id=inv.id,
                field=issue.field,
                message=issue.message,
                severity=issue.severity,
            )
        )
    db.commit()

    return {"invoice": invoice_to_dict(inv), "validation": result.model_dump()}


@router.get("/{invoice_id}/compare/{other_invoice_id}")
def compare_invoices(invoice_id: str, other_invoice_id: str, db: Session = Depends(get_db)):
    """Cross-document verification between two extracted invoices."""
    from app.validation.cross_verify import compare_records

    a = db.get(ExtractedInvoice, invoice_id)
    b = db.get(ExtractedInvoice, other_invoice_id)
    if not a or not b:
        raise HTTPException(404, "Invoice not found")

    fields = ("document_type", "invoice_number", "invoice_date", "supplier_name", "customer_name",
              "merchant_name", "transaction_date", "payment_method", "currency", "subtotal", "tax", "total")
    result = compare_records(
        {k: getattr(a, k) for k in fields},
        {k: getattr(b, k) for k in fields},
    )
    return result.model_dump()
