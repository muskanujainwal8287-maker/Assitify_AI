
from pydantic import BaseModel, Field, model_validator


class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    detected_type: str
    extracted_text_preview: str


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


class SummaryResponse(BaseModel):
    document_id: str
    summary: str


class KeyPointRecommendationRequest(DocumentRequest):
    pass


class KeyPointRecommendationResponse(BaseModel):
    document_id: str
    key_points: list[str]


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


class DoubtRequest(DocumentRequest):
    question: str = Field(min_length=3, max_length=2000)


class DoubtResponse(BaseModel):
    document_id: str
    question: str
    answer: str


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
