"""
models/article.py - Article and ArticleView Database Models
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Float, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class Article(Base):
    """Represents a news article stored in the database."""
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True)

    # Content fields
    title = Column(String(500), nullable=False, index=True)
    url = Column(String(1000), unique=True, nullable=False, index=True)
    content = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)  # AI-generated summary
    image_url = Column(String(1000), nullable=True)

    # Metadata
    source = Column(String(200), nullable=True)
    author = Column(String(200), nullable=True)
    category = Column(String(100), default="General", index=True)
    published_at = Column(DateTime, nullable=True, index=True)

    # AI/NLP fields
    sentiment = Column(String(20), default="Neutral")  # Positive / Neutral / Negative
    sentiment_score = Column(Float, default=0.0)       # -1.0 to 1.0
    keywords = Column(String(500), nullable=True)       # comma-separated keywords

    # Deduplication hash (hash of title+content)
    content_hash = Column(String(64), unique=True, nullable=False, index=True)

    # Engagement & ranking
    view_count = Column(Integer, default=0)
    rank_score = Column(Float, default=0.0)  # Computed ranking score

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    views = relationship("ArticleView", back_populates="article", cascade="all, delete-orphan")

    def get_keywords(self) -> list:
        """Parse keywords string into a list."""
        if not self.keywords:
            return []
        return [k.strip() for k in self.keywords.split(",") if k.strip()]

    def get_sentiment_badge_class(self) -> str:
        """Return Bootstrap badge class based on sentiment."""
        mapping = {
            "Positive": "badge-positive",
            "Negative": "badge-negative",
            "Neutral": "badge-neutral",
        }
        return mapping.get(self.sentiment, "badge-neutral")


class ArticleView(Base):
    """Tracks which user viewed which article (for personalization)."""
    __tablename__ = "article_views"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=False, index=True)
    viewed_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="article_views")
    article = relationship("Article", back_populates="views")
