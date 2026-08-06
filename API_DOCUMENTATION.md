# API Documentation

Base URL (local): `http://localhost:8020`
Interactive docs (Swagger UI): `http://localhost:8020/docs`

All endpoints return JSON. Timestamps are ISO 8601, UTC.

---

## Health Check

### `GET /health`

Simple liveness check.

**Response `200`**
```json
{ "status": "ok" }
```

---

## Documents

### `POST /documents/upload`

Uploads a document, stores it in S3-compatible storage, creates a database record with status `pending`, and dispatches an async Celery task to process it. Returns immediately — does not wait for extraction to complete.

**Request**
`multipart/form-data`

| Field | Type | Required | Description |
|---|---|---|---|
| `file` | file | yes | The document to upload. Supported: `.pdf`, `.png`, `.jpg`, `.jpeg`, `.webp`, `.tiff`, `.bmp`, `.docx`, `.csv` |

**Constraints**
- Max file size: configurable via `MAX_UPLOAD_SIZE_MB` (default 25 MB). Files over the limit are rejected before upload completes.

**Response `200`**
```json
{
  "id": "abe04b46-d7ba-4ff4-9c2f-1449f50d2c58",
  "original_filename": "cover-letter.pdf",
  "status": "pending",
  "file_type": null,
  "extraction_method": null,
  "confidence": null,
  "extracted_text": null,
  "error": null,
  "created_at": "2026-08-05T20:03:41.426882Z"
}
```

**Error responses**
| Status | Condition |
|---|---|
| `413` | File exceeds `MAX_UPLOAD_SIZE_MB` |
| `502` | Storage upload to S3/MinIO failed |

---

### `GET /documents/{document_id}`

Fetches the current state of a document by ID. Poll this after upload to track processing progress.

**Path parameters**
| Param | Type | Description |
|---|---|---|
| `document_id` | UUID | The document's ID, returned from the upload endpoint |

**Response `200`**
```json
{
  "id": "abe04b46-d7ba-4ff4-9c2f-1449f50d2c58",
  "original_filename": "cover-letter.pdf",
  "status": "completed",
  "file_type": "native_pdf",
  "extraction_method": "native",
  "confidence": 1.0,
  "extracted_text": "Full extracted text...",
  "error": null,
  "created_at": "2026-08-05T20:03:41.426882Z"
}
```

**Status values**
| Status | Meaning |
|---|---|
| `pending` | Uploaded, waiting for a worker to pick it up |
| `processing` | Worker is actively running the extraction pipeline |
| `completed` | Extraction finished successfully |
| `failed` | Extraction failed — see `error` field for details |

**`file_type` values**: `native_pdf`, `scanned_pdf`, `image`, `docx`, `csv`, `unknown`
**`extraction_method` values**: `native`, `ocr`, `vision`, `docx`, `csv`, `none`

**Error responses**
| Status | Condition |
|---|---|
| `404` | No document with that ID exists |

---

### `GET /documents`

Lists documents, most recently created first.

**Query parameters**
| Param | Type | Default | Constraints | Description |
|---|---|---|---|---|
| `limit` | int | 20 | 1–100 | Max number of results |
| `offset` | int | 0 | ≥ 0 | Pagination offset |

**Response `200`**
```json
[
  {
    "id": "abe04b46-d7ba-4ff4-9c2f-1449f50d2c58",
    "original_filename": "cover-letter.pdf",
    "status": "completed",
    "file_type": "native_pdf",
    "extraction_method": "native",
    "confidence": 1.0,
    "extracted_text": "...",
    "error": null,
    "created_at": "2026-08-05T20:03:41.426882Z"
  }
]
```

---

### `DELETE /documents/{document_id}`

Deletes a document's database record and its associated file in storage.

**Path parameters**
| Param | Type | Description |
|---|---|---|
| `document_id` | UUID | The document's ID |

**Response `204`**
No content.

**Behavior notes**
- Storage deletion is best-effort: if the S3/MinIO delete fails, the database row is still removed. A stranded file in storage is treated as a cost issue, not a correctness issue — consistent with the deletion pattern used elsewhere in this system.

**Error responses**
| Status | Condition |
|---|---|
| `404` | No document with that ID exists |

---

## Typical flow
POST /documents/upload → { id, status: "pending" }
GET /documents/{id} (poll) → status: "processing"
GET /documents/{id} (poll) → status: "completed", extracted_text populated

## Error object shape

All error responses follow FastAPI's standard shape:
```json
{ "detail": "human-readable error message" }