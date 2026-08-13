from __future__ import annotations

import logging

from ai_layer.config import settings
from ai_layer.repositories.base import DocumentRepository
from ai_layer.repositories.memory_repo import InMemoryDocumentRepository

logger = logging.getLogger(__name__)

_repository: DocumentRepository | None = None


def get_repository() -> DocumentRepository:
    global _repository
    if _repository is not None:
        return _repository

    if settings.redis_url:
        try:
            from ai_layer.repositories.redis_repo import RedisDocumentRepository

            _repository = RedisDocumentRepository(settings.redis_url)
            logger.info("AI layer document repository: Redis")
            return _repository
        except Exception as exc:  # noqa: BLE001
            logger.warning("Redis unavailable (%s); falling back to in-memory store.", exc)

    _repository = InMemoryDocumentRepository()
    logger.info("AI layer document repository: in-memory")
    return _repository
