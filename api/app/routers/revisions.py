import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, get_current_user, require_role
from app.db.session import get_db
from app.models.revision import Revision
from app.schemas.revision import RevisionCreate, RevisionEditApprove, RevisionRead, RevisionReject
from app.services.revision_service import (
    get_entity,
    approve_revision,
    edit_and_approve_revision,
    entity_site_id,
    list_revisions,
    reject_revision,
    submit_revision,
)

router = APIRouter(prefix="/revisions", tags=["revisions"], dependencies=[Depends(get_current_user)])


@router.post("", response_model=RevisionRead, status_code=201, dependencies=[Depends(require_role("pic"))])
def submit_revision_endpoint(
    payload: RevisionCreate, current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)
) -> Revision:
    """PIC only -- a PIC may only propose changes to a record in their own
    Hospital Unit, even though `entity_id` alone doesn't reveal that until
    the entity is loaded, so the scope check happens here rather than in
    the service."""
    entity = get_entity(db, payload.entity_type, payload.entity_id)
    if entity_site_id(db, payload.entity_type, entity) != current_user.site_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not permitted")
    return submit_revision(
        db, current_user.id, payload.entity_type, payload.entity_id, payload.proposed_value, payload.comment
    )


@router.get("", response_model=list[RevisionRead])
def list_revisions_endpoint(
    status: str | None = None,
    entity_type: str | None = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Revision]:
    """Admin sees the full Review Queue (optionally filtered); a PIC only
    ever sees their own submitted revisions and their status -- never
    other PICs' requests."""
    submitted_by = current_user.id if current_user.role == "pic" else None
    return list_revisions(db, status_filter=status, entity_type=entity_type, submitted_by=submitted_by)


@router.post("/{revision_id}/approve", response_model=RevisionRead, dependencies=[Depends(require_role("admin"))])
def approve_revision_endpoint(
    revision_id: uuid.UUID, current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)
) -> Revision:
    return approve_revision(db, revision_id, current_user.id)


@router.post("/{revision_id}/reject", response_model=RevisionRead, dependencies=[Depends(require_role("admin"))])
def reject_revision_endpoint(
    revision_id: uuid.UUID,
    payload: RevisionReject,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Revision:
    return reject_revision(db, revision_id, current_user.id, payload.reason)


@router.post(
    "/{revision_id}/edit-approve", response_model=RevisionRead, dependencies=[Depends(require_role("admin"))]
)
def edit_and_approve_revision_endpoint(
    revision_id: uuid.UUID,
    payload: RevisionEditApprove,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Revision:
    """Admin modifies the PIC's proposal before applying it -- see
    revision_service.edit_and_approve_revision docstring."""
    return edit_and_approve_revision(db, revision_id, current_user.id, payload.final_value)
