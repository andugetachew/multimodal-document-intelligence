# Architecture

## Overview

This system exists to solve one problem: documents arrive in inconsistent formats, and no single extraction method works for all of them. A clean, text-based PDF should be parsed directly. A scanned contract needs OCR. A blurry phone photo needs a vision model. A Word doc or spreadsheet needs its own parser entirely. Rather than forcing one extraction method on every input, the system classifies each document first and routes it down the cheapest path that will actually work — escalating to more expensive methods only when necessary.

## Request lifecycle
Client → POST /documents/upload
API reads the file, uploads it to S3-compatible storage (MinIO/S3)
API creates a Document row in PostgreSQL with status=pending
API dispatches a Celery task (process_document) and returns immediately
Celery worker picks up the task:
a. Downloads the file from storage to a temp local path
b. Runs it through the LangGraph pipeline
c. Writes the result back to PostgreSQL (status=completed or failed)
d. Deletes the temp local file
Client polls GET /documents/{id} until status is completed or failed

The upload endpoint never blocks on extraction — this matters because vision-model calls can take several seconds, and OCR on a large scanned PDF is not instant. Keeping the HTTP request/response cycle fast and moving real work to a background worker is a standard pattern for this class of problem.

## The LangGraph pipeline
                classify_document
                      │
    ┌────────┬────────┼────────┬────────┐

native_pdf scanned_pdf/img docx csv unknown
│ │ │ │ │
extract_native extract_ocr extract_docx extract_csv │
│ │ │ │ │
END confidence END END │
check │
┌────┴────┐ │
sufficient too low ─────────────────────────┘
│ │
END extract_vision
│
END


### Why LangGraph, not a plain function chain

