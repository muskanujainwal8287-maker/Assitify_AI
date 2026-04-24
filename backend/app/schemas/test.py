from pydantic import BaseModel, Field


class AnswerSubmission(BaseModel):
    question_id: str
    user_answer: str


class TestReviewRequest(BaseModel):
    document_id: str
    answers: list[AnswerSubmission]


class AnswerReview(BaseModel):
    question_id: str
    expected_answer: str
    user_answer: str
    is_correct: bool
    score: float
    explanation: str
    topic: str


class WeakTopic(BaseModel):
    topic: str
    accuracy: float
    suggestion: str


class TestReviewResponse(BaseModel):
    document_id: str
    total_score: float = Field(ge=0, le=100)
    reviews: list[AnswerReview]
    weak_topics: list[WeakTopic]
    recommended_difficulty: str
