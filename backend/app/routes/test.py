from fastapi import APIRouter, HTTPException

from app.schemas.test import TestReviewRequest, TestReviewResponse
from app.services.storage import store
from ai_layer.evaluation_service import EvaluationService

router = APIRouter()


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
