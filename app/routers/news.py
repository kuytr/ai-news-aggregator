"""
routers/news.py - News browsing endpoints: home, article detail, search, category filter.
"""

import math
from typing import Optional
from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_

from app.database import get_db
from app.models.article import Article, UserArticleView
from app.models.user import User
from app.config import settings
from app.dependencies import get_current_user_optional

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def _get_articles_query(
    db: Session,
    category: str = "All",
    search: str = "",
    sort: str = "latest",
):
    """Build a filtered, sorted SQLAlchemy query for articles."""
    query = db.query(Article)

    # Category filter
    if category and category != "All":
        query = query.filter(Article.category == category)

    # Full-text search across title, description, summary
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Article.title.ilike(search_term),
                Article.description.ilike(search_term),
                Article.summary.ilike(search_term),
                Article.source.ilike(search_term),
            )
        )

    # Sorting
    if sort == "rank":
        query = query.order_by(desc(Article.rank_score))
    elif sort == "views":
        query = query.order_by(desc(Article.view_count))
    else:  # default: latest
        query = query.order_by(desc(Article.published_at))

    return query


@router.get("/", response_class=HTMLResponse)
async def home(
    request: Request,
    category: str = Query(default="All"),
    search: str = Query(default=""),
    sort: str = Query(default="rank"),
    page: int = Query(default=1, ge=1),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Home page with article feed, search, and category filters."""
    per_page = settings.ARTICLES_PER_PAGE

    query = _get_articles_query(db, category, search, sort)
    total = query.count()
    total_pages = max(1, math.ceil(total / per_page))
    page = min(page, total_pages)

    articles = query.offset((page - 1) * per_page).limit(per_page).all()

    return templates.TemplateResponse(
        "news/home.html",
        {
            "request": request,
            "articles": articles,
            "categories": settings.CATEGORIES,
            "selected_category": category,
            "search": search,
            "sort": sort,
            "page": page,
            "total_pages": total_pages,
            "total": total,
            "current_user": current_user,
        },
    )


@router.get("/article/{article_id}", response_class=HTMLResponse)
async def article_detail(
    request: Request,
    article_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Article detail page. Increments view count and tracks user view."""
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        return templates.TemplateResponse(
            "404.html", {"request": request}, status_code=404
        )

    # Increment global view counter
    article.view_count += 1

    # Track individual user view for personalization
    if current_user:
        existing = (
            db.query(UserArticleView)
            .filter(
                UserArticleView.user_id == current_user.id,
                UserArticleView.article_id == article_id,
            )
            .first()
        )
        if not existing:
            db.add(UserArticleView(user_id=current_user.id, article_id=article_id))

    db.commit()

    # Related articles: same category, different ID
    related = (
        db.query(Article)
        .filter(Article.category == article.category, Article.id != article_id)
        .order_by(desc(Article.rank_score))
        .limit(4)
        .all()
    )

    return templates.TemplateResponse(
        "news/article_detail.html",
        {
            "request": request,
            "article": article,
            "related": related,
            "current_user": current_user,
        },
    )


@router.get("/api/articles", response_class=JSONResponse)
async def api_articles(
    category: str = Query(default="All"),
    search: str = Query(default=""),
    sort: str = Query(default="rank"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=12, le=50),
    db: Session = Depends(get_db),
):
    """
    REST API endpoint for articles.
    Useful for mobile apps and external consumers.
    """
    query = _get_articles_query(db, category, search, sort)
    total = query.count()
    total_pages = max(1, math.ceil(total / per_page))
    articles = query.offset((page - 1) * per_page).limit(per_page).all()

    return {
        "articles": [
            {
                "id": a.id,
                "title": a.title,
                "url": a.url,
                "description": a.description,
                "image_url": a.image_url,
                "source": a.source,
                "category": a.category,
                "summary": a.summary,
                "sentiment": a.sentiment,
                "sentiment_score": a.sentiment_score,
                "published_at": a.published_at.isoformat() if a.published_at else None,
                "view_count": a.view_count,
                "rank_score": a.rank_score,
            }
            for a in articles
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
    }
