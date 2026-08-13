from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.core.security import get_current_user
from backend.app.db.models import User
from backend.app.db.session import get_db
from backend.app.schemas import AttemptDetailResponse
from backend.app.services import document_service

router = APIRouter(prefix="/api/attempts", tags=["attempts"])


@router.get("/{attempt_id}", response_model=AttemptDetailResponse)
def get_attempt(
    attempt_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AttemptDetailResponse:
    return document_service.get_attempt_by_id(db, attempt_id, user)
