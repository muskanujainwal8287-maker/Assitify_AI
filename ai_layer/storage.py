from collections import defaultdict
from dataclasses import dataclass, field

from ai_layer.schemas import Question


@dataclass
class StoredDocument:
    id: str
    filename: str
    detected_type: str
    text: str


@dataclass
class DocumentStore:
    documents: dict[str, StoredDocument] = field(default_factory=dict)
    questions_by_document: dict[str, list[Question]] = field(default_factory=lambda: defaultdict(list))


store = DocumentStore()
