"""Format detection and dispatch to the right processor."""
import os

from app.processors import excel_processor, image_processor, pdf_processor, text_processor

PDF_EXTS = {".pdf"}


def detect_kind(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    if ext in PDF_EXTS:
        return "pdf"
    if ext in image_processor.SUPPORTED:
        return "image"
    if ext in excel_processor.EXCEL_EXTS:
        return "excel"
    if ext in excel_processor.CSV_EXTS:
        return "csv"
    if ext in text_processor.TEXT_EXTS or ext in text_processor.DOCX_EXTS:
        return "text"
    raise ValueError(f"Unsupported file type: {ext or '(none)'}")


def extract_text(path: str, filename: str) -> str:
    kind = detect_kind(filename)
    if kind == "pdf":
        text, _pages = pdf_processor.extract_pdf_text(path)
        return text
    if kind == "image":
        return image_processor.extract_image_text(path)
    if kind == "excel":
        return excel_processor.extract_excel_text(path)
    if kind == "csv":
        return excel_processor.extract_csv_text(path)
    if kind == "text":
        return text_processor.extract_text_file(path, filename)
    raise ValueError(f"Unhandled kind: {kind}")
