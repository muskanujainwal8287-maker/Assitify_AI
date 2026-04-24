from fastapi import APIRouter, HTTPException

from app.schemas.generate import (
    QuestionGenerationRequest,
    QuestionGenerationResponse,
    SummaryRequest,
    SummaryResponse,
)
from app.services.storage import store
from ai_layer.ai_service import AIService

router = APIRouter()


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
