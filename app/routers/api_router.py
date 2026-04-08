"""
routers/api_router.py - REST API Endpoints

JSON API for mobile apps and third-party integrations.
All endpoints return structured JSON responses.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc
from typing import Optional, List
import math

from app.database import get_db
from app.models.article import Article
from app.models.user import User
from app.schemas.article import ArticleResponse, ArticleListResponse
from app.schemas.user import TokenResponse, UserResponse
from app.services.auth_service import authenticate_user, create_access_token
from app.config import settings
from app.dependencies import get_current_user

router = APIRouter(prefix="/api/v1", tags=["API v1"])
PER_PAGE = settings.articles_per_page


@router.get("/articles", response_model=ArticleListResponse)
def api_get_articles(
    page: int = Query(default=1, ge=1),
    category: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    sort: str = Query(default="latest"),
    db: Session = Depends(get_db),
):
    query = db.query(Article)

    if category and category != "All":
        query = query.filter(Article.category == category)

    if search:
        term = f"%{search}%"
        query = query.filter(
            or_(
                Article.title.ilike(term),
                Article.summary.ilike(term),
                Article.keywords.ilike(term),
            )
        )

    if sort == "trending":
        query = query.order_by(desc(Article.view_count))
    elif sort == "ranked":
        query = query.order_by(desc(Article.rank_score))
    else:
        query = query.order_by(desc(Article.published_at))

    total = query.count()
    total_pages = max(1, math.ceil(total / PER_PAGE))
    articles = query.offset((page - 1) * PER_PAGE).limit(PER_PAGE).all()

    return ArticleListResponse(
        articles=articles,
        total=total,
        page=page,
        pages=total_pages,
        per_page=PER_PAGE,
    )


@router.get("/articles/{article_id}", response_model=ArticleResponse)
def api_get_article(article_id: int, db: Session = Depends(get_db)):
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article


@router.post("/auth/login", response_model=TokenResponse)
def api_login(email: str, password: str, db: Session = Depends(get_db)):
    user = authenticate_user(db, email=email, password=password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials or unverified account",
        )
    token = create_access_token(data={"sub": user.email})
    return TokenResponse(access_token=token, user=user)


@router.get("/me", response_model=UserResponse)
def api_get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/categories", response_model=List[str])
def api_get_categories():
    return settings.get_categories()


@router.post("/refresh")
def api_refresh_news(db: Session = Depends(get_db)):
    """Manually trigger a news fetch cycle."""
    try:
        from app.services.news_fetcher import fetch_all_news
        count = fetch_all_news(db)
        return {
            "status": "success",
            "new_articles": count,
            "message": f"Fetched {count} new articles!"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fetch failed: {str(e)}")
@router.post("/email-schedule")
def update_email_schedule(
    interval_minutes: int = Query(..., ge=1, le=10080, description="Interval in minutes (1 min to 7 days)"),
    db: Session = Depends(get_db),
):
    """Update how often email digests are sent."""
    from app.services.scheduler_service import update_email_schedule, get_email_interval
    success = update_email_schedule(interval_minutes)
    if success:
        return {
            "status": "success",
            "message": f"Email digest will now be sent every {interval_minutes} minutes.",
            "interval_minutes": interval_minutes,
        }
    raise HTTPException(status_code=500, detail="Failed to update email schedule.")


@router.get("/email-schedule")
def get_email_schedule():
    """Get current email digest schedule."""
    from app.services.scheduler_service import get_email_interval
    interval = get_email_interval()
    return {
        "interval_minutes": interval,
        "message": f"Email digest sent every {interval} minutes."
    }
@router.post("/send-digest")
def send_digest_now(db: Session = Depends(get_db)):
    """Manually trigger email digest to all users right now."""
    try:
        from app.services.scheduler_service import _send_daily_digests_job
        _send_daily_digests_job()
        return {"status": "success", "message": "Digest emails sent successfully!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed: {str(e)}")