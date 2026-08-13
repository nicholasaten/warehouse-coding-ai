from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import CurrentUser, get_current_user
from app.core.security import create_access_token, generate_refresh_token, hash_refresh_token, verify_password
from app.db.session import get_db
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.auth import LoginRequest, LoginResponse, MeResponse

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE_NAME = "refresh_token"


def _to_me_response(user: User) -> MeResponse:
    return MeResponse(id=user.id, full_name=user.full_name, email=user.email, role=user.role, site_id=user.site_id)


def _set_refresh_cookie(response: Response, plain_refresh: str, max_age_seconds: int) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=plain_refresh,
        httponly=True,
        secure=True,
        samesite=settings.cookie_samesite,
        max_age=max_age_seconds,
    )


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)) -> LoginResponse:
    user = db.scalar(select(User).where(User.email == payload.email))

    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    access_token = create_access_token(user_id=str(user.id), role=user.role, site_id=str(user.site_id) if user.site_id else None)

    plain_refresh, token_hash, expires_at = generate_refresh_token()
    db.add(RefreshToken(user_id=user.id, token_hash=token_hash, expires_at=expires_at))
    db.commit()

    _set_refresh_cookie(response, plain_refresh, settings.jwt_refresh_token_days * 24 * 60 * 60)
    return LoginResponse(access_token=access_token, user=_to_me_response(user))


@router.post("/refresh", response_model=LoginResponse)
def refresh(request: Request, response: Response, db: Session = Depends(get_db)) -> LoginResponse:
    plain_refresh = request.cookies.get(REFRESH_COOKIE_NAME)
    if not plain_refresh:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No refresh token")

    token_hash = hash_refresh_token(plain_refresh)
    token_row = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))

    if token_row is None or token_row.revoked_at is not None or token_row.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token invalid or expired")

    user = db.get(User, token_row.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token invalid or expired")

    access_token = create_access_token(user_id=str(user.id), role=user.role, site_id=str(user.site_id) if user.site_id else None)
    return LoginResponse(access_token=access_token, user=_to_me_response(user))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> None:
    plain_refresh = request.cookies.get(REFRESH_COOKIE_NAME)
    if plain_refresh:
        token_hash = hash_refresh_token(plain_refresh)
        token_row = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
        if token_row is not None and token_row.revoked_at is None:
            token_row.revoked_at = datetime.now(timezone.utc)
            db.commit()
    response.delete_cookie(REFRESH_COOKIE_NAME, secure=True, samesite=settings.cookie_samesite)


@router.get("/me", response_model=MeResponse)
def me(current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)) -> MeResponse:
    user = db.get(User, current_user.id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return _to_me_response(user)
