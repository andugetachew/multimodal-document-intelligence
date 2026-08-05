import fitz


def extract_native_text(file_path: str) -> str:
    doc = fitz.open(file_path)
    pages_text = []

    for page in doc:
        pages_text.append(page.get_text())

    doc.close()
    return "\n\n".join(pages_text).strip()