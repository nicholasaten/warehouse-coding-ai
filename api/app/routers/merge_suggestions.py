import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import require_role
from app.db.session import get_db
from app.models.location import Location
from app.models.merge_suggestion import MergeSuggestion
from app.schemas.location import LocationRead
from app.schemas.merge_suggestion import MergeSuggestionRead
from app.services.merge_suggestion_service import approve_suggestion, reject_suggestion

router = APIRouter(prefix="/merge-suggestions", tags=["merge-suggestions"], dependencies=[Depends(require_role("admin"))])


@router.get("", response_model=list[MergeSuggestionRead])
def list_merge_suggestions(status: str = "pending", db: Session = Depends(get_db)) -> list[MergeSuggestion]:
    return list(
        db.scalars(
            select(MergeSuggestion).where(MergeSuggestion.status == status).order_by(MergeSuggestion.created_at)
        ).all()
    )


@router.post("/{suggestion_id}/approve", response_model=MergeSuggestionRead)
def approve(suggestion_id: uuid.UUID, db: Session = Depends(get_db)) -> MergeSuggestion:
    """Confirms the raw row is the same real place as the suggested
    existing location -- no new Location is created."""
    return approve_suggestion(db, suggestion_id)


@router.post("/{suggestion_id}/reject", response_model=LocationRead)
def reject(suggestion_id: uuid.UUID, db: Session = Depends(get_db)) -> Location:
    """The admin says this is genuinely a different place -- creates it as
    a real new Location and returns it."""
    return reject_suggestion(db, suggestion_id)
