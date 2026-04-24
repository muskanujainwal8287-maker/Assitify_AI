from pydantic import BaseModel, Field


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
