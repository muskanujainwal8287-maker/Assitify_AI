from ai_layer.repositories.base import DocumentRepository
from ai_layer.repositories.memory_repo import InMemoryDocumentRepository

_repository: DocumentRepository = InMemoryDocumentRepository()


def get_repository() -> DocumentRepository:
    return _repository
