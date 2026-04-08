"""
services/sentiment.py - Sentiment analysis using TextBlob.
Classifies articles as positive, neutral, or negative.
"""

import logging
from sqlalchemy.orm import Session

from app.models.article import Article

logger = logging.getLogger(__name__)


def analyze_sentiment(text: str) -> tuple[str, float]:
    """
    Analyze the sentiment of the given text using TextBlob.

    Returns:
        Tuple of (label, score) where:
        - label: 'positive', 'neutral', or 'negative'
        - score: polarity score from -1.0 (negative) to +1.0 (positive)
    """
    try:
        from textblob import TextBlob

        blob = TextBlob(text[:2000])  # Limit for performance
        polarity = blob.sentiment.polarity

        # Classify based on polarity thresholds
        if polarity > 0.1:
            label = "positive"
        elif polarity < -0.1:
            label = "negative"
        else:
            label = "neutral"

        return label, round(polarity, 4)

    except Exception as e:
        logger.error(f"Sentiment analysis error: {e}")
        return "neutral", 0.0


def analyze_pending_articles(db: Session, batch_size: int = 50) -> int:
    """
    Run sentiment analysis on articles that still have default sentiment.
    Returns count of articles processed.
    """
    articles = (
        db.query(Article)
        .filter(Article.sentiment_score == 0.0)
        .limit(batch_size)
        .all()
    )

    count = 0
    for article in articles:
        text = " ".join(
            filter(None, [article.title, article.description, article.summary])
        )
        if text:
            label, score = analyze_sentiment(text)
            article.sentiment = label
            article.sentiment_score = score
            count += 1

    db.commit()
    logger.info(f"Sentiment analyzed for {count} articles")
    return count
