from unittest.mock import patch, MagicMock

from app.services.vision.claude_vision import extract_with_vision


@patch("app.services.vision.claude_vision.client")
def test_extract_with_vision_returns_text(mock_client, tmp_path):
    image_path = tmp_path / "test.png"
    image_path.write_bytes(b"\x89PNG\r\n\x1a\n fake png bytes")

    mock_text_block = MagicMock()
    mock_text_block.type = "text"
    mock_text_block.text = "Extracted text from the image."

    mock_response = MagicMock()
    mock_response.content = [mock_text_block]
    mock_client.messages.create.return_value = mock_response

    result = extract_with_vision([str(image_path)], model="claude-haiku-4-5-20251001")

    assert result == "Extracted text from the image."
    mock_client.messages.create.assert_called_once()


@patch("app.services.vision.claude_vision.client")
def test_extract_with_vision_multiple_images(mock_client, tmp_path):
    img1 = tmp_path / "page1.png"
    img2 = tmp_path / "page2.jpg"
    img1.write_bytes(b"fake png")
    img2.write_bytes(b"fake jpg")

    mock_text_block = MagicMock()
    mock_text_block.type = "text"
    mock_text_block.text = "Combined text."

    mock_response = MagicMock()
    mock_response.content = [mock_text_block]
    mock_client.messages.create.return_value = mock_response

    result = extract_with_vision([str(img1), str(img2)], model="claude-haiku-4-5-20251001")

    assert result == "Combined text."

    call_args = mock_client.messages.create.call_args
    content_blocks = call_args.kwargs["messages"][0]["content"]
    image_blocks = [b for b in content_blocks if b["type"] == "image"]
    assert len(image_blocks) == 2