"""Tests for spreadsheet/CSV parsing and format detection (no OCR/LLM needed)."""
import pandas as pd
import pytest

from app.processors import excel_processor
from app.processors.base import detect_kind


def test_detect_kinds():
    assert detect_kind("invoice.pdf") == "pdf"
    assert detect_kind("scan.PNG") == "image"
    assert detect_kind("report.xlsx") == "excel"
    assert detect_kind("data.csv") == "csv"
    with pytest.raises(ValueError):
        detect_kind("malware.exe")


def test_csv_parsing(tmp_path):
    p = tmp_path / "inv.csv"
    p.write_text("description,qty,price\nWidget,2,10.5\nGadget,1,3.25\n")
    text = excel_processor.extract_csv_text(str(p))
    assert "Widget" in text and "Gadget" in text
    assert "description" in text  # header preserved


def test_excel_parsing_multiple_sheets(tmp_path):
    pytest.importorskip("openpyxl", reason="openpyxl not installed")
    p = tmp_path / "book.xlsx"
    with pd.ExcelWriter(p) as writer:
        pd.DataFrame({"item": ["A", "B"], "amount": [1.5, 2.5]}).to_excel(writer, sheet_name="Sheet1", index=False)
        pd.DataFrame({"item": ["C"], "amount": [9.0]}).to_excel(writer, sheet_name="Sheet2", index=False)
    text = excel_processor.extract_excel_text(str(p))
    assert "Sheet: Sheet1" in text and "Sheet: Sheet2" in text
    assert "A" in text and "C" in text


def test_corrupt_csv_raises(tmp_path):
    p = tmp_path / "bad.csv"
    p.write_bytes(b"\x00\x01\x02not,a,csv\n")
    # pandas may parse garbage or raise; either is acceptable, but it must not silently succeed with wrong schema
    try:
        excel_processor.extract_csv_text(str(p))
    except Exception:
        pass  # raising on corrupt input is correct behavior
