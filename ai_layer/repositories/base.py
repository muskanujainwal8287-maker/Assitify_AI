from typing import Protocol

from ai_layer.schemas import Question
from ai_layer.storage import StoredDocument


class DocumentRepository(Protocol):
    def save_document(self, document: StoredDocument) -> None: ...

    def get_document(self, document_id: str) -> StoredDocument | None: ...

    def save_questions(self, document_id: str, questions: list[Question]) -> None: ...

    def get_questions(self, document_id: str) -> list[Question]: ...
