"""Plain-text and Word document extraction."""
import os

TEXT_EXTS = {".txt", ".md", ".log"}
DOCX_EXTS = {".docx"}


def extract_txt_text(path: str) -> str:
    for encoding in ("utf-8", "utf-16", "latin-1"):
        try:
            with open(path, "r", encoding=encoding) as f:
                return f.read()
        except (UnicodeDecodeError, UnicodeError):
            continue
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def extract_docx_text(path: str) -> str:
    import docx

    document = docx.Document(path)
    parts = []
    for para in document.paragraphs:
        if para.text.strip():
            parts.append(para.text)
    for table in document.tables:
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells]
            if any(cells):
                parts.append(" | ".join(cells))
    return "\n".join(parts)


def extract_text_file(path: str, filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    if ext in TEXT_EXTS:
        return extract_txt_text(path)
    if ext in DOCX_EXTS:
        return extract_docx_text(path)
    raise ValueError(f"Unsupported text file type: {ext}")
