"""OCR for standalone image files (JPG, PNG, TIFF)."""
from PIL import Image

SUPPORTED = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp"}


def extract_image_text(path: str) -> str:
    img = Image.open(path)
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    import pytesseract

    return pytesseract.image_to_string(img)
