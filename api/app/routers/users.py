from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import require_role
from app.core.security import hash_password
from app.db.session import get_db
from app.models.site import Site
from app.models.user import ROLE_VALUES, User
from app.schemas.user import UserCreate, UserRead

router = APIRouter(prefix="/users", tags=["users"], dependencies=[Depends(require_role("admin"))])


@router.get("", response_model=list[UserRead])
def list_users(db: Session = Depends(get_db)) -> list[User]:
    return list(db.scalars(select(User).order_by(User.full_name)).all())


@router.post("", response_model=UserRead, status_code=201)
def create_user(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    if payload.role not in ROLE_VALUES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"role must be one of {ROLE_VALUES}")
    if db.scalar(select(User).where(User.email == payload.email)) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A user with this email already exists")
    if payload.site_id is not None and db.get(Site, payload.site_id) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown site")

    user = User(
        full_name=payload.full_name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role,
        site_id=payload.site_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