The pipeline isn't strictly linear — it has a genuine branching decision (which extraction method fits this document type) and a genuine conditional retry (escalate to vision if OCR confidence is too low). LangGraph's `StateGraph` models this as an explicit state machine: each node is a pure function that receives the current state and returns an updated state, and edges are either fixed or conditional (a function that inspects state and returns the next node's name). This makes the routing logic testable in isolation — `route_by_type()` and `should_escalate_to_vision()` are plain functions with no side effects, tested directly without running the whole pipeline or touching any external service.

### Classification (`classify_document`)

- File extension determines the initial bucket: image extensions → `image`; `.docx` → `docx`; `.csv` → `csv`; `.pdf` → sampled for a text layer.
- For PDFs specifically, the first 3 pages are sampled with PyMuPDF (`page.get_text()`), and average characters-per-page is compared against a threshold (`MIN_CHARS_FOR_NATIVE = 50`). Above the threshold, it's `native_pdf`; below it (or zero), it's `scanned_pdf` — meaning it has a valid PDF structure but no usable embedded text layer, so it needs OCR just like an image would.

### Extraction methods

| Method | Node | Library | Confidence |
|---|---|---|---|
| Native PDF text | `extract_native` | PyMuPDF (`fitz`) | Always 1.0 — deterministic |
| OCR | `extract_ocr` | Tesseract via `pytesseract`, `pdf2image` for PDF→image rendering | Computed from Tesseract's per-word confidence scores |
| DOCX | `extract_docx` | `python-docx` | Always 1.0 — deterministic |
| CSV | `extract_csv` | Python's built-in `csv` module | Always 1.0 — deterministic |
| Vision | `extract_vision` | Anthropic Claude API (vision-capable model) | Fixed at 0.95 — treated as high-trust since it's the fallback of last resort |

DOCX and CSV are treated as deterministic, structured formats — there's no meaningful "confidence" concept the way there is for OCR, since the parser either successfully reads the file's actual content or fails outright (caught as a task-level error, not a low-confidence result).

### The escalation decision

```python
def should_escalate_to_vision(state):
    if state.get("confidence", 0) < settings.OCR_CONFIDENCE_THRESHOLD:
        return "extract_vision"
    return "done"
```

`OCR_CONFIDENCE_THRESHOLD` defaults to `0.6`. Tesseract returns per-word confidence values, including `-1` for regions it couldn't confidently identify as text at all (as opposed to text it read with low confidence) — these `-1` values are filtered out before averaging, since including them artificially deflates the score and would over-trigger escalation on otherwise-readable images.

This threshold was validated empirically during development: a dark-mode UI screenshot with mixed text and icons scored `0.59` — just under threshold — correctly triggering escalation, while the same image with the threshold temporarily set to `0.0` completed via OCR alone with a lower-quality (but non-empty) result. This confirmed the routing logic behaves as intended in both directions.

## Async processing: Celery + Redis

Celery was chosen for the same reason as the DevOps pattern used elsewhere in this system's sibling project — background task processing decoupled from the request/response cycle, with Redis as both the message broker and result backend.

### A real bug and its fix

Each Celery task in this project runs the async pipeline via `asyncio.run(_process_document_async(...))` inside a synchronous task function — because Celery's task execution model is fundamentally synchronous, and the pipeline (DB writes, storage downloads) is written with `async`/`await`. `asyncio.run()` creates a **new event loop for every single task invocation**.

This collided with SQLAlchemy's async engine, which by default maintains a connection pool. The first task worked fine — but the second task, running in a *new* event loop, tried to reuse a pooled connection that was still bound to the *previous* task's event loop. `asyncpg` refuses this outright, since a connection cannot cross event loops: `RuntimeError: Task ... got Future ... attached to a different loop`.

**Fix**: the async engine uses `NullPool`:
```python
engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
```
Every operation opens a fresh connection instead of reusing a pooled one. This has minimal real-world cost here since Neon already pools connections server-side via PgBouncer — the client-side pool was redundant and actively harmful in this specific worker execution pattern.

## Storage: S3-compatible (MinIO locally)

Uploaded files are never kept on the API container's local disk beyond the initial read — they're immediately uploaded to S3-compatible storage (MinIO in local development, swappable for AWS S3 or Cloudflare R2 in production via `S3_ENDPOINT_URL`). This is deliberate: the Celery worker that eventually processes the file may be a **different container** than the one that received the upload. Local disk storage would make the file invisible to the worker. The worker downloads the file from storage to a temporary local path only for the duration of the extraction call (PyMuPDF/Tesseract need a real file path, not a byte stream), then deletes the temp file immediately after.

## Database: PostgreSQL via Neon

A single `documents` table holds all state: original filename, storage key, detected file type, extraction method used, confidence score, extracted text, processing status, and error message if failed. Timestamps are stored as timezone-aware (`DateTime(timezone=True)`) — an early version used naive timestamps, which caused a runtime error when `asyncpg` tried to insert a Python `datetime` object that carried UTC offset info into a column that didn't expect one. Fixed via an Alembic migration altering the column type.

## Testing strategy

- **Unit tests for pure logic** (`classify.py`, `nodes.py` routing functions, extractors) run with no mocking needed where possible — real PyMuPDF/python-docx calls against generated test fixtures.
- **External services are mocked at the boundary**: S3 calls (`boto3` client), the Anthropic API client, Tesseract's `pytesseract` calls, and Celery's `.delay()` dispatch are all patched in tests — this keeps the suite fast (a few seconds for 49 tests) and independent of any running infrastructure (no Docker required to run `pytest`).
- **API-level tests** use FastAPI's `dependency_overrides` to swap the real Neon-backed DB session for an isolated SQLite session per test, and `httpx.AsyncClient` with `ASGITransport` to call the app in-process without a running server.
- **Failure paths are tested explicitly**, not just happy paths — e.g., a storage-upload failure returning `502`, a Celery task's pipeline exception being caught and marking the document `failed` rather than leaving it stuck in `processing`.

Current coverage: 92%, with the remaining gap being infrastructure lifecycle code (app startup/shutdown, DB engine construction) that provides limited testing value relative to the effort of covering it.

## CI/CD

GitHub Actions runs on every push to `main`:
1. **`test` job**: installs dependencies (including system-level `tesseract-ocr` and `poppler-utils`), runs the full test suite with coverage reporting. No live infrastructure required — everything external is mocked.
2. **`build-and-push` job** (only runs after `test` passes, only on `main`): builds the multi-stage Docker image and pushes it to Docker Hub tagged with both `latest` and the commit SHA, so any deployed version is traceable back to an exact commit.

## What's built but not yet verified end-to-end

Vision-model escalation (`extract_vision` → Anthropic Claude API) is fully implemented and unit-tested with mocked API responses, but has not been verified against the live Anthropic API in this environment — the account is intentionally on a $0 balance while other spending priorities are addressed first. The routing logic that decides *when* to escalate has been validated (see the empirical confidence-threshold test above); what remains unverified is only the live API call itself, which is a thin, well-isolated piece of the system (`app/services/vision/claude_vision.py`).