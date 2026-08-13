from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy.orm import Session

from backend.app.core.security import get_current_user
from backend.app.db.models import User
from backend.app.db.session import get_db
from backend.app.schemas import (
    AttemptDetailResponse,
    AttemptListResponse,
    DocumentChaptersResponse,
    DocumentChunksResponse,
    DocumentDetailResponse,
    DocumentListResponse,
    DocumentUploadResponse,
    DoubtRequest,
    DoubtResponse,
    KeyPointsResponse,
    QuestionGenerationRequest,
    QuestionGenerationResponse,
    SummaryResponse,
    TestReviewRequest,
    TestReviewResponse,
)
from backend.app.services import document_service

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile | None = File(default=None),
    text: str | None = Form(
        default=None,
        description="Plain text to store/append (optional).",
        examples=[""],
    ),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DocumentUploadResponse:
    content: bytes | None = None
    filename: str | None = None
    content_type: str | None = None
    if file is not None and file.filename:
        content = await file.read()
        filename = file.filename
        content_type = file.content_type

    return document_service.upload_document(
        db,
        filename=filename,
        content=content,
        content_type=content_type,
        text=text,
        user=user,
    )


@router.get("", response_model=DocumentListResponse)
def list_documents(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DocumentListResponse:
    return document_service.list_documents(db, user)


@router.get("/{document_id}", response_model=DocumentDetailResponse)
def get_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DocumentDetailResponse:
    return document_service.get_document(db, document_id, user)


@router.delete("/{document_id}")
def delete_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, str]:
    return document_service.delete_document(db, document_id, user)


@router.get("/{document_id}/summary", response_model=SummaryResponse)
def get_summary(
    document_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SummaryResponse:
    return document_service.get_summary(db, document_id, user)


@router.get("/{document_id}/keypoints", response_model=KeyPointsResponse)
def get_keypoints(
    document_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> KeyPointsResponse:
    return document_service.get_keypoints(db, document_id, user)


@router.post("/{document_id}/questions", response_model=QuestionGenerationResponse)
def generate_questions(
    document_id: UUID,
    payload: QuestionGenerationRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> QuestionGenerationResponse:
    return document_service.generate_questions(db, document_id, payload, user)


@router.post("/{document_id}/review", response_model=TestReviewResponse)
def review_test(
    document_id: UUID,
    payload: TestReviewRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TestReviewResponse:
    return document_service.review_test(db, document_id, payload, user)


@router.post("/{document_id}/doubt", response_model=DoubtResponse)
def resolve_doubt(
    document_id: UUID,
    payload: DoubtRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DoubtResponse:
    return document_service.resolve_doubt(db, document_id, payload.question, user)


@router.get("/{document_id}/chapters", response_model=DocumentChaptersResponse)
def get_chapters(
    document_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DocumentChaptersResponse:
    return document_service.get_chapters(db, document_id, user)


@router.get("/{document_id}/chunks", response_model=DocumentChunksResponse)
def get_chunks(
    document_id: UUID,
    chapter_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DocumentChunksResponse:
    return document_service.get_chunks(
        db, document_id, chapter_id=chapter_id, limit=limit, user=user
    )


@router.get("/{document_id}/attempts", response_model=AttemptListResponse)
def list_attempts(
    document_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AttemptListResponse:
    return document_service.list_attempts(db, document_id, user)


@router.get("/{document_id}/attempts/{attempt_id}", response_model=AttemptDetailResponse)
def get_attempt(
    document_id: UUID,
    attempt_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AttemptDetailResponse:
    return document_service.get_attempt(db, document_id, attempt_id, user)
