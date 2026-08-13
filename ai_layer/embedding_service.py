from __future__ import annotations

import logging

from openai import APIError, OpenAI

from ai_layer.config import settings

logger = logging.getLogger(__name__)

_client: OpenAI | None = None
_EMBED_BATCH = 64


def _client_or_none() -> OpenAI | None:
    global _client
    if not settings.openai_api_key:
        return None
    if _client is None:
        _client = OpenAI(api_key=settings.openai_api_key)
    return _client


def embed_texts(texts: list[str]) -> list[list[float]] | None:
    """Return one embedding per text, or None if embeddings are unavailable."""
    if not texts:
        return []
    client = _client_or_none()
    if client is None:
        logger.warning("Skipping embeddings: OPENAI_API_KEY is not set.")
        return None

    vectors: list[list[float]] = []
    try:
        for start in range(0, len(texts), _EMBED_BATCH):
            batch = [item if item.strip() else " " for item in texts[start : start + _EMBED_BATCH]]
            response = client.embeddings.create(model=settings.embed_model, input=batch)
            ordered = sorted(response.data, key=lambda row: row.index)
            vectors.extend(item.embedding for item in ordered)
    except APIError as exc:
        logger.warning("Embedding API error: %s", exc)
        return None
    except Exception as exc:  # noqa: BLE001
        logger.warning("Embedding failed: %s: %s", type(exc).__name__, exc)
        return None

    if len(vectors) != len(texts):
        logger.warning("Embedding count mismatch (%s != %s).", len(vectors), len(texts))
        return None
    return vectors
