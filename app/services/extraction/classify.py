import os
import fitz


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tiff", ".bmp"}
DOCX_EXTENSIONS = {".docx"}
CSV_EXTENSIONS = {".csv"}
MIN_CHARS_FOR_NATIVE = 50


def detect_document_type(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()

    if ext in IMAGE_EXTENSIONS:
        return "image"

    if ext in DOCX_EXTENSIONS:
        return "docx"

    if ext in CSV_EXTENSIONS:
        return "csv"

    if ext == ".pdf":
        return _classify_pdf(file_path)

    return "unknown"


def _classify_pdf(file_path: str) -> str:
    try:
        doc = fitz.open(file_path)
    except Exception:
        return "unknown"

    total_chars = 0
    pages_checked = min(3, doc.page_count)

    for i in range(pages_checked):
        total_chars += len(doc[i].get_text().strip())

    doc.close()

    avg_chars_per_page = total_chars / max(pages_checked, 1)
    return "native_pdf" if avg_chars_per_page >= MIN_CHARS_FOR_NATIVE else "scanned_pdf"