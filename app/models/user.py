"""
models/user.py - User and OTP Database Models
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class User(Base):
    """Represents a registered user in the system."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)

    # Email verification status
    is_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

    # User preferences - comma-separated categories
    preferred_categories = Column(String(500), default="Technology,AI")

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    # Relationships
    otp_codes = relationship("OTPCode", back_populates="user", cascade="all, delete-orphan")
    article_views = relationship("ArticleView", back_populates="user", cascade="all, delete-orphan")

    def get_preferred_categories(self) -> list:
        """Parse preferred_categories string into a list."""
        if not self.preferred_categories:
            return []
        return [c.strip() for c in self.preferred_categories.split(",") if c.strip()]

    def set_preferred_categories(self, categories: list) -> None:
        """Set preferred_categories from a list."""
        self.preferred_categories = ",".join(categories)


class OTPCode(Base):
    """Stores OTP codes for email verification."""
    __tablename__ = "otp_codes"

    id = Column(Integer, primary_key=True, index=True)
    
    # ✅ FIXED: Proper ForeignKey
    user_id = Column(Integer, ForeignKey("users.id"), index=True)

    email = Column(String(255), index=True, nullable=False)
    code = Column(String(10), nullable=False)
    is_used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)

    # Relationship
    user = relationship("User", back_populates="otp_codes")