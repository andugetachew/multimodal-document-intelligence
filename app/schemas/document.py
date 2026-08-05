import uuid
from datetime import datetime
from pydantic import BaseModel


class DocumentResponse(BaseModel):
    id: uuid.UUID
    original_filename: str
    status: str
    file_type: str | None = None
    extraction_method: str | None = None
    confidence: float | None = None
    extracted_text: str | None = None
    error: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}