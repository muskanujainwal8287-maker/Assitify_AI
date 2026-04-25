import re
import uuid

from ai_layer.storage import StoredChapter, StoredChunk, StoredDocument


class IngestionService:
    # Detect chapter-like headings for segmentation, e.g.:
    # - "Chapter 1", "Unit IV", "Part 3", "Section 2: ..."
    # - numbered headings like "1. Introduction" or "2) Basics"

    CHAPTER_HEADING_PATTERN = re.compile(
        r"(?im)^\s*((chapter|unit|part|section)\s+([0-9ivxlcdm]+)[\s:.\-]*(.*)|[0-9]+[.)]\s+[^\n]{3,})\s*$"
    )

    @staticmethod
    def ingest_document(document: StoredDocument, chunk_size: int = 1200, overlap: int = 200) -> StoredDocument:
        text = document.text.strip()
        if not text:
            document.chapters = []
            document.chunks = []
            return document

        chapters = IngestionService._split_into_chapters(text)
        chunks = IngestionService._build_chunks(
            text=text, document_id=document.id, chapters=chapters, chunk_size=chunk_size, overlap=overlap
        )
        document.chapters = chapters
        document.chunks = chunks
        return document

    @staticmethod
    def _split_into_chapters(text: str) -> list[StoredChapter]:
        matches = list(IngestionService.CHAPTER_HEADING_PATTERN.finditer(text))
        if not matches:
            return [
                StoredChapter(
                    id=str(uuid.uuid4()),
                    title="Full Document",
                    chapter_number=1,
                    start_char=0,
                    end_char=len(text),
                )
            ]

        chapters: list[StoredChapter] = []
        for index, match in enumerate(matches):
            start_char = match.start()
            end_char = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            heading = match.group(1).strip()
            chapter_number = index + 1
            title = heading if heading else f"Chapter {chapter_number}"
            chapters.append(
                StoredChapter(
                    id=str(uuid.uuid4()),
                    title=title[:150],
                    chapter_number=chapter_number,
                    start_char=start_char,
                    end_char=end_char,
                )
            )
        return chapters

    @staticmethod
    def _build_chunks(
        text: str, document_id: str, chapters: list[StoredChapter], chunk_size: int = 1200, overlap: int = 200
    ) -> list[StoredChunk]:
        chunks: list[StoredChunk] = []
        if chunk_size <= overlap:
            overlap = max(0, chunk_size // 4)
        step = max(1, chunk_size - overlap)

        for chapter in chapters:
            chunk_index = 0
            chapter_cursor = chapter.start_char
            while chapter_cursor < chapter.end_char:
                chunk_end = min(chapter_cursor + chunk_size, chapter.end_char)
                chunks.append(
                    StoredChunk(
                        id=str(uuid.uuid4()),
                        document_id=document_id,
                        chapter_id=chapter.id,
                        chapter_title=chapter.title,
                        chunk_index=chunk_index,
                        text=text[chapter_cursor:chunk_end],
                        start_char=chapter_cursor,
                        end_char=chunk_end,
                    )
                )
                chapter_cursor += step
                chunk_index += 1
                if chunk_end >= chapter.end_char:
                    break
        return chunks
