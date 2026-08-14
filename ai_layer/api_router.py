import uuid
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile

from ai_layer.ai_service import AIService
from ai_layer.evaluation_service import EvaluationService
from ai_layer.ingestion_service import IngestionService
from ai_layer.parser_service import ParserService
from ai_layer.repositories.provider import get_repository
from ai_layer.schemas import (
    ChunkInfo,
    ChapterInfo,
    DocumentChaptersResponse,
    DocumentChunksResponse,
    DocumentRestoreRequest,
    DocumentUploadResponse,
    DoubtRequest,
    DoubtResponse,
    DoubtStartRequest,
    DoubtStartResponse,
    KeyPointRecommendationResponse,
    NotesResponse,
    QuestionGenerationRequest,
    QuestionGenerationResponse,
    SummaryResponse,
    TopicKeyPointsResponse,
)
from ai_layer.schemas import TestReviewRequest, TestReviewResponse
from ai_layer.llm_result import LLMResult
from ai_layer.storage import StoredDocument

router = APIRouter()
repo = get_repository()


def _meta_from_result(result: LLMResult) -> dict[str, str | None]:
    return {
        "source": result.source,
        "llm_error": result.error,
        "fallback_reason": result.fallback_reason,
    }


def _resolve_document(document_id: str) -> StoredDocument:
    document = repo.get_document(document_id)
    if document:
        return document

    raise HTTPException(status_code=404, detail="Document not found. Provide a valid document_id.")


def _find_chapter(document: StoredDocument, chapter_ref: str):
    ref = chapter_ref.strip()
    if not ref:
        return None
    for chapter in document.chapters:
        if chapter.id == ref:
            return chapter
    if ref.isdigit():
        number = int(ref)
        for chapter in document.chapters:
            if chapter.chapter_number == number:
                return chapter
    ref_l = ref.lower()
    matches = [chapter for chapter in document.chapters if chapter.title.lower() == ref_l]
    if len(matches) == 1:
        return matches[0]
    return None


async def _read_optional_upload(
    file: UploadFile | None,
) -> tuple[bytes | None, str | None, str | None]:
    if file is None:
        return None, None, None
    filename = (file.filename or "").strip() or None
    content = await file.read()
    if not content:
        if filename:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")
        return None, None, None
    return content, filename or "uploaded_file", file.content_type


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
)
async def upload_document(
    file: Annotated[
        UploadFile | None,
        File(description="Document file to parse (optional)."),
    ] = None,
    text: Annotated[
        str | None,
        Form(description="Plain text to store/append (optional)."),
    ] = None,
) -> DocumentUploadResponse:
    content, filename, content_type = await _read_optional_upload(file)
    has_file = content is not None
    cleaned_text = (text or "").strip()
    has_text = bool(cleaned_text)
    if not has_file and not has_text:
        raise HTTPException(status_code=400, detail="Provide file, text, or both.")

    if not has_file:
        document_id = str(uuid.uuid4())
        document = StoredDocument(
            id=document_id,
            filename="pasted_text.txt",
            detected_type="text/plain",
            text=cleaned_text,
        )
        IngestionService.ingest_document(document)
        repo.save_document(document)
        return DocumentUploadResponse(
            document_id=document_id,
            filename="pasted_text.txt",
            detected_type="text/plain",
            extracted_text_preview=cleaned_text[:500],
            extracted_text=cleaned_text,
        )

    document_id = str(uuid.uuid4())
    parsed_text, detected_type = ParserService.parse_bytes(
        content=content or b"",
        filename=filename or "uploaded_file",
        content_type=content_type or "",
    )
    combined_text = parsed_text.strip() if parsed_text else ""
    if has_text and combined_text:
        combined_text = f"{combined_text}\n\n{cleaned_text}"
    elif has_text:
        combined_text = cleaned_text

    if not combined_text:
        raise HTTPException(status_code=422, detail="Could not extract usable content from file/text input.")

    stored_type = f"{detected_type}+text" if has_text else detected_type

    document = StoredDocument(
        id=document_id,
        filename=filename or "uploaded_file",
        detected_type=stored_type,
        text=combined_text,
    )
    IngestionService.ingest_document(document)
    repo.save_document(document)
    return DocumentUploadResponse(
        document_id=document_id,
        filename=filename or "uploaded_file",
        detected_type=stored_type,
        extracted_text_preview=combined_text[:500],
        extracted_text=combined_text,
    )


@router.post("/documents/restore", response_model=DocumentUploadResponse)
def restore_document(payload: DocumentRestoreRequest) -> DocumentUploadResponse:
    document_id = payload.document_id.strip()
    text = payload.text.strip()
    if not document_id or not text:
        raise HTTPException(status_code=400, detail="document_id and text are required.")

    existing = repo.get_document(document_id)
    if existing and existing.text.strip() == text:
        if not existing.chapters:
            IngestionService.ingest_document(existing)
            repo.save_document(existing)
        return DocumentUploadResponse(
            document_id=existing.id,
            filename=existing.filename,
            detected_type=existing.detected_type,
            extracted_text_preview=existing.text[:500],
            extracted_text=existing.text,
        )

    document = StoredDocument(
        id=document_id,
        filename=payload.filename.strip() or "restored.txt",
        detected_type=payload.detected_type or "text/plain",
        text=text,
    )
    IngestionService.ingest_document(document)
    repo.save_document(document)
    return DocumentUploadResponse(
        document_id=document.id,
        filename=document.filename,
        detected_type=document.detected_type,
        extracted_text_preview=text[:500],
        extracted_text=text,
    )


