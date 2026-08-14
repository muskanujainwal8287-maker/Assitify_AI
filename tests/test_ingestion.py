from unittest.mock import patch

from ai_layer.ingestion_service import IngestionService
from ai_layer.storage import StoredDocument


SAMPLE_TEXT = """Chapter 1 Introduction
Photosynthesis converts light energy into chemical energy in plants.
It happens mainly in the leaves using chlorophyll.

Chapter 2 Cellular Respiration
Respiration releases energy from glucose.
Mitochondria play a central role in this process.
"""


def test_chapter_ids_are_stable_across_runs() -> None:
    doc_id = "11111111-1111-1111-1111-111111111111"
    first = IngestionService._split_into_chapters(SAMPLE_TEXT, doc_id)
    second = IngestionService._split_into_chapters(SAMPLE_TEXT, doc_id)
    assert len(first) >= 2
    assert [c.id for c in first] == [c.id for c in second]
    assert first[0].id == IngestionService._chapter_id(doc_id, 1)
    assert first[1].id == IngestionService._chapter_id(doc_id, 2)


def test_split_without_headings_makes_full_document_chapter() -> None:
    text = "Just a plain paragraph without any chapter markers at all."
    chapters = IngestionService._split_into_chapters(text, "doc-a")
    assert len(chapters) == 1
    assert chapters[0].title == "Full Document"
    assert chapters[0].start_char == 0
    assert chapters[0].end_char == len(text)


def test_build_chunks_keeps_chapter_bounds() -> None:
    doc_id = "doc-chunks"
    chapters = IngestionService._split_into_chapters(SAMPLE_TEXT, doc_id)
    chunks = IngestionService._build_chunks(
        SAMPLE_TEXT,
        document_id=doc_id,
        chapters=chapters,
        chunk_size=80,
        overlap=10,
    )
    assert chunks
    for chunk in chunks:
        chapter = next(c for c in chapters if c.id == chunk.chapter_id)
        assert chapter.start_char <= chunk.start_char < chunk.end_char <= chapter.end_char
        assert chunk.text == SAMPLE_TEXT[chunk.start_char : chunk.end_char]


def test_ingest_document_populates_chapters_and_chunks() -> None:
    document = StoredDocument(
        id="doc-ingest",
        filename="notes.txt",
        detected_type="text/plain",
        text=SAMPLE_TEXT,
    )
    with patch("ai_layer.vector_pipeline.index_document") as index_mock:
        result = IngestionService.ingest_document(document, chunk_size=100, overlap=20)
    assert len(result.chapters) >= 2
    assert result.chunks
    index_mock.assert_called_once_with(document)
