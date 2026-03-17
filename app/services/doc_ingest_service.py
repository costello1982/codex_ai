"""Ingest Cisco documents into vector store."""
from __future__ import annotations

from pathlib import Path
import pdfplumber

from app.core.config import settings
from app.llm.chunking import chunk_text
from app.llm.retriever import Retriever


class DocIngestService:
    def __init__(self) -> None:
        self.retriever = Retriever(str(settings.vectorstore_dir))

    def _extract_text(self, file_path: Path) -> list[tuple[int, str]]:
        if file_path.suffix.lower() == ".pdf":
            pages: list[tuple[int, str]] = []
            with pdfplumber.open(file_path) as pdf:
                for i, page in enumerate(pdf.pages, start=1):
                    pages.append((i, page.extract_text() or ""))
            return pages
        text = file_path.read_text(encoding="utf-8")
        return [(1, text)]

    def ingest_file(self, file_path: Path) -> int:
        pages = self._extract_text(file_path)
        ids, docs, metas = [], [], []
        for page_num, text in pages:
            for idx, chunk in enumerate(chunk_text(text)):
                ids.append(f"{file_path.stem}-{page_num}-{idx}")
                docs.append(chunk)
                metas.append({"source": file_path.name, "page": page_num, "section": f"chunk-{idx}"})
        if ids:
            self.retriever.add(ids, docs, metas)
        return len(ids)
