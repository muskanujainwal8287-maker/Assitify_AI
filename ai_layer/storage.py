from collections import defaultdict
from dataclasses import dataclass, field

from ai_layer.schemas import Question


@dataclass
class StoredChapter:
    id: str
    title: str
    chapter_number: int
    start_char: int
    end_char: int


@dataclass
class StoredChunk:
    id: str
    document_id: str
    chapter_id: str
    chapter_title: str
    chunk_index: int
    text: str
    start_char: int
    end_char: int


@dataclass
class StoredDocument:
    id: str
    filename: str
    detected_type: str
    text: str
    chapters: list[StoredChapter] = field(default_factory=list)
    chunks: list[StoredChunk] = field(default_factory=list)


@dataclass
class DocumentStore:
    documents: dict[str, StoredDocument] = field(default_factory=dict)
    questions_by_document: dict[str, list[Question]] = field(default_factory=lambda: defaultdict(list))


store = DocumentStore()