@router.delete("/documents/{document_id}")
def delete_document(document_id: str) -> dict[str, str]:
    document = repo.get_document(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")
    repo.delete_document(document_id)
    from ai_layer.vector_store import delete_document_vectors

    delete_document_vectors(document_id)
    return {"status": "deleted", "document_id": document_id}


@router.get("/summary", response_model=SummaryResponse)
def generate_summary(document_id: str = Query(...)) -> SummaryResponse:
    document = _resolve_document(document_id)
    result = AIService.summarize(document.text)
    return SummaryResponse(document_id=document.id, summary=result.data, **_meta_from_result(result))


@router.get("/keypoints", response_model=KeyPointRecommendationResponse)
def generate_keypoints(document_id: str = Query(...)) -> KeyPointRecommendationResponse:
    document = _resolve_document(document_id)
    result = AIService.recommend_key_points(document.text)
    return KeyPointRecommendationResponse(document_id=document.id, key_points=result.data, **_meta_from_result(result))


@router.get("/topic-keypoints", response_model=TopicKeyPointsResponse)
def generate_topic_keypoints(
    document_id: str = Query(...),
    topic: str = Query(..., min_length=2, max_length=255, description="Required topic name."),
) -> TopicKeyPointsResponse:
    document = _resolve_document(document_id)
    chosen_topic = topic.strip()
    result = AIService.recommend_topic_key_points(document.text, chosen_topic)
    return TopicKeyPointsResponse(
        document_id=document.id,
        topic=chosen_topic,
        key_points=result.data,
        **_meta_from_result(result),
    )


@router.get("/notes", response_model=NotesResponse)
def generate_notes(
    document_id: str = Query(...),
    chapter_id: str = Query(
        ...,
        description="Required. chapter_id from GET /chapters, or chapter_number like 1.",
    ),
    topic: str | None = Query(default=None),
) -> NotesResponse:
    document = _resolve_document(document_id)
    if not document.chapters:
        IngestionService.ingest_document(document)
        repo.save_document(document)

    chapter = _find_chapter(document, chapter_id.strip())
    if not chapter:
        raise HTTPException(
            status_code=404,
            detail="Chapter not found. List chapters with GET /documents/{document_id}/chapters, then pass chapter_id or chapter_number.",
        )

    topic_filter = topic.strip() if topic else ""
    sections = [
        {
            "title": chapter.title,
            "text": document.text[chapter.start_char : chapter.end_char],
            "chapter_id": chapter.id,
            "chapter_number": chapter.chapter_number,
        }
    ]

    result = AIService.generate_notes(sections, topic=topic_filter or None)
    return NotesResponse(
        document_id=document.id,
        chapters=result.data,
        **_meta_from_result(result),
    )


@router.post("/questions", response_model=QuestionGenerationResponse)
def generate_questions(payload: QuestionGenerationRequest) -> QuestionGenerationResponse:
    document = _resolve_document(payload.document_id)
    result = AIService.generate_questions(
        text=document.text,
        question_type=payload.question_type,
        difficulty=payload.difficulty,
        count=payload.count,
        topic=payload.topic,
    )
    repo.save_questions(document.id, result.data)
    return QuestionGenerationResponse(document_id=document.id, questions=result.data, **_meta_from_result(result))


@router.post("/review", response_model=TestReviewResponse)
def review_test(payload: TestReviewRequest) -> TestReviewResponse:
    questions = payload.questions or repo.get_questions(payload.document_id)
    if not questions:
        raise HTTPException(status_code=404, detail="No generated questions found for this document.")

    if payload.questions:
        repo.save_questions(payload.document_id, payload.questions)

    expected = {item.id: {"answer": item.answer, "topic": item.topic} for item in questions}
    answers = {item.question_id: item.user_answer for item in payload.answers}
    evaluation = EvaluationService.review_answers(answers, expected)

    return TestReviewResponse(
        document_id=payload.document_id,
        total_score=evaluation.total_score,
        reviews=evaluation.reviews,
        weak_topics=evaluation.weak_topics,
        recommended_difficulty=evaluation.recommended_difficulty,
        source=evaluation.source,
        scoring_source=evaluation.scoring_source,
        weak_topics_source=evaluation.weak_topics_source,
        llm_error=evaluation.llm_error,
        fallback_reason=evaluation.fallback_reason,
    )


@router.post("/doubt", response_model=DoubtResponse)
def resolve_doubt(payload: DoubtRequest) -> DoubtResponse:
    document = _resolve_document(payload.document_id)
    from ai_layer.vector_pipeline import retrieve_context

    history = [{"role": item.role, "content": item.content} for item in payload.history]
    search_query = payload.question
    if history and len(payload.question.split()) <= 8:
        prior_user = next((item["content"] for item in reversed(history) if item["role"] == "user"), "")
        if prior_user:
            search_query = f"{prior_user}\n{payload.question}"

    context = retrieve_context(document.id, search_query, document.text)
    result = AIService.answer_doubt(context, payload.question, history=history)
    return DoubtResponse(
        document_id=document.id,
        question=payload.question,
        answer=result.data,
        history=payload.history,
        **_meta_from_result(result),
    )


@router.post("/doubt/start", response_model=DoubtStartResponse)
def start_doubt_session(payload: DoubtStartRequest) -> DoubtStartResponse:
    document = _resolve_document(payload.document_id)
    from ai_layer.vector_pipeline import retrieve_context

    context = retrieve_context(document.id, "main concepts for a first tutoring question", document.text)
    result = AIService.start_doubt_session(context)
    return DoubtStartResponse(
        document_id=document.id,
        message=result.data,
        **_meta_from_result(result),
    )


@router.get("/documents/{document_id}/chapters", response_model=DocumentChaptersResponse)
def get_document_chapters(document_id: str) -> DocumentChaptersResponse:
    document = _resolve_document(document_id)

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
    document = _resolve_document(document_id)

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
