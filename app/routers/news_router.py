"""
routers/news_router.py - News Article Routes
"""

import logging

from fastapi import APIRouter, Depends, Request, Query, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc
from typing import Optional
import math
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

from app.database import get_db
from app.models.article import Article, ArticleView
from app.models.user import User
from app.config import settings
from app.dependencies import get_current_user_optional

router = APIRouter(tags=["news"])
templates = Jinja2Templates(directory="app/templates")

PER_PAGE = settings.articles_per_page


@router.get("/", response_class=HTMLResponse)
async def home(
    request: Request,
    page: int = Query(default=1, ge=1),
    category: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    sort: str = Query(default="latest"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    query = db.query(Article)

    if category and category != "All":
        query = query.filter(Article.category == category)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Article.title.ilike(search_term),
                Article.summary.ilike(search_term),
                Article.content.ilike(search_term),
                Article.keywords.ilike(search_term),
            )
        )

    if sort == "latest":
        query = query.order_by(desc(Article.published_at))
    elif sort == "trending":
        query = query.order_by(desc(Article.view_count))
    elif sort == "ranked":
        query = query.order_by(desc(Article.rank_score))
    else:
        query = query.order_by(desc(Article.published_at))

    total = query.count()
    total_pages = max(1, math.ceil(total / PER_PAGE))
    page = min(page, total_pages)
    articles = query.offset((page - 1) * PER_PAGE).limit(PER_PAGE).all()

    return templates.TemplateResponse("index.html", {
        "request": request,
        "articles": articles,
        "current_user": current_user,
        "categories": settings.get_categories(),
        "selected_category": category or "All",
        "search_query": search or "",
        "sort": sort,
        "page": page,
        "total_pages": total_pages,
        "total": total,
    })


def _update_article_views(article_id: int, user_id: Optional[int] = None) -> None:
    """
    Background task to update article view count and log user views.
    Non-blocking - does not affect response time.
    """
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        # Update article view count
        article = db.query(Article).filter(Article.id == article_id).first()
        if article:
            article.view_count += 1
            db.commit()
        
        # Log user view if user is logged in
        if user_id:
            existing_view = db.query(ArticleView).filter(
                ArticleView.user_id == user_id,
                ArticleView.article_id == article_id,
            ).first()
            if not existing_view:
                view = ArticleView(user_id=user_id, article_id=article_id)
                db.add(view)
                db.commit()
    except OperationalError:
        # Silently fail if database is locked - view count is not critical
        pass
    except Exception as e:
        logger.error(f"Failed to update article views: {e}")
    finally:
        db.close()


@router.get("/article/{article_id}", response_class=HTMLResponse)
async def article_detail(
    article_id: int,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)
    
    # Schedule view count update as background task (non-blocking)
    background_tasks.add_task(_update_article_views, article_id, current_user.id if current_user else None)
    
    # Fetch related articles
    related = (
        db.query(Article)
        .filter(Article.category == article.category, Article.id != article.id)
        .order_by(desc(Article.rank_score))
        .limit(4)
        .all()
    )

    return templates.TemplateResponse("article_detail.html", {
        "request": request,
        "article": article,
        "related_articles": related,
        "current_user": current_user,
    })


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    if not current_user:
        return RedirectResponse("/auth/login", status_code=302)

    preferred_categories = current_user.get_preferred_categories()

    # ── Get user's viewed article IDs ──
    viewed_ids_rows = (
        db.query(ArticleView.article_id)
        .filter(ArticleView.user_id == current_user.id)
        .order_by(desc(ArticleView.viewed_at))
        .all()
    )
    viewed_ids = [row.article_id for row in viewed_ids_rows]

    # ── Check for NEW articles (added in last 2 hours) ──
    two_hours_ago = datetime.now(timezone.utc) - timedelta(hours=2)

    new_articles_query = db.query(Article).filter(
        Article.created_at >= two_hours_ago
    )
    if preferred_categories:
        new_articles_query = new_articles_query.filter(
            Article.category.in_(preferred_categories)
        )

    # Exclude already viewed articles
    if viewed_ids:
        new_articles_query = new_articles_query.filter(
            Article.id.notin_(viewed_ids)
        )

    new_articles = (
        new_articles_query
        .order_by(desc(Article.view_count), desc(Article.rank_score))
        .limit(12)
        .all()
    )

    # ── If new articles found → show them ──
    # ── If no new articles → show personalized based on view history ──
    if new_articles:
        personalized = new_articles
        is_new = True
    else:
        # Fall back to personalized based on preferences + view history
        if preferred_categories:
            personalized_query = (
                db.query(Article)
                .filter(Article.category.in_(preferred_categories))
            )
        else:
            personalized_query = db.query(Article)

        # Exclude recently viewed (last 6) to avoid repetition
        recently_viewed_ids = viewed_ids[:6]
        if recently_viewed_ids:
            personalized_query = personalized_query.filter(
                Article.id.notin_(recently_viewed_ids)
            )

        personalized = (
            personalized_query
            .order_by(desc(Article.rank_score))
            .limit(12)
            .all()
        )

        # If still empty (all articles viewed), show top ranked
        if not personalized:
            personalized = (
                db.query(Article)
                .order_by(desc(Article.rank_score))
                .limit(12)
                .all()
            )
        is_new = False

    # ── Recently viewed articles ──
    recently_viewed = []
    if viewed_ids:
        recently_viewed = (
            db.query(Article)
            .filter(Article.id.in_(viewed_ids[:6]))
            .all()
        )

    # ── Trending articles ──
    trending = (
        db.query(Article)
        .order_by(desc(Article.view_count))
        .limit(5)
        .all()
    )

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "current_user": current_user,
        "personalized_articles": personalized,
        "recently_viewed": recently_viewed,
        "trending": trending,
        "categories": settings.get_categories(),
        "preferred_categories": preferred_categories,
        "is_new": is_new,  # flag to show "New Articles!" badge
    })


@router.post("/preferences")
async def update_preferences(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    if not current_user:
        return RedirectResponse("/auth/login", status_code=302)

    form = await request.form()
    selected = form.getlist("categories")
    current_user.set_preferred_categories(selected)
    db.commit()
    return RedirectResponse("/dashboard", status_code=302)