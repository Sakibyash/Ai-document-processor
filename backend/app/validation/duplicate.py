"""Duplicate invoice detection across stored invoices."""
import re
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ExtractedInvoice


def _norm_invoice_number(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"[^A-Z0-9]", "", value.upper())


def find_duplicates(db: Session, invoice: ExtractedInvoice) -> list[ExtractedInvoice]:
    """Match on normalized invoice number + supplier, or number + total + date."""
    candidates = db.scalars(select(ExtractedInvoice).where(ExtractedInvoice.id != invoice.id)).all()
    norm_num = _norm_invoice_number(invoice.invoice_number)
    dupes = []

    for c in candidates:
        same_number = norm_num and _norm_invoice_number(c.invoice_number) == norm_num
        if not same_number:
            continue
        same_supplier = (invoice.supplier_name or "").strip().lower() == (c.supplier_name or "").strip().lower()
        same_total = (
            invoice.total is not None
            and c.total is not None
            and abs(invoice.total - c.total) < 0.01
        )
        same_date = (invoice.invoice_date or "") == (c.invoice_date or "")
        if same_supplier or (same_total and same_date):
            dupes.append(c)

    return dupes
