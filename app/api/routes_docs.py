"""Document ingestion and retrieval routes."""
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile

from app.core.config import settings
from app.llm.retriever import Retriever
from app.services.doc_ingest_service import DocIngestService

router = APIRouter(prefix="/docs", tags=["docs"])


@router.post("/ingest")
async def ingest_doc(file: UploadFile) -> dict:
    target = settings.docs_dir / file.filename
    settings.docs_dir.mkdir(parents=True, exist_ok=True)
    content = await file.read()
    target.write_bytes(content)
    count = DocIngestService().ingest_file(target)
    return {"chunks_ingested": count, "file": file.filename}


@router.get("/ask")
def ask(question: str) -> dict:
    try:
        hits = Retriever(str(settings.vectorstore_dir)).query(question)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return {"question": question, "results": hits}
