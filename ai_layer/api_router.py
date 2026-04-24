import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from ai_layer.config import settings
from ai_layer.schemas import DocumentUploadResponse
from ai_layer.schemas import (
    QuestionGenerationRequest,
    QuestionGenerationResponse,
    SummaryRequest,
    SummaryResponse,
)
from ai_layer.schemas import TestReviewRequest, TestReviewResponse
from ai_layer.ai_service import AIService
from ai_layer.evaluation_service import EvaluationService
from ai_layer.parser_service import ParserService
from ai_layer.storage import StoredDocument, store

router = APIRouter()


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
    return DocumentUploadResponse(
        document_id=document_id,
        filename=file.filename,
        detected_type=detected_type,
        extracted_text_preview=parsed_text[:500],
    )


@router.post("/summary", response_model=SummaryResponse)
def generate_summary(payload: SummaryRequest) -> SummaryResponse:
    document = store.documents.get(payload.document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")

    summary, key_points = AIService.summarize(document.text, payload.mode)
    return SummaryResponse(document_id=payload.document_id, summary=summary, key_points=key_points)


@router.post("/questions", response_model=QuestionGenerationResponse)
def generate_questions(payload: QuestionGenerationRequest) -> QuestionGenerationResponse:
    document = store.documents.get(payload.document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")

    questions = AIService.generate_questions(
        text=document.text,
        question_type=payload.question_type,
        difficulty=payload.difficulty,
        count=payload.count,
        topic=payload.topic,
    )
    store.questions_by_document[payload.document_id] = questions
    return QuestionGenerationResponse(document_id=payload.document_id, questions=questions)


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
