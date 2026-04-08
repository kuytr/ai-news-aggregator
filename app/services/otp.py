"""
services/otp.py - OTP (One-Time Password) generation and validation.
OTPs are 6-digit codes stored in the database with expiry timestamps.
"""

import random
import string
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.config import settings
from app.models.user import OTPCode


def generate_otp(length: int = 6) -> str:
    """Generate a random numeric OTP of given length."""
    return "".join(random.choices(string.digits, k=length))


def create_otp(
    db: Session,
    user_id: int,
    purpose: str = "registration"
) -> str:
    """
    Create a new OTP record in the database for the given user.
    Invalidates any previous unused OTPs for the same purpose.
    Returns the plain OTP code to be emailed.
    """
    # Expire previous OTPs for this user/purpose to avoid confusion
    db.query(OTPCode).filter(
        OTPCode.user_id == user_id,
        OTPCode.purpose == purpose,
        OTPCode.is_used == False,  # noqa: E712
    ).delete()

    code = generate_otp()
    expires_at = datetime.utcnow() + timedelta(minutes=settings.OTP_EXPIRE_MINUTES)

    otp_record = OTPCode(
        user_id=user_id,
        code=code,
        purpose=purpose,
        expires_at=expires_at,
    )
    db.add(otp_record)
    db.commit()

    return code


def verify_otp(
    db: Session,
    user_id: int,
    code: str,
    purpose: str = "registration"
) -> bool:
    """
    Verify a submitted OTP code.
    Marks the OTP as used if valid.
    Returns True if valid and not expired, False otherwise.
    """
    otp_record = (
        db.query(OTPCode)
        .filter(
            OTPCode.user_id == user_id,
            OTPCode.code == code,
            OTPCode.purpose == purpose,
            OTPCode.is_used == False,  # noqa: E712
        )
        .first()
    )

    if not otp_record:
        return False

    if otp_record.is_expired:
        return False

    # Mark as used to prevent replay attacks
    otp_record.is_used = True
    db.commit()

    return True
