"""
services/ranking_service.py - Article Ranking Service

Computes a rank score for each article based on:
1. Recency (newer = higher score)
2. Keyword frequency (more keywords matched = higher score)  
3. Engagement (view count)
"""

import logging
import math
from datetime import datetime, timedelta, timezone
from typing import List
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def compute_rank_score(article) -> float:
    """
    Compute a composite ranking score for an article.
    
    Formula:
        score = recency_score * 0.5 + keyword_score * 0.2 + engagement_score * 0.3
    """
    # --- Recency Score (0–1) ---
    recency_score = 0.5  # Default if no date
    if article.published_at:
        try:
            now = datetime.now(timezone.utc)
            published = article.published_at
            # Make published_at timezone-aware if it isn't
            if published.tzinfo is None:
                published = published.replace(tzinfo=timezone.utc)
            age_hours = (now - published).total_seconds() / 3600
            recency_score = max(0.0, 1.0 - (age_hours / 48.0))
        except Exception:
            recency_score = 0.5

    # --- Keyword Score (0–1) ---
    keyword_count = len(article.get_keywords()) if hasattr(article, 'get_keywords') else 0
    keyword_score = min(1.0, keyword_count / 10.0)

    # --- Engagement Score (0–1) ---
    view_count = article.view_count or 0
    engagement_score = min(1.0, math.log1p(view_count) / math.log1p(1000))

    # --- Weighted composite ---
    score = (recency_score * 0.5) + (keyword_score * 0.2) + (engagement_score * 0.3)
    return round(score, 6)


def recompute_rankings(db: Session) -> None:
    """
    Recompute rank scores for all articles in DB.
    Called periodically by the scheduler.
    """
    from app.models.article import Article

    articles = db.query(Article).all()
    for article in articles:
        article.rank_score = compute_rank_score(article)

    db.commit()
    logger.info(f"Recomputed rankings for {len(articles)} articles.")


def get_trending_articles(db: Session, limit: int = 10) -> List:
    """
    Return top trending articles ranked by score.
    Trending = high engagement + recent.
    """
    from app.models.article import Article

    cutoff = datetime.now(timezone.utc) - timedelta(hours=48)

    # Handle both timezone-aware and naive published_at in DB
    articles = (
        db.query(Article)
        .order_by(Article.view_count.desc(), Article.rank_score.desc())
        .limit(limit * 3)
        .all()
    )

    # Filter manually to handle mixed timezone awareness
    recent = []
    for a in articles:
        if a.published_at:
            pub = a.published_at
            if pub.tzinfo is None:
                pub = pub.replace(tzinfo=timezone.utc)
            if pub >= cutoff:
                recent.append(a)
        if len(recent) >= limit:
            break

    return recent