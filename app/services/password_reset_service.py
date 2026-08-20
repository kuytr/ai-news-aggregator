"""Password reset token generation and validation."""

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.config import settings
from app.models.password_reset import PasswordResetToken
from app.models.user import User
from app.services.auth_service import hash_password


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_password_reset_token(db: Session, user: User) -> str:
    """Invalidate previous reset tokens and create a new one-time token."""
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.is_used.is_(False),
    ).update({PasswordResetToken.is_used: True}, synchronize_session=False)

    raw_token = secrets.token_urlsafe(48)
    token = PasswordResetToken(
        user_id=user.id,
        token_hash=_hash_token(raw_token),
        expires_at=datetime.utcnow() + timedelta(minutes=settings.password_reset_expire_minutes),
    )
    db.add(token)
    db.commit()
    return raw_token


def get_valid_reset_token(db: Session, raw_token: str) -> Optional[PasswordResetToken]:
    """Return a valid, unused token or None."""
    token_hash = _hash_token(raw_token)
    reset_token = db.query(PasswordResetToken).filter(
        PasswordResetToken.token_hash == token_hash,
        PasswordResetToken.is_used.is_(False),
    ).first()

    if not reset_token or reset_token.expires_at < datetime.utcnow():
        return None
    return reset_token


def reset_user_password(db: Session, reset_token: PasswordResetToken, new_password: str) -> None:
    """Set the new password and permanently consume the reset token."""
    user = db.query(User).filter(User.id == reset_token.user_id).first()
    if not user:
        raise ValueError("User no longer exists")

    user.hashed_password = hash_password(new_password)
    reset_token.is_used = True
    db.commit()
