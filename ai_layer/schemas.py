from typing import Literal

from pydantic import BaseModel, Field, model_validator


class AIResponseMeta(BaseModel):
    source: Literal["openai", "fallback"]
    llm_error: str | None = None
    fallback_reason: str | None = None


class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    detected_type: str
    extracted_text_preview: str
    extracted_text: str = ""


class DocumentRestoreRequest(BaseModel):
    document_id: str
    filename: str
    detected_type: str = "text/plain"
    text: str = Field(min_length=1)


class DocumentRequest(BaseModel):
    document_id: str

    @model_validator(mode="after")
    def validate_document_id(self) -> "DocumentRequest":
        self.document_id = self.document_id.strip()
        if not self.document_id:
            raise ValueError("Provide a valid document_id.")
        return self


class SummaryRequest(DocumentRequest):
    pass


class SummaryResponse(AIResponseMeta):
    document_id: str
    summary: str


class KeyPointRecommendationRequest(DocumentRequest):
    pass


class KeyPointRecommendationResponse(AIResponseMeta):
    document_id: str
    key_points: list[str]


class TopicKeyPointsResponse(AIResponseMeta):
    document_id: str
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
    document_id: str
    chapters: list[ChapterNotes]


class QuestionGenerationRequest(DocumentRequest):
    topic: str | None = None
    question_type: str = Field(default="objective", pattern="^(objective|subjective)$")
    difficulty: str = Field(default="easy", pattern="^(easy|medium|hard)$")
    count: int = Field(default=5, ge=1, le=20)


class Question(BaseModel):
    id: str
    prompt: str
    question_type: str
    options: list[str] = []
    answer: str
    difficulty: str
    topic: str


class QuestionGenerationResponse(AIResponseMeta):
    document_id: str
    questions: list[Question]


class AnswerSubmission(BaseModel):
    question_id: str
    user_answer: str


class TestReviewRequest(BaseModel):
    document_id: str
    answers: list[AnswerSubmission]
    questions: list[Question] | None = None


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


class TestReviewResponse(AIResponseMeta):
    source: Literal["openai", "fallback", "mixed"]
    document_id: str
    total_score: float = Field(ge=0, le=100)
    reviews: list[AnswerReview]
    weak_topics: list[WeakTopic]
    recommended_difficulty: str
    scoring_source: Literal["openai", "fallback", "mixed"] = "fallback"
    weak_topics_source: Literal["openai", "fallback"] = "fallback"


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=8000)


class DoubtRequest(DocumentRequest):
    question: str = Field(min_length=3, max_length=2000)
    history: list[ChatTurn] = []


class DoubtResponse(AIResponseMeta):
    document_id: str
    question: str
    answer: str
    history: list[ChatTurn] = []


class DoubtStartRequest(DocumentRequest):
    pass


class DoubtStartResponse(AIResponseMeta):
    document_id: str
    message: str


class ChapterInfo(BaseModel):
    chapter_id: str
    chapter_number: int
    title: str
    start_char: int
    end_char: int
    chunk_count: int


class DocumentChaptersResponse(BaseModel):
    document_id: str
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
    document_id: str
    total_chunks: int
    chunks: list[ChunkInfo]
