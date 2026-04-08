"""Models package - exports all SQLAlchemy models."""
from app.models.user import User, OTPCode
from app.models.article import Article, ArticleView

__all__ = ["User", "OTPCode", "Article", "ArticleView"]
