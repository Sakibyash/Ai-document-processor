"""End-to-end API test: upload CSV -> pipeline (mocked LLM) -> validation issues stored."""
import pytest
from fastapi.testclient import TestClient

from app.ai import extraction
from app.main import app
from app.schemas import InvoiceExtraction, LineItemSchema


@pytest.fixture()
def client(monkeypatch):
    fake = InvoiceExtraction(
        invoice_number="CSV-001",
        invoice_date="2026-02-01",
        supplier_name="CSV Supplier",
        customer_name="CSV Customer",
        subtotal=200.0,
        tax=30.0,
        total=999.0,  # deliberate mismatch
        currency="USD",
        line_items=[LineItemSchema(description="Item", quantity=1, unit_price=200.0, amount=200.0)],
    )
    monkeypatch.setattr(extraction, "extract_invoice", lambda text: fake)
    return TestClient(app)


def test_upload_csv_pipeline(client):
    csv_content = b"description,quantity,unit_price,amount\nWidget,1,200,200\n"
    resp = client.post(
        "/api/uploads",
        files={"file": ("invoices.csv", csv_content, "text/csv")},
    )
    assert resp.status_code == 200, resp.text
    doc = resp.json()
    assert doc["status"] in ("uploaded", "processing", "completed")

    # Pipeline runs eagerly via fallback; poll the document endpoint
    final = None
    for _ in range(20):
        final = client.get(f"/api/documents/{doc['id']}").json()
        if final["status"] in ("completed", "failed"):
            break
    assert final["status"] == "completed", final.get("error_message")
    assert final["invoice"]["invoice_number"] == "CSV-001"

    issues = [i for i in final["validation_issues"] if not i["resolved"]]
    assert any(i["field"] == "total" for i in issues)


def test_unsupported_type_rejected(client):
    resp = client.post(
        "/api/uploads",
        files={"file": ("evil.exe", b"MZ", "application/octet-stream")},
    )
    assert resp.status_code == 400
