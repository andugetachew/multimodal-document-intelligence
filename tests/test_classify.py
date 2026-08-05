import os
import tempfile
import pytest

from app.services.extraction.classify import detect_document_type


def test_detect_image_extension():
    assert detect_document_type("photo.jpg") == "image"
    assert detect_document_type("scan.png") == "image"
    assert detect_document_type("doc.webp") == "image"


def test_detect_unknown_extension():
    assert detect_document_type("file.xyz") == "unknown"
    assert detect_document_type("archive.zip") == "unknown"


def test_detect_native_pdf_with_real_text(tmp_path):
    import fitz

    pdf_path = tmp_path / "native.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "This is a real text-based PDF with plenty of content to exceed the character threshold for native detection.")
    doc.save(str(pdf_path))
    doc.close()

    assert detect_document_type(str(pdf_path)) == "native_pdf"


def test_detect_scanned_pdf_with_no_text(tmp_path):
    import fitz

    pdf_path = tmp_path / "scanned.pdf"
    doc = fitz.open()
    doc.new_page()  # blank page, no text layer
    doc.save(str(pdf_path))
    doc.close()

    assert detect_document_type(str(pdf_path)) == "scanned_pdf"


def test_detect_corrupt_pdf_returns_unknown(tmp_path):
    fake_pdf = tmp_path / "corrupt.pdf"
    fake_pdf.write_bytes(b"not a real pdf file")

    assert detect_document_type(str(fake_pdf)) == "unknown"