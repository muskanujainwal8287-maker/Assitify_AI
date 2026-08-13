from __future__ import annotations

import json
from typing import Any

from redis import Redis

from ai_layer.repositories.base import DocumentRepository
from ai_layer.schemas import Question
from ai_layer.storage import StoredChapter, StoredChunk, StoredDocument

_DOC_PREFIX = "assitify:doc:"
_QUESTIONS_PREFIX = "assitify:questions:"


def _document_to_dict(document: StoredDocument) -> dict[str, Any]:
    return {
        "id": document.id,
        "filename": document.filename,
        "detected_type": document.detected_type,
        "text": document.text,
        "chapters": [
            {
                "id": chapter.id,
                "title": chapter.title,
                "chapter_number": chapter.chapter_number,
                "start_char": chapter.start_char,
                "end_char": chapter.end_char,
            }
            for chapter in document.chapters
        ],
        "chunks": [
            {
                "id": chunk.id,
                "document_id": chunk.document_id,
                "chapter_id": chunk.chapter_id,
                "chapter_title": chunk.chapter_title,
                "chunk_index": chunk.chunk_index,
                "text": chunk.text,
                "start_char": chunk.start_char,
                "end_char": chunk.end_char,
            }
            for chunk in document.chunks
        ],
    }


def _document_from_dict(payload: dict[str, Any]) -> StoredDocument:
    return StoredDocument(
        id=payload["id"],
        filename=payload["filename"],
        detected_type=payload["detected_type"],
        text=payload["text"],
        chapters=[
            StoredChapter(
                id=item["id"],
                title=item["title"],
                chapter_number=item["chapter_number"],
                start_char=item["start_char"],
                end_char=item["end_char"],
            )
            for item in payload.get("chapters") or []
        ],
        chunks=[
            StoredChunk(
                id=item["id"],
                document_id=item["document_id"],
                chapter_id=item["chapter_id"],
                chapter_title=item["chapter_title"],
                chunk_index=item["chunk_index"],
                text=item["text"],
                start_char=item["start_char"],
                end_char=item["end_char"],
            )
            for item in payload.get("chunks") or []
        ],
    )


class RedisDocumentRepository(DocumentRepository):
    def __init__(self, redis_url: str) -> None:
        self._client = Redis.from_url(redis_url, decode_responses=True)
        self._client.ping()

    def save_document(self, document: StoredDocument) -> None:
        self._client.set(_DOC_PREFIX + document.id, json.dumps(_document_to_dict(document)))

    def get_document(self, document_id: str) -> StoredDocument | None:
        raw = self._client.get(_DOC_PREFIX + document_id)
        if not raw:
            return None
        return _document_from_dict(json.loads(raw))

    def save_questions(self, document_id: str, questions: list[Question]) -> None:
        payload = [question.model_dump() for question in questions]
        self._client.set(_QUESTIONS_PREFIX + document_id, json.dumps(payload))

    def get_questions(self, document_id: str) -> list[Question]:
        raw = self._client.get(_QUESTIONS_PREFIX + document_id)
        if not raw:
            return []
        return [Question.model_validate(item) for item in json.loads(raw)]

    def delete_document(self, document_id: str) -> None:
        self._client.delete(_DOC_PREFIX + document_id, _QUESTIONS_PREFIX + document_id)
