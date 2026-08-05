import fitz

from app.services.extraction.native import extract_native_text


def test_extract_text_from_single_page(tmp_path):
    pdf_path = tmp_path / "single_page.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Hello from a single page PDF.")
    doc.save(str(pdf_path))
    doc.close()

    result = extract_native_text(str(pdf_path))

    assert "Hello from a single page PDF." in result


def test_extract_text_from_multiple_pages(tmp_path):
    pdf_path = tmp_path / "multi_page.pdf"
    doc = fitz.open()

    page1 = doc.new_page()
    page1.insert_text((72, 72), "Content on page one.")

    page2 = doc.new_page()
    page2.insert_text((72, 72), "Content on page two.")

    doc.save(str(pdf_path))
    doc.close()

    result = extract_native_text(str(pdf_path))

    assert "Content on page one." in result
    assert "Content on page two." in result


def test_extract_text_from_blank_pdf_returns_empty_string(tmp_path):
    pdf_path = tmp_path / "blank.pdf"
    doc = fitz.open()
    doc.new_page()
    doc.save(str(pdf_path))
    doc.close()

    result = extract_native_text(str(pdf_path))

    assert result == ""