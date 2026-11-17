from app.models import ExtractedInvoice
from app.validation.duplicate import find_duplicates


def test_duplicate_detection(db_session):
    a = ExtractedInvoice(
        document_id="doc-a",
        invoice_number="INV-2026-001",
        supplier_name="ABC Ltd",
        total=1150.0,
        invoice_date="2026-01-01",
    )
    b = ExtractedInvoice(
        document_id="doc-b",
        invoice_number="inv 2026 001",  # normalizes to same
        supplier_name="ABC Ltd",
        total=1150.0,
        invoice_date="2026-01-01",
    )
    c = ExtractedInvoice(
        document_id="doc-c",
        invoice_number="INV-999",
        supplier_name="Other",
        total=50.0,
    )
    db_session.add_all([a, b, c])
    db_session.commit()

    dupes = find_duplicates(db_session, a)
    assert len(dupes) == 1
    assert dupes[0].id == b.id
