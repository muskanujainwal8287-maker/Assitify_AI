from pydantic import BaseModel, Field


class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    detected_type: str
    extracted_text_preview: str


class SummaryRequest(BaseModel):
    document_id: str
    mode: str = Field(default="standard", pattern="^(short|standard|detailed)$")


class SummaryResponse(BaseModel):
    document_id: str
    summary: str
    key_points: list[str]


class QuestionGenerationRequest(BaseModel):
    document_id: str
    topic: str | None = None
    question_type: str = Field(default="objective", pattern="^(objective|subjective)$")
    difficulty: str = Field(default="medium", pattern="^(easy|medium|hard)$")
    count: int = Field(default=5, ge=1, le=20)


class Question(BaseModel):
    id: str
    prompt: str
    question_type: str
    options: list[str] = []
    answer: str
    difficulty: str
    topic: str


class QuestionGenerationResponse(BaseModel):
    document_id: str
    questions: list[Question]


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


class DoubtRequest(BaseModel):
    document_id: str
    question: str = Field(min_length=3, max_length=2000)


class DoubtResponse(BaseModel):
    document_id: str
    question: str
    answer: str
