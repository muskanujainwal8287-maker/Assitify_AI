from ai_layer.repositories.base import DocumentRepository
from ai_layer.schemas import Question
from ai_layer.storage import StoredDocument, store


class InMemoryDocumentRepository(DocumentRepository):
    def save_document(self, document: StoredDocument) -> None:
        store.documents[document.id] = document

    def get_document(self, document_id: str) -> StoredDocument | None:
        return store.documents.get(document_id)

    def save_questions(self, document_id: str, questions: list[Question]) -> None:
        store.questions_by_document[document_id] = questions

    def get_questions(self, document_id: str) -> list[Question]:
        return store.questions_by_document.get(document_id, [])
