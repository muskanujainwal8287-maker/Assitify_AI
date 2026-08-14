from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

def normalize_mobile_number(value: str) -> str:
    digits = "".join(ch for ch in value.strip() if ch.isdigit())
    if digits.startswith("91") and len(digits) == 12:
        digits = digits[2:]
    if len(digits) != 10 or not digits[0] in "6789":
        raise ValueError("Mobile number must be a valid 10-digit Indian number.")
    return digits


class AIResponseMeta(BaseModel):
    source: Literal["openai", "fallback", "mixed"] = "fallback"
    llm_error: str | None = None
    fallback_reason: str | None = None


class UserRegisterRequest(BaseModel):
    email: EmailStr
    mobile_number: str = Field(min_length=10, max_length=16)
    password: str = Field(min_length=6, max_length=128)
    full_name: str = Field(default="", max_length=255)

    @field_validator("mobile_number")
    @classmethod
    def validate_mobile_number(cls, value: str) -> str:
        return normalize_mobile_number(value)


class UserLoginRequest(BaseModel):
    email: EmailStr | None = None
    mobile_number: str | None = None
    password: str = Field(min_length=1, max_length=128)

    @field_validator("mobile_number")
    @classmethod
    def validate_login_mobile(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        return normalize_mobile_number(value)

    @model_validator(mode="after")
    def require_email_or_mobile(self) -> "UserLoginRequest":
        if not self.email and not self.mobile_number:
            raise ValueError("Provide email or mobile_number.")
        return self


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    mobile_number: str
    full_name: str
    created_at: datetime


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class DocumentUploadResponse(BaseModel):
    document_id: UUID
    filename: str
    detected_type: str
    extracted_text_preview: str


class DocumentListItem(BaseModel):
    document_id: UUID
    filename: str
    detected_type: str
    created_at: datetime
    question_count: int = 0


class DocumentListResponse(BaseModel):
    documents: list[DocumentListItem]
    total: int


class DocumentDetailResponse(BaseModel):
    document_id: UUID
    filename: str
    detected_type: str
    created_at: datetime
    text_preview: str
    text_length: int
    question_count: int = 0
    attempt_count: int = 0


class SummaryResponse(AIResponseMeta):
    document_id: UUID
    summary: str


class KeyPointsResponse(AIResponseMeta):
    document_id: UUID
    key_points: list[str]


class TopicKeyPointsResponse(AIResponseMeta):
    document_id: UUID
    topic: str
    key_points: list[str]


class TopicNotes(BaseModel):
    topic: str
    notes: list[str] = []


class ChapterNotes(BaseModel):
    title: str
    chapter_id: str | None = None
    chapter_number: int | None = None
    topics: list[TopicNotes] = []


class NotesResponse(AIResponseMeta):
    document_id: UUID
    chapters: list[ChapterNotes]


class QuestionOut(BaseModel):
    id: str
    prompt: str
    question_type: str
    options: list[str] = []
    answer: str
    difficulty: str
    topic: str


class QuestionGenerationRequest(BaseModel):
    topic: str | None = None
    question_type: str = Field(default="objective", pattern="^(objective|subjective)$")
    difficulty: str = Field(default="easy", pattern="^(easy|medium|hard)$")
    count: int = Field(default=5, ge=1, le=20)


class QuestionGenerationResponse(AIResponseMeta):
    document_id: UUID
    questions: list[QuestionOut]


class AnswerSubmission(BaseModel):
    question_id: str
    user_answer: str


class TestReviewRequest(BaseModel):
    answers: list[AnswerSubmission]


class AnswerReviewOut(BaseModel):
    question_id: str
    expected_answer: str
    user_answer: str
    is_correct: bool
    score: float
    explanation: str
    topic: str


class WeakTopicOut(BaseModel):
    topic: str
    accuracy: float
    suggestion: str


class TestReviewResponse(AIResponseMeta):
    document_id: UUID
    attempt_id: UUID
    total_score: float
    reviews: list[AnswerReviewOut]
    weak_topics: list[WeakTopicOut]
    recommended_difficulty: str
    scoring_source: Literal["openai", "fallback", "mixed"] = "fallback"
    weak_topics_source: Literal["openai", "fallback"] = "fallback"


class DoubtRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    session_id: UUID | None = None


class ChatMessageOut(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime


class DoubtResponse(AIResponseMeta):
    document_id: UUID
    session_id: UUID
    question: str
    answer: str
    messages: list[ChatMessageOut] = []


class DoubtSessionListItem(BaseModel):
    session_id: UUID
    document_id: UUID
    title: str
    message_count: int = 0
    created_at: datetime
    updated_at: datetime


class DoubtSessionListResponse(BaseModel):
    document_id: UUID
    sessions: list[DoubtSessionListItem]
    total: int


class DoubtSessionDetailResponse(BaseModel):
    session_id: UUID
    document_id: UUID
    title: str
    messages: list[ChatMessageOut]
    created_at: datetime
    updated_at: datetime


class ChapterInfo(BaseModel):
    chapter_id: str
    chapter_number: int
    title: str
    start_char: int
    end_char: int
    chunk_count: int


class DocumentChaptersResponse(BaseModel):
    document_id: UUID
    total_chapters: int
    chapters: list[ChapterInfo]


class ChunkInfo(BaseModel):
    chunk_id: str
    chapter_id: str
    chapter_title: str
    chunk_index: int
    start_char: int
    end_char: int
    text_preview: str


class DocumentChunksResponse(BaseModel):
    document_id: UUID
    total_chunks: int
    chunks: list[ChunkInfo]


class AttemptListItem(BaseModel):
    attempt_id: UUID
    document_id: UUID
    total_score: float
    recommended_difficulty: str
    source: str
    scoring_source: str
    weak_topics: list
    created_at: datetime
    answer_count: int = 0


class AttemptListResponse(BaseModel):
    document_id: UUID
    attempts: list[AttemptListItem]
    total: int


class AttemptDetailResponse(BaseModel):
    attempt_id: UUID
    document_id: UUID
    total_score: float
    recommended_difficulty: str
    source: str
    scoring_source: str
    weak_topics: list
    created_at: datetime
    reviews: list[AnswerReviewOut]
