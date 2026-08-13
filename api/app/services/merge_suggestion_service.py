"""Deterministic string-similarity duplicate detection, not a model call --
fast, free, and exactly reproducible for the same input, which matters for
a suggestion someone will act on. Deliberately SUGGESTS ONLY: nothing here
ever creates or merges a Location on its own. Same approach and threshold
convention as the sibling WMS Readiness Tracker project's fuzzy email-match
feature, applied here to location descriptions instead of emails.
"""
import uuid
from datetime import datetime, timezone
from difflib import SequenceMatcher

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.location import Location
from app.models.merge_suggestion import MergeSuggestion
from app.services.location_service import create_location

# Below this similarity ratio, a suggestion does more harm than good --
# unrelated descriptions start looking like false matches. Same starting
# point as the sibling project's email-similarity threshold; can be tuned
# once more real near-duplicate examples are seen in practice.
SIMILARITY_THRESHOLD = 0.82


def find_similar_location(
    db: Session, warehouse_id: uuid.UUID, location_type_code: str, description: str
) -> tuple[Location | None, float]:
    """Scoped to the same (warehouse, location_type) as the exact-duplicate
    check -- a similarly-worded description in a totally different
    warehouse or category isn't a real duplicate candidate. Returns
    (None, 0.0) if nothing clears the threshold."""
    candidates = list(
        db.scalars(
            select(Location).where(
                Location.warehouse_id == warehouse_id, Location.location_type_code == location_type_code
            )
        ).all()
    )
    best: Location | None = None
    best_ratio = 0.0
    for candidate in candidates:
        ratio = SequenceMatcher(None, description.casefold(), candidate.description.casefold()).ratio()
        if ratio > best_ratio:
            best, best_ratio = candidate, ratio
    if best is not None and best_ratio >= SIMILARITY_THRESHOLD:
        return best, best_ratio
    return None, 0.0


def create_suggestion(
    db: Session,
    upload_batch_id: uuid.UUID | None,
    row_number: int | None,
    warehouse_id: uuid.UUID,
    location_type_code: str,
    raw_category_rack: str | None,
    raw_description: str,
    suggested_location: Location,
    similarity_score: float,
) -> MergeSuggestion:
    reasoning = (
        f"'{raw_description}' is {similarity_score:.0%} textually similar to the existing location "
        f"'{suggested_location.description}' ({suggested_location.generated_code}) in the same warehouse "
        f"and location type -- likely the same real place described differently, not a new one."
    )
    suggestion = MergeSuggestion(
        upload_batch_id=upload_batch_id,
        row_number=row_number,
        warehouse_id=warehouse_id,
        location_type_code=location_type_code,
        raw_category_rack=raw_category_rack,
        raw_description=raw_description,
        suggested_location_id=suggested_location.id,
        similarity_score=similarity_score,
        reasoning=reasoning,
    )
    db.add(suggestion)
    db.flush()
    return suggestion


def approve_suggestion(db: Session, suggestion_id: uuid.UUID) -> MergeSuggestion:
    """Confirms the raw row really is the same place as the suggested
    existing Location -- no new Location is created, the existing one
    already covers it."""
    suggestion = db.get(MergeSuggestion, suggestion_id)
    if suggestion is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Suggestion not found")
    if suggestion.status != "pending":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Suggestion already resolved")
    suggestion.status = "approved"
    suggestion.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(suggestion)
    return suggestion


def reject_suggestion(db: Session, suggestion_id: uuid.UUID) -> Location:
    """The admin says this is genuinely a different place -- creates it as
    a real new Location the normal way (through the same id_generator-backed
    service every other Location goes through), using the row's originally
    held raw description."""
    suggestion = db.get(MergeSuggestion, suggestion_id)
    if suggestion is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Suggestion not found")
    if suggestion.status != "pending":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Suggestion already resolved")

    location = create_location(
        db, suggestion.warehouse_id, suggestion.location_type_code, suggestion.raw_category_rack, suggestion.raw_description
    )
    suggestion.status = "rejected"
    suggestion.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(location)
    return location
