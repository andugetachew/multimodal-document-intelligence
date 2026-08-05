from typing import TypedDict, Optional, Literal


class DocumentState(TypedDict, total=False):
    file_path: str
    file_type: Literal["native_pdf", "scanned_pdf", "image", "unknown"]

    extracted_text: str
    extraction_method: Literal["native", "ocr", "vision", "none"]
    confidence: float

    page_images: list[str]      # rendered page image paths, for OCR/vision fallback
    metadata: dict

    error: Optional[str]
    retry_count: int