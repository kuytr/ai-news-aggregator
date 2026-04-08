"""
dependencies.py - FastAPI Dependency Injection

Provides reusable dependencies for route handlers:
- Database session
- Current authenticated user (from JWT cookie or header)
"""

from typing import Optional
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.services.auth_service import decode_access_token, get_user_by_email


def get_current_user_optional(
    request: Request,
    db: Session = Depends(get_db),
) -> Optional[User]:
    """
    Try to get current user from JWT token (cookie or header).
    Returns None if not authenticated (for public pages).
    """
    token = None

    # Try to get token from cookie first
    token = request.cookies.get("access_token")

    # Fallback: Authorization header
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]

    if not token:
        return None

    payload = decode_access_token(token)
    if not payload:
        return None

    email = payload.get("sub")
    if not email:
        return None

    user = get_user_by_email(db, email)
    if not user or not user.is_active:
        return None

    return user


def get_current_user(
    user: Optional[User] = Depends(get_current_user_optional),
) -> User:
    """
    Require authenticated user. Raises 401 if not logged in.
    Use this for protected routes.
    """
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_verified_user(
    user: User = Depends(get_current_user),
) -> User:
    """
    Require verified user. Raises 403 if email not verified.
    """
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required",
        )
    return user
