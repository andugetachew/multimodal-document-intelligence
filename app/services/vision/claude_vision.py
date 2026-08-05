import base64
import anthropic

from app.core.config import get_settings

settings = get_settings()
client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

EXTRACTION_PROMPT = (
    "Extract all readable text from this document image, preserving structure "
    "(headings, tables, lists) as plain text. Do not summarize or omit content. "
    "If the image contains no readable text, respond with an empty string."
)


def extract_with_vision(image_paths: list[str], model: str) -> str:
    content_blocks = []

    for path in image_paths:
        media_type = _media_type_for(path)
        with open(path, "rb") as f:
            encoded = base64.standard_b64encode(f.read()).decode("utf-8")

        content_blocks.append({
            "type": "image",
            "source": {"type": "base64", "media_type": media_type, "data": encoded},
        })

    content_blocks.append({"type": "text", "text": EXTRACTION_PROMPT})

    response = client.messages.create(
        model=model,
        max_tokens=4096,
        messages=[{"role": "user", "content": content_blocks}],
    )

    text_parts = [block.text for block in response.content if block.type == "text"]
    return "\n\n".join(text_parts).strip()


def _media_type_for(path: str) -> str:
    ext = path.rsplit(".", 1)[-1].lower()
    return {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "webp": "image/webp",
    }.get(ext, "image/png")