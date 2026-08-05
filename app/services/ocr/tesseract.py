import os
import uuid
import pytesseract
from pdf2image import convert_from_path
from PIL import Image

from app.core.config import get_settings

settings = get_settings()
pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD

PAGE_IMAGE_DIR = "storage/page_images"


def run_ocr_on_pages(file_path: str) -> tuple[str, float, list[str]]:
    os.makedirs(PAGE_IMAGE_DIR, exist_ok=True)

    images = _load_images(file_path)
    page_image_paths = []
    all_text = []
    all_confidences = []

    for img in images:
        page_path = os.path.join(PAGE_IMAGE_DIR, f"{uuid.uuid4().hex}.png")
        img.save(page_path)
        page_image_paths.append(page_path)

        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
        words = [w for w in data["text"] if w.strip()]
        confidences = [
            float(c) for c, w in zip(data["conf"], data["text"])
            if w.strip() and c != "-1"
        ]

        all_text.append(" ".join(words))
        if confidences:
            all_confidences.append(sum(confidences) / len(confidences))

    full_text = "\n\n".join(all_text).strip()
    avg_confidence = (sum(all_confidences) / len(all_confidences) / 100) if all_confidences else 0.0

    return full_text, avg_confidence, page_image_paths


def _load_images(file_path: str) -> list[Image.Image]:
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        return convert_from_path(file_path, dpi=200)

    return [Image.open(file_path)]