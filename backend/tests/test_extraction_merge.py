"""Tests for chunked extraction and merge logic (no LLM calls)."""
from app.ai import extraction
from app.ai.extraction import _chunk_text, _merge_extractions
from app.schemas import InvoiceExtraction, LineItemSchema


def test_chunk_text_small_doc_single_chunk():
    assert _chunk_text("short text") == ["short text"]


def test_chunk_text_large_doc_multiple_chunks():
    text = "x" * (extraction.MAX_TEXT_CHARS * 2 + 500)
    chunks = _chunk_text(text)
    assert len(chunks) == 3
    # overlap preserved
    assert chunks[1].startswith(chunks[0][-extraction.CHUNK_OVERLAP:][:10])


def test_chunk_text_respects_max_chunks():
    text = "x" * (extraction.MAX_TEXT_CHARS * 100)
    assert len(_chunk_text(text)) == extraction.MAX_CHUNKS


def test_merge_first_non_null_wins():
    a = InvoiceExtraction(invoice_number="INV-1", supplier_name="A Corp", total=100.0)
    b = InvoiceExtraction(invoice_number="INV-2", supplier_name="B Corp", total=200.0)
    merged = _merge_extractions([a, b])
    assert merged.invoice_number == "INV-1"
    assert merged.supplier_name == "A Corp"


def test_merge_fills_nulls_from_later_chunks():
    a = InvoiceExtraction(total=100.0)
    b = InvoiceExtraction(invoice_number="INV-9", currency="USD")
    merged = _merge_extractions([a, b])
    assert merged.invoice_number == "INV-9"
    assert merged.currency == "USD"
    assert merged.total == 100.0


def test_merge_line_items_deduped():
    item = LineItemSchema(description="Widget", amount=10.0)
    a = InvoiceExtraction(line_items=[item])
    b = InvoiceExtraction(line_items=[item, LineItemSchema(description="Gadget", amount=5.0)])
    merged = _merge_extractions([a, b])
    assert len(merged.line_items) == 2


def test_merge_missing_uncertain_unioned():
    a = InvoiceExtraction(missing_fields=["tax"], uncertain_fields=["total"])
    b = InvoiceExtraction(missing_fields=["currency"], uncertain_fields=["total", "date"])
    merged = _merge_extractions([a, b])
    assert merged.missing_fields == ["currency", "tax"]
    assert merged.uncertain_fields == ["date", "total"]
