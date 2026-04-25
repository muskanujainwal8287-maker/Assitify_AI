import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from ai_layer.config import settings
from ai_layer.schemas import DocumentUploadResponse
from ai_layer.schemas import (
    ChunkInfo,
    DocumentChaptersResponse,
    DocumentChunksResponse,
    DoubtRequest,
    DoubtResponse,
    ChapterInfo,
    KeyPointRecommendationRequest,
    KeyPointRecommendationResponse,
    QuestionGenerationRequest,
    QuestionGenerationResponse,
    SummaryRequest,
    SummaryResponse,
)
from ai_layer.schemas import TestReviewRequest, TestReviewResponse
from ai_layer.ai_service import AIService
from ai_layer.evaluation_service import EvaluationService
from ai_layer.ingestion_service import IngestionService
from ai_layer.parser_service import ParserService
from ai_layer.storage import StoredDocument, store

router = APIRouter()


def _resolve_document(document_id: str | None, text: str | None) -> StoredDocument:
    if text and text.strip():
        new_document_id = str(uuid.uuid4())
        document = StoredDocument(
            id=new_document_id,
            filename="pasted_text.txt",
            detected_type="text/plain",
            text=text.strip(),
        )
        IngestionService.ingest_document(document)
        store.documents[new_document_id] = document
        return document

    if document_id:
        document = store.documents.get(document_id)
        if document:
            return document

    raise HTTPException(status_code=404, detail="Document not found. Provide a valid document_id or text.")


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...)) -> DocumentUploadResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required.")

    upload_directory = Path(settings.upload_dir)
    upload_directory.mkdir(parents=True, exist_ok=True)
    document_id = str(uuid.uuid4())
    file_path = upload_directory / f"{document_id}_{file.filename}"

    content = await file.read()
    file_path.write_bytes(content)

    parsed_text, detected_type = ParserService.parse(file_path=file_path, content_type=file.content_type or "")
    if not parsed_text:
        raise HTTPException(status_code=422, detail="Could not extract text from the uploaded file.")

    store.documents[document_id] = StoredDocument(
        id=document_id, filename=file.filename, detected_type=detected_type, text=parsed_text
    )
    IngestionService.ingest_document(store.documents[document_id])
    return DocumentUploadResponse(
        document_id=document_id,
        filename=file.filename,
        detected_type=detected_type,
        extracted_text_preview=parsed_text[:500],
    )


@router.post("/summary", response_model=SummaryResponse)
def generate_summary(payload: SummaryRequest) -> SummaryResponse:
    document = _resolve_document(payload.document_id, payload.text)
    summary = AIService.summarize(document.text, payload.mode)
    return SummaryResponse(document_id=document.id, summary=summary)


@router.post("/keypoints", response_model=KeyPointRecommendationResponse)
def generate_keypoints(payload: KeyPointRecommendationRequest) -> KeyPointRecommendationResponse:
    document = _resolve_document(payload.document_id, payload.text)
    key_points = AIService.recommend_key_points(document.text, payload.count)
    return KeyPointRecommendationResponse(document_id=document.id, key_points=key_points)


@router.post("/questions", response_model=QuestionGenerationResponse)
def generate_questions(payload: QuestionGenerationRequest) -> QuestionGenerationResponse:
    document = _resolve_document(payload.document_id, payload.text)
    questions = AIService.generate_questions(
        text=document.text,
        question_type=payload.question_type,
        difficulty=payload.difficulty,
        count=payload.count,
        topic=payload.topic,
    )
    store.questions_by_document[document.id] = questions
    return QuestionGenerationResponse(document_id=document.id, questions=questions)


@router.post("/review", response_model=TestReviewResponse)
def review_test(payload: TestReviewRequest) -> TestReviewResponse:
    questions = store.questions_by_document.get(payload.document_id)
    if not questions:
        raise HTTPException(status_code=404, detail="No generated questions found for this document.")

    expected = {item.id: {"answer": item.answer, "topic": item.topic} for item in questions}
    answers = {item.question_id: item.user_answer for item in payload.answers}
    reviews, total_score, weak_topics, recommended_difficulty = EvaluationService.review_answers(answers, expected)

    return TestReviewResponse(
        document_id=payload.document_id,
        total_score=total_score,
        reviews=reviews,
        weak_topics=weak_topics,
        recommended_difficulty=recommended_difficulty,
    )


@router.post("/doubt", response_model=DoubtResponse)
def resolve_doubt(payload: DoubtRequest) -> DoubtResponse:
    document = _resolve_document(payload.document_id, payload.text)
    answer = AIService.answer_doubt(document.text, payload.question)
    return DoubtResponse(document_id=document.id, question=payload.question, answer=answer)


@router.get("/documents/{document_id}/chapters", response_model=DocumentChaptersResponse)
def get_document_chapters(document_id: str) -> DocumentChaptersResponse:
    document = store.documents.get(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")

    if not document.chapters:
        IngestionService.ingest_document(document)

    chapter_chunk_counts: dict[str, int] = {}
    for chunk in document.chunks:
        chapter_chunk_counts[chunk.chapter_id] = chapter_chunk_counts.get(chunk.chapter_id, 0) + 1

    chapters = [
        ChapterInfo(
            chapter_id=chapter.id,
            chapter_number=chapter.chapter_number,
            title=chapter.title,
            start_char=chapter.start_char,
            end_char=chapter.end_char,
            chunk_count=chapter_chunk_counts.get(chapter.id, 0),
        )
        for chapter in document.chapters
    ]
    return DocumentChaptersResponse(document_id=document.id, total_chapters=len(chapters), chapters=chapters)


@router.get("/documents/{document_id}/chunks", response_model=DocumentChunksResponse)
def get_document_chunks(
    document_id: str, chapter_id: str | None = Query(default=None), limit: int = Query(default=50, ge=1, le=200)
) -> DocumentChunksResponse:
    document = store.documents.get(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")

    if not document.chunks:
        IngestionService.ingest_document(document)

    filtered_chunks = document.chunks
    if chapter_id:
        filtered_chunks = [chunk for chunk in filtered_chunks if chunk.chapter_id == chapter_id]

    chunks = [
        ChunkInfo(
            chunk_id=chunk.id,
            chapter_id=chunk.chapter_id,
            chapter_title=chunk.chapter_title,
            chunk_index=chunk.chunk_index,
            start_char=chunk.start_char,
            end_char=chunk.end_char,
            text_preview=chunk.text[:250],
        )
        for chunk in filtered_chunks[:limit]
    ]
    return DocumentChunksResponse(document_id=document.id, total_chunks=len(filtered_chunks), chunks=chunks)
