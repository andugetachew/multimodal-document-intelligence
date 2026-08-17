import sys
print("STARTUP: main.py is loading", file=sys.stderr, flush=True)

from fastapi import FastAPI

from app.api.documents import router as documents_router
from app.services.storage.s3_client import ensure_bucket_exists

app = FastAPI(title="Multimodal Document Intelligence")

app.include_router(documents_router)


@app.on_event("startup")
async def startup_event():
    ensure_bucket_exists()


@app.get("/health")
async def health():
    return {"status": "ok"}