import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import settings

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_access_token(user_id: str, role: str, site_id: str | None) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "role": role,
        "site_id": site_id,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_access_token_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Raises jwt.PyJWTError (expired, bad signature, malformed) -- callers decide
    how to turn that into an HTTP response; this module stays framework-agnostic."""
    return jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])


def generate_refresh_token() -> tuple[str, str, datetime]:
    """Returns (plaintext_to_send_to_client, hash_to_store_in_db, expires_at).
    The plaintext is never stored -- only its hash is, so a DB leak alone can't
    be replayed as a live session."""
    plain = secrets.token_urlsafe(48)
    token_hash = hash_refresh_token(plain)
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_token_days)
    return plain, token_hash, expires_at


def hash_refresh_token(plain: str) -> str:
    # SHA-256, not bcrypt: this token is already high-entropy random data, not a
    # human password, so there's nothing for a slow hash to protect against --
    # a fast hash is the right tool for a lookup key.
    return hashlib.sha256(plain.encode("utf-8")).hexdigest()
