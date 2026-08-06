import pytest
from unittest.mock import patch
from app.graph import nodes


def test_route_native_pdf_goes_to_native_extraction():
    state = {"file_type": "native_pdf"}
    assert nodes.route_by_type(state) == "extract_native"


def test_route_scanned_pdf_goes_to_ocr():
    state = {"file_type": "scanned_pdf"}
    assert nodes.route_by_type(state) == "extract_ocr"


def test_route_image_goes_to_ocr():
    state = {"file_type": "image"}
    assert nodes.route_by_type(state) == "extract_ocr"


def test_route_unknown_falls_back_to_vision():
    state = {"file_type": "unknown"}
    assert nodes.route_by_type(state) == "extract_vision"


def test_high_confidence_ocr_does_not_escalate():
    state = {"confidence": 0.95}
    assert nodes.should_escalate_to_vision(state) == "done"


def test_low_confidence_ocr_escalates_to_vision():
    state = {"confidence": 0.3}
    assert nodes.should_escalate_to_vision(state) == "extract_vision"


def test_confidence_exactly_at_threshold_does_not_escalate():
    from app.core.config import get_settings
    threshold = get_settings().OCR_CONFIDENCE_THRESHOLD
    state = {"confidence": threshold}
    assert nodes.should_escalate_to_vision(state) == "done"

def test_route_docx_goes_to_docx_extraction():
    state = {"file_type": "docx"}
    assert nodes.route_by_type(state) == "extract_docx"


def test_route_csv_goes_to_csv_extraction():
    state = {"file_type": "csv"}
    assert nodes.route_by_type(state) == "extract_csv"

@patch("app.services.extraction.native.extract_native_text")
def test_extract_native_node_sets_fields(mock_extract):
    mock_extract.return_value = "extracted content"
    state = {"file_path": "fake.pdf"}

    result = nodes.extract_native(state)

    assert result["extracted_text"] == "extracted content"
    assert result["extraction_method"] == "native"
    assert result["confidence"] == 1.0


@patch("app.services.extraction.docx_extractor.extract_docx_text")
def test_extract_docx_node_sets_fields(mock_extract):
    mock_extract.return_value = "docx content"
    state = {"file_path": "fake.docx"}

    result = nodes.extract_docx(state)

    assert result["extracted_text"] == "docx content"
    assert result["extraction_method"] == "docx"


@patch("app.graph.nodes.extract_native_text")
def test_extract_native_node_sets_fields(mock_extract):
    mock_extract.return_value = "extracted content"
    state = {"file_path": "fake.pdf"}

    result = nodes.extract_native(state)

    assert result["extracted_text"] == "extracted content"
    assert result["extraction_method"] == "native"
    assert result["confidence"] == 1.0


@patch("app.graph.nodes.run_ocr_on_pages")
def test_extract_ocr_node_sets_fields(mock_ocr):
    mock_ocr.return_value = ("ocr text", 0.85, ["page1.png"])
    state = {"file_path": "fake.png"}

    result = nodes.extract_ocr(state)

    assert result["extracted_text"] == "ocr text"
    assert result["confidence"] == 0.85
    assert result["page_images"] == ["page1.png"]


@patch("app.graph.nodes.extract_with_vision")
def test_extract_vision_node_sets_fields(mock_vision):
    mock_vision.return_value = "vision extracted text"
    state = {"file_path": "fake.png"}

    result = nodes.extract_vision(state)

    assert result["extracted_text"] == "vision extracted text"
    assert result["extraction_method"] == "vision"
    assert result["confidence"] == 0.95