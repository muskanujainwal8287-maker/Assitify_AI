from __future__ import annotations

import logging

from ai_layer.embedding_service import embed_texts
from ai_layer.storage import StoredDocument
from ai_layer.vector_store import delete_document_vectors, search_chunks, upsert_chunks

logger = logging.getLogger(__name__)


def index_document(document: StoredDocument) -> None:
    """Embed document chunks and upsert them into Qdrant. No-op if embeddings/Qdrant are down."""
    if not document.chunks:
        delete_document_vectors(document.id)
        return
    vectors = embed_texts([chunk.text for chunk in document.chunks])
    if not vectors:
        logger.info("Vector index skipped for %s (embeddings unavailable).", document.id)
        return
    upsert_chunks(document, vectors)


def retrieve_context(document_id: str, question: str, fallback_text: str, *, limit: int = 5) -> str:
    """Return top matching chunk text, or the full document if retrieval fails."""
    query_vectors = embed_texts([question])
    if not query_vectors:
        return fallback_text
    hits = search_chunks(document_id, query_vectors[0], limit=limit)
    if not hits:
        return fallback_text
    parts = []
    for hit in hits:
        title = (hit.get("chapter_title") or "").strip()
        text = (hit.get("text") or "").strip()
        if title:
            parts.append(f"[{title}]\n{text}")
        else:
            parts.append(text)
    return "\n\n---\n\n".join(parts)
