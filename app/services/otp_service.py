"""
services/otp_service.py - OTP (One-Time Password) Service

Generates, stores, and validates OTP codes for email verification.
"""

import random
import string
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.config import settings
from app.models.user import OTPCode


def generate_otp(length: int = 6) -> str:
    """Generate a random numeric OTP code."""
    return "".join(random.choices(string.digits, k=length))


def create_otp(db: Session, email: str, user_id: Optional[int] = None) -> str:
    """
    Create and store a new OTP for the given email.
    Invalidates any existing unused OTPs for this email.
    
    Returns:
        The generated OTP code (to be sent via email)
    """
    # Invalidate existing OTPs for this email
    existing = db.query(OTPCode).filter(
        OTPCode.email == email,
        OTPCode.is_used == False  # noqa: E712
    ).all()
    for otp in existing:
        otp.is_used = True

    # Generate new OTP
    code = generate_otp()
    expires_at = datetime.utcnow() + timedelta(minutes=settings.otp_expire_minutes)

    otp_record = OTPCode(
        user_id=user_id,
        email=email,
        code=code,
        is_used=False,
        expires_at=expires_at,
    )
    db.add(otp_record)
    db.commit()
    return code


def verify_otp(db: Session, email: str, code: str) -> bool:
    """
    Verify an OTP code for the given email.
    Marks the OTP as used if valid.
    
    Returns:
        True if OTP is valid and not expired, False otherwise
    """
    otp_record = db.query(OTPCode).filter(
        OTPCode.email == email,
        OTPCode.code == code,
        OTPCode.is_used == False  # noqa: E712
    ).order_by(OTPCode.created_at.desc()).first()

    if not otp_record:
        return False

    # Check expiry
    if datetime.utcnow() > otp_record.expires_at:
        otp_record.is_used = True
        db.commit()
        return False

    # Mark as used
    otp_record.is_used = True
    db.commit()
    return True
