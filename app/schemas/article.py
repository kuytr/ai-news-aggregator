"""
schemas/article.py - Pydantic schemas for Article data validation.
"""

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class ArticleResponse(BaseModel):
    """Schema for article data returned from API."""
    id: int
    title: str
    url: str
    content: Optional[str] = None
    summary: Optional[str] = None
    image_url: Optional[str] = None
    source: Optional[str] = None
    author: Optional[str] = None
    category: str
    published_at: Optional[datetime] = None
    sentiment: str
    sentiment_score: float
    keywords: Optional[str] = None
    view_count: int
    rank_score: float
    created_at: datetime

    class Config:
        from_attributes = True


class ArticleListResponse(BaseModel):
    """Paginated list of articles."""
    articles: List[ArticleResponse]
    total: int
    page: int
    pages: int
    per_page: int


class SearchQuery(BaseModel):
    """Schema for search requests."""
    query: str
    category: Optional[str] = None
    page: int = 1
