from app.models import Document, ExtractedInvoice, LineItem, ValidationError


def invoice_to_dict(inv: ExtractedInvoice, include_items: bool = True) -> dict:
    data = {
        "id": inv.id,
        "document_id": inv.document_id,
        "document_type": inv.document_type,
        "invoice_number": inv.invoice_number,
        "invoice_date": inv.invoice_date,
        "supplier_name": inv.supplier_name,
        "customer_name": inv.customer_name,
        "merchant_name": inv.merchant_name,
        "transaction_date": inv.transaction_date,
        "payment_method": inv.payment_method,
        "currency": inv.currency,
        "subtotal": inv.subtotal,
        "tax": inv.tax,
        "total": inv.total,
        "corrected_by_user": inv.corrected_by_user,
        "raw_extraction": inv.raw_extraction,
    }
    if include_items:
        data["line_items"] = [
            {
                "id": li.id,
                "description": li.description,
                "quantity": li.quantity,
                "unit_price": li.unit_price,
                "amount": li.amount,
            }
            for li in inv.line_items
        ]
    return data


def document_to_dict(doc: Document, db=None) -> dict:
    data = {
        "id": doc.id,
        "filename": doc.filename,
        "content_type": doc.content_type,
        "file_size": doc.file_size,
        "extracted_text": doc.extracted_text,
        "status": doc.status.value,
        "error_message": doc.error_message,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
    }
    if db is not None and doc.invoice:
        data["invoice"] = invoice_to_dict(doc.invoice, include_items=False)
    return data


def issue_to_dict(issue: ValidationError) -> dict:
    return {
        "id": issue.id,
        "document_id": issue.document_id,
        "invoice_id": issue.invoice_id,
        "field": issue.field,
        "message": issue.message,
        "severity": issue.severity.value,
        "resolved": issue.resolved,
        "created_at": issue.created_at.isoformat() if issue.created_at else None,
    }
