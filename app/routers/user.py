"""
routers/user.py - User dashboard and preference management endpoints.
"""

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models.article import Article, UserArticleView
from app.models.user import User
from app.config import settings
from app.dependencies import get_current_user

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    User dashboard showing:
    - Personalized news feed based on preferences
    - Recently viewed articles
    - Category preference controls
    """
    preferred = current_user.preferred_categories_list

    # Build personalized article query
    if "All" in preferred:
        personalized_articles = (
            db.query(Article)
            .order_by(desc(Article.rank_score))
            .limit(12)
            .all()
        )
    else:
        personalized_articles = (
            db.query(Article)
            .filter(Article.category.in_(preferred))
            .order_by(desc(Article.rank_score))
            .limit(12)
            .all()
        )

    # Recently viewed articles by this user
    viewed_ids = (
        db.query(UserArticleView.article_id)
        .filter(UserArticleView.user_id == current_user.id)
        .order_by(desc(UserArticleView.viewed_at))
        .limit(6)
        .subquery()
    )
    recently_viewed = (
        db.query(Article)
        .filter(Article.id.in_(viewed_ids))
        .limit(6)
        .all()
    )

    # Trending articles (global)
    trending = (
        db.query(Article)
        .order_by(desc(Article.view_count))
        .limit(5)
        .all()
    )

    return templates.TemplateResponse(
        "user/dashboard.html",
        {
            "request": request,
            "current_user": current_user,
            "personalized_articles": personalized_articles,
            "recently_viewed": recently_viewed,
            "trending": trending,
            "categories": settings.CATEGORIES,
            "preferred": preferred,
        },
    )


@router.post("/dashboard/preferences")
async def update_preferences(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update user's preferred news categories from form submission."""
    form_data = await request.form()
    # Collect all checked category checkboxes
    selected = [
        v for k, v in form_data.multi_items() if k == "categories"
    ]

    if not selected:
        selected = ["All"]

    current_user.preferred_categories = ",".join(selected)
    db.commit()

    return RedirectResponse(url="/dashboard?updated=1", status_code=303)
