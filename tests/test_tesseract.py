from unittest.mock import patch, MagicMock
from PIL import Image

from app.services.ocr.tesseract import run_ocr_on_pages


@patch("app.services.ocr.tesseract.pytesseract")
def test_run_ocr_on_single_image(mock_tesseract, tmp_path):
    image_path = tmp_path / "test.png"
    img = Image.new("RGB", (100, 100), color="white")
    img.save(str(image_path))

    mock_tesseract.image_to_data.return_value = {
        "text": ["Hello", "World", ""],
        "conf": ["95", "90", "-1"],
    }
    mock_tesseract.Output.DICT = "dict"

    text, confidence, page_images = run_ocr_on_pages(str(image_path))

    assert "Hello World" in text
    assert confidence == pytest_approx_92_5()
    assert len(page_images) == 1


def pytest_approx_92_5():
    import pytest
    return pytest.approx(0.925, rel=0.01)


@patch("app.services.ocr.tesseract.pytesseract")
def test_run_ocr_filters_negative_confidence(mock_tesseract, tmp_path):
    image_path = tmp_path / "noisy.png"
    img = Image.new("RGB", (100, 100), color="white")
    img.save(str(image_path))

    mock_tesseract.image_to_data.return_value = {
        "text": ["Real", "", "text", ""],
        "conf": ["80", "-1", "70", "-1"],
    }
    mock_tesseract.Output.DICT = "dict"

    text, confidence, page_images = run_ocr_on_pages(str(image_path))

    assert confidence == pytest_approx_75()


def pytest_approx_75():
    import pytest
    return pytest.approx(0.75, rel=0.01)


@patch("app.services.ocr.tesseract.convert_from_path")
@patch("app.services.ocr.tesseract.pytesseract")
def test_run_ocr_on_pdf_uses_convert_from_path(mock_tesseract, mock_convert, tmp_path):
    fake_pdf = tmp_path / "scan.pdf"
    fake_pdf.write_bytes(b"%PDF-1.4 fake")

    fake_page = Image.new("RGB", (100, 100), color="white")
    mock_convert.return_value = [fake_page]

    mock_tesseract.image_to_data.return_value = {
        "text": ["Scanned", "text"],
        "conf": ["88", "92"],
    }
    mock_tesseract.Output.DICT = "dict"

    text, confidence, page_images = run_ocr_on_pages(str(fake_pdf))

    mock_convert.assert_called_once()
    assert "Scanned text" in text