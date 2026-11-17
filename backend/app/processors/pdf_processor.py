"""PDF text extraction: digital text via PyMuPDF, OCR fallback for scanned pages."""
import io

from PIL import Image

MAX_OCR_PAGES = 20  # cap OCR work per document


def extract_pdf_text(path: str) -> tuple[str, int]:
    """Returns (text, page_count). Uses embedded text; OCRs pages with little text."""
    import fitz  # PyMuPDF — lazy import so module loads without it installed

    doc = fitz.open(path)
    pages_text: list[str] = []
    ocr_pages = 0

    for i, page in enumerate(doc):
        text = page.get_text("text").strip()
        # Heuristic: scanned pages have almost no extractable text
        if len(text) < 30 and ocr_pages < MAX_OCR_PAGES:
            pix = page.get_pixmap(dpi=200)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            text = _ocr_image(img)
            ocr_pages += 1
        pages_text.append(f"--- Page {i + 1} ---\n{text}")

    doc.close()
    return "\n\n".join(pages_text), len(pages_text)


def _ocr_image(img: Image.Image) -> str:
    import pytesseract

    return pytesseract.image_to_string(img)
