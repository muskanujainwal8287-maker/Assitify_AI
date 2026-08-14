from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
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
    DoubtSessionDetailResponse,
    DoubtSessionListResponse,
    KeyPointsResponse,
    NotesResponse,
    QuestionGenerationRequest,
    QuestionGenerationResponse,
    SummaryResponse,
    TestReviewRequest,
    TestReviewResponse,
    TopicKeyPointsResponse,
)
from backend.app.services import document_service

router = APIRouter(prefix="/api/documents", tags=["documents"])


async def _read_optional_upload(
    file: UploadFile | None,
) -> tuple[bytes | None, str | None, str | None]:
    """Swagger sends an empty file part when nothing is chosen; ignore that."""
    if file is None:
        return None, None, None
    filename = (file.filename or "").strip() or None
    content = await file.read()
    if not content:
        if filename:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")
        return None, None, None
    return content, filename or "uploaded_file", file.content_type


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: Annotated[
        UploadFile | None,
        File(description="Document file (PDF, DOCX, TXT, or image)."),
    ] = None,
    text: Annotated[
        str | None,
        Form(description="Plain text to store/append (optional)."),
    ] = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DocumentUploadResponse:
    content, filename, content_type = await _read_optional_upload(file)

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


@router.get("/{document_id}/topic-keypoints", response_model=TopicKeyPointsResponse)
def get_topic_keypoints(
    document_id: UUID,
    topic: str = Query(..., min_length=2, max_length=255, description="Required topic name."),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TopicKeyPointsResponse:
    return document_service.get_topic_keypoints(db, document_id, topic=topic, user=user)


@router.get("/{document_id}/notes", response_model=NotesResponse)
def get_notes(
    document_id: UUID,
    chapter_id: str = Query(
        ...,
        description="Required. Use chapter_id from GET /api/documents/{document_id}/chapters, or chapter_number (1, 2, 3).",
    ),
    topic: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> NotesResponse:
    return document_service.get_notes(
        db,
        document_id,
        chapter_id=chapter_id,
        topic=topic,
        user=user,
    )


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
    return document_service.resolve_doubt(
        db,
        document_id,
        payload.question,
        user,
        session_id=payload.session_id,
    )


@router.post("/{document_id}/doubt/sessions", response_model=DoubtSessionDetailResponse)
def create_doubt_session(
    document_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DoubtSessionDetailResponse:
    return document_service.create_doubt_session(db, document_id, user)


@router.get("/{document_id}/doubt/sessions", response_model=DoubtSessionListResponse)
def list_doubt_sessions(
    document_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DoubtSessionListResponse:
    return document_service.list_doubt_sessions(db, document_id, user)


@router.get("/{document_id}/doubt/sessions/{session_id}", response_model=DoubtSessionDetailResponse)
def get_doubt_session(
    document_id: UUID,
    session_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DoubtSessionDetailResponse:
    return document_service.get_doubt_session(db, document_id, session_id, user)


@router.delete("/{document_id}/doubt/sessions/{session_id}")
def delete_doubt_session(
    document_id: UUID,
    session_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, str]:
    return document_service.delete_doubt_session(db, document_id, session_id, user)


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


attempts_router = APIRouter(prefix="/api/attempts", tags=["documents"])


@attempts_router.get("/{attempt_id}", response_model=AttemptDetailResponse)
def get_attempt_by_id(
    attempt_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AttemptDetailResponse:
    return document_service.get_attempt_by_id(db, attempt_id, user)
