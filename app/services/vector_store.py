"""
Vector Store — ChromaDB integration for few-shot example retrieval.

Each person gets their own collection: person_{id}_examples.
At chat time, the current user message is embedded and the top-k most
similar few-shot examples are retrieved to inject into the system prompt.
"""

from __future__ import annotations

import chromadb
from chromadb.utils import embedding_functions

from app.config import settings

_client: chromadb.ClientAPI | None = None
_ef = embedding_functions.DefaultEmbeddingFunction()


def _get_client() -> chromadb.ClientAPI:
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=settings.chroma_path)
    return _client


def _collection_name(person_id: int) -> str:
    return f"person_{person_id}_examples"


def upsert_examples(person_id: int, examples: list[dict[str, str]]) -> None:
    """Store or replace few-shot examples for a person."""
    if not examples:
        return

    client = _get_client()
    col = client.get_or_create_collection(
        name=_collection_name(person_id),
        embedding_function=_ef,
    )

    # ChromaDB requires string IDs
    ids = [f"ex_{i}" for i in range(len(examples))]
    documents = [ex.get("user", "") for ex in examples]
    metadatas = [{"person_response": ex.get("person", "")} for ex in examples]

    col.upsert(ids=ids, documents=documents, metadatas=metadatas)


def retrieve_examples(person_id: int, query: str, k: int = 5) -> list[dict[str, str]]:
    """Return the top-k few-shot examples most similar to `query`."""
    client = _get_client()
    try:
        col = client.get_collection(name=_collection_name(person_id), embedding_function=_ef)
    except Exception:
        return []

    count = col.count()
    if count == 0:
        return []

    results = col.query(query_texts=[query], n_results=min(k, count))
    examples = []
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    for doc, meta in zip(docs, metas):
        examples.append({"user": doc, "person": meta.get("person_response", "")})
    return examples


def delete_collection(person_id: int) -> None:
    client = _get_client()
    try:
        client.delete_collection(name=_collection_name(person_id))
    except Exception:
        pass
