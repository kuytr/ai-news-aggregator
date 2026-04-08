"""
services/summarizer.py - AI-powered article summarization using OpenAI.
Generates 3–5 concise summary lines for each unsummarized article.
"""

import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.config import settings
from app.models.article import Article

logger = logging.getLogger(__name__)

# Lazy import OpenAI to avoid crashing if key is missing
_openai_client = None


def _get_client():
    """Return a cached OpenAI client instance."""
    global _openai_client
    if _openai_client is None:
        if not settings.OPENAI_API_KEY:
            return None
        from openai import OpenAI
        _openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
    return _openai_client


def summarize_text(text: str) -> Optional[str]:
    """
    Use OpenAI GPT to summarize the given text in 3–5 concise lines.
    Returns None if summarization fails or API key is not set.
    """
    client = _get_client()
    if not client:
        logger.warning("OpenAI API key not configured. Skipping summarization.")
        return None

    if not text or len(text.strip()) < 50:
        return None

    try:
        # Truncate to avoid hitting token limits (~4000 chars ≈ 1000 tokens)
        truncated = text[:4000]

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a news editor. Summarize the following article "
                        "in exactly 3 to 5 concise, clear sentences. "
                        "Focus on the key facts and avoid filler phrases."
                    ),
                },
                {"role": "user", "content": truncated},
            ],
            max_tokens=200,
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        logger.error(f"OpenAI summarization error: {e}")
        return None


def summarize_pending_articles(db: Session, batch_size: int = 10) -> int:
    """
    Find articles without summaries and generate them in batches.
    Returns the number of articles summarized.
    Batch size is kept small to manage API rate limits.
    """
    if not settings.OPENAI_API_KEY:
        return 0

    articles = (
        db.query(Article)
        .filter(Article.is_summarized == False)  # noqa: E712
        .order_by(Article.fetched_at.desc())
        .limit(batch_size)
        .all()
    )

    count = 0
    for article in articles:
        # Use content if available, fall back to description
        text = article.content or article.description or article.title
        summary = summarize_text(text)

        if summary:
            article.summary = summary

        # Mark as processed regardless (avoid re-trying failed articles)
        article.is_summarized = True
        count += 1

    db.commit()
    logger.info(f"Summarized {count} articles")
    return count
