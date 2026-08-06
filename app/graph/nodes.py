from app.graph.state import DocumentState
from app.services.extraction.native import extract_native_text
from app.services.ocr.tesseract import run_ocr_on_pages
from app.services.vision.claude_vision import extract_with_vision
from app.core.config import get_settings

settings = get_settings()


def classify_document(state: DocumentState) -> DocumentState:
    """Decide whether the PDF has extractable text or needs OCR/vision."""
    from app.services.extraction.classify import detect_document_type

    doc_type = detect_document_type(state["file_path"])
    return {**state, "file_type": doc_type, "retry_count": 0}


def extract_native(state: DocumentState) -> DocumentState:
    text = extract_native_text(state["file_path"])
    return {
        **state,
        "extracted_text": text,
        "extraction_method": "native",
        "confidence": 1.0,
    }


def extract_ocr(state: DocumentState) -> DocumentState:
    text, confidence, page_images = run_ocr_on_pages(state["file_path"])
    return {
        **state,
        "extracted_text": text,
        "extraction_method": "ocr",
        "confidence": confidence,
        "page_images": page_images,
    }
def extract_docx(state: DocumentState) -> DocumentState:
    from app.services.extraction.docx_extractor import extract_docx_text

    text = extract_docx_text(state["file_path"])
    return {
        **state,
        "extracted_text": text,
        "extraction_method": "docx",
        "confidence": 1.0,
    }


def extract_csv(state: DocumentState) -> DocumentState:
    from app.services.extraction.csv_extractor import extract_csv_text

    text = extract_csv_text(state["file_path"])
    return {
        **state,
        "extracted_text": text,
        "extraction_method": "csv",
        "confidence": 1.0,
    }


def extract_vision(state: DocumentState) -> DocumentState:
    """Escalation path: used when OCR confidence is too low, or file is image-only."""
    text = extract_with_vision(
        state.get("page_images") or [state["file_path"]],
        model=settings.ANTHROPIC_VISION_MODEL,
    )
    return {
        **state,
        "extracted_text": text,
        "extraction_method": "vision",
        "confidence": 0.95,  # vision extraction treated as high-trust
    }


def should_escalate_to_vision(state: DocumentState) -> str:
    """Conditional edge: route to vision model if OCR confidence too low."""
    if state.get("confidence", 0) < settings.OCR_CONFIDENCE_THRESHOLD:
        return "extract_vision"
    return "done"

def route_by_type(state: DocumentState) -> str:
    match state["file_type"]:
        case "native_pdf":
            return "extract_native"
        case "scanned_pdf" | "image":
            return "extract_ocr"
        case "docx":
            return "extract_docx"
        case "csv":
            return "extract_csv"
        case _:
            return "extract_vision"