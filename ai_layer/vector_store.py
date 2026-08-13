from __future__ import annotations

import logging
from uuid import UUID

from ai_layer.config import settings
from ai_layer.storage import StoredChunk, StoredDocument

logger = logging.getLogger(__name__)

COLLECTION = "assitify_chunks"
VECTOR_SIZE = 1536  # text-embedding-3-small

_client = None
_client_failed = False


def _get_client():
    global _client, _client_failed
    if _client is not None:
        return _client
    if _client_failed or not settings.qdrant_url:
        return None
    try:
        from qdrant_client import QdrantClient

        kwargs: dict = {"url": settings.qdrant_url, "timeout": 10}
        if settings.qdrant_api_key:
            kwargs["api_key"] = settings.qdrant_api_key
        client = QdrantClient(**kwargs)
        client.get_collections()
        _client = client
        return _client
    except Exception as exc:  # noqa: BLE001
        _client_failed = True
        logger.warning("Qdrant unavailable (%s); skipping vector store.", exc)
        return None


def is_ready() -> bool:
    return _get_client() is not None


def _ensure_collection(client) -> None:
    from qdrant_client.http import models

    names = {item.name for item in client.get_collections().collections}
    if COLLECTION in names:
        return
    client.create_collection(
        collection_name=COLLECTION,
        vectors_config=models.VectorParams(size=VECTOR_SIZE, distance=models.Distance.COSINE),
    )
    client.create_payload_index(
        collection_name=COLLECTION,
        field_name="document_id",
        field_schema=models.PayloadSchemaType.KEYWORD,
    )


def _point_id(chunk_id: str) -> str:
    try:
        return str(UUID(chunk_id))
    except ValueError:
        return str(UUID(bytes=chunk_id.encode("utf-8")[:16].ljust(16, b"0")))


def delete_document_vectors(document_id: str) -> None:
    client = _get_client()
    if client is None:
        return
    from qdrant_client.http import models

    try:
        _ensure_collection(client)
        client.delete(
            collection_name=COLLECTION,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[models.FieldCondition(key="document_id", match=models.MatchValue(value=document_id))]
                )
            ),
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Qdrant delete failed for %s: %s", document_id, exc)


def upsert_chunks(document: StoredDocument, vectors: list[list[float]]) -> None:
    client = _get_client()
    if client is None or not document.chunks or len(vectors) != len(document.chunks):
        return
    from qdrant_client.http import models

    try:
        _ensure_collection(client)
        delete_document_vectors(document.id)
        points = [
            models.PointStruct(
                id=_point_id(chunk.id),
                vector=vector,
                payload=_payload(document, chunk),
            )
            for chunk, vector in zip(document.chunks, vectors, strict=True)
        ]
        client.upsert(collection_name=COLLECTION, points=points)
        logger.info("Indexed %s chunks in Qdrant for document %s", len(points), document.id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Qdrant upsert failed for %s: %s", document.id, exc)


def _payload(document: StoredDocument, chunk: StoredChunk) -> dict:
    return {
        "document_id": document.id,
        "filename": document.filename,
        "chunk_id": chunk.id,
        "chapter_id": chunk.chapter_id,
        "chapter_title": chunk.chapter_title,
        "chunk_index": chunk.chunk_index,
        "text": chunk.text,
    }


def search_chunks(document_id: str, query_vector: list[float], limit: int = 5) -> list[dict]:
    client = _get_client()
    if client is None:
        return []
    from qdrant_client.http import models

    try:
        _ensure_collection(client)
        results = client.search(
            collection_name=COLLECTION,
            query_vector=query_vector,
            limit=limit,
            query_filter=models.Filter(
                must=[models.FieldCondition(key="document_id", match=models.MatchValue(value=document_id))]
            ),
        )
        hits: list[dict] = []
        for point in results:
            payload = point.payload or {}
            text = (payload.get("text") or "").strip()
            if text:
                hits.append(payload)
        return hits
    except Exception as exc:  # noqa: BLE001
        logger.warning("Qdrant search failed for %s: %s", document_id, exc)
        return []
