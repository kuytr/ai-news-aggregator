"""
services/ranking.py - Article ranking algorithm.
Computes a composite rank_score based on:
  1. Recency   - newer articles score higher
  2. Engagement - view count boosts score
  3. Sentiment  - positive articles get a slight boost
"""

import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.article import Article

logger = logging.getLogger(__name__)

# ── Ranking Constants ──────────────────────────────────────────────────────────
RECENCY_WEIGHT = 0.5       # Weight for time-based decay
ENGAGEMENT_WEIGHT = 0.35   # Weight for view count
SENTIMENT_WEIGHT = 0.15    # Weight for sentiment polarity

MAX_AGE_HOURS = 72         # Articles older than this get minimum recency score
MAX_VIEWS_NORMALIZER = 100 # Normalizer for view count (diminishing returns)


def _recency_score(published_at: datetime) -> float:
    """
    Compute a recency score 0.0–1.0.
    Score decays linearly from 1.0 (just published) to 0.0 (MAX_AGE_HOURS old).
    """
    if not published_at:
        return 0.1  # Unknown date gets a low but non-zero score

    age = datetime.utcnow() - published_at
    age_hours = age.total_seconds() / 3600

    # Linear decay: 1.0 at 0 hours, 0.0 at MAX_AGE_HOURS
    score = max(0.0, 1.0 - (age_hours / MAX_AGE_HOURS))
    return round(score, 4)


def _engagement_score(view_count: int) -> float:
    """
    Compute an engagement score 0.0–1.0 using square-root normalization.
    Square root provides diminishing returns (avoids very popular articles dominating).
    """
    import math
    normalized = min(1.0, math.sqrt(view_count) / math.sqrt(MAX_VIEWS_NORMALIZER))
    return round(normalized, 4)


def _sentiment_score_component(polarity: float) -> float:
    """
    Map sentiment polarity (-1.0 to 1.0) to a 0.0–1.0 score.
    Neutral (0.0) maps to 0.5, giving all articles a baseline.
    """
    return round((polarity + 1.0) / 2.0, 4)


def compute_rank_score(article: Article) -> float:
    """Compute composite rank score for a single article."""
    r = _recency_score(article.published_at) * RECENCY_WEIGHT
    e = _engagement_score(article.view_count) * ENGAGEMENT_WEIGHT
    s = _sentiment_score_component(article.sentiment_score) * SENTIMENT_WEIGHT
    return round(r + e + s, 6)


def update_article_ranks(db: Session) -> None:
    """
    Recalculate rank_score for all articles.
    Called periodically by the scheduler.
    """
    articles = db.query(Article).all()
    for article in articles:
        article.rank_score = compute_rank_score(article)

    db.commit()
    logger.info(f"Updated rank scores for {len(articles)} articles")
