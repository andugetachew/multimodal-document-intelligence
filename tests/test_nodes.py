import pytest

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