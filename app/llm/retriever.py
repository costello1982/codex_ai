"""Simple Chroma-backed retriever."""
from __future__ import annotations

from chromadb import PersistentClient


class Retriever:
    def __init__(self, persist_dir: str, collection_name: str = "cisco_docs") -> None:
        client = PersistentClient(path=persist_dir)
        self.collection = client.get_or_create_collection(collection_name)

    def add(self, ids: list[str], docs: list[str], metadatas: list[dict]) -> None:
        self.collection.add(ids=ids, documents=docs, metadatas=metadatas)

    def query(self, question: str, k: int = 4) -> list[dict]:
        result = self.collection.query(query_texts=[question], n_results=k)
        docs = result.get("documents", [[]])[0]
        metas = result.get("metadatas", [[]])[0]
        return [{"text": d, "metadata": m} for d, m in zip(docs, metas)]
