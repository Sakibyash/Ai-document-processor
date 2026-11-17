from app.schemas import InvoiceExtraction, LineItemSchema
from app.validation.financial import validate_invoice


def make_inv(**overrides):
    base = dict(
        invoice_number="INV-001",
        invoice_date="2026-01-01",
        supplier_name="ABC Ltd",
        customer_name="XYZ Corp",
        subtotal=1000.0,
        tax=150.0,
        total=1150.0,
        currency="USD",
        line_items=[LineItemSchema(description="Service", quantity=2, unit_price=500.0, amount=1000.0)],
    )
    base.update(overrides)
    return InvoiceExtraction(**base)


def test_valid_invoice():
    result = validate_invoice(make_inv())
    assert result.valid
    assert result.issues == []


def test_total_mismatch_is_error():
    result = validate_invoice(make_inv(total=1200.0))
    assert not result.valid
    assert any(i.field == "total" and i.severity == "error" for i in result.issues)


def test_missing_required_field():
    result = validate_invoice(make_inv(invoice_number=None))
    assert not result.valid
    assert any(i.field == "invoice_number" for i in result.issues)


def test_line_item_amount_mismatch_warning():
    inv = make_inv(line_items=[LineItemSchema(quantity=2, unit_price=500.0, amount=900.0)])
    result = validate_invoice(inv)
    assert any("line_items[0]" in (i.field or "") for i in result.issues)


def test_uncertain_fields_become_warnings():
    result = validate_invoice(make_inv(uncertain_fields=["total"]))
    assert any(i.severity == "warning" and i.field == "total" for i in result.issues)
    assert result.valid  # warnings don't invalidate
