"""
services/sentiment_service.py - Sentiment Analysis Service

Uses TextBlob to analyze sentiment of article text.
"""

import logging
from typing import Tuple

logger = logging.getLogger(__name__)


def analyze_sentiment(text: str) -> Tuple[str, float]:
    """
    Analyze sentiment of given text using TextBlob.
    
    Args:
        text: Article text to analyze
        
    Returns:
        Tuple of (sentiment_label, polarity_score)
        - sentiment_label: "Positive", "Negative", or "Neutral"
        - polarity_score: float between -1.0 (most negative) and 1.0 (most positive)
    """
    if not text or not text.strip():
        return "Neutral", 0.0

    try:
        from textblob import TextBlob
        blob = TextBlob(text[:2000])  # Limit text length for performance
        polarity = blob.sentiment.polarity  # type: ignore

        # Map polarity score to label
        if polarity > 0.1:
            label = "Positive"
        elif polarity < -0.1:
            label = "Negative"
        else:
            label = "Neutral"

        return label, round(polarity, 4)

    except Exception as e:
        logger.warning(f"Sentiment analysis failed: {e}")
        return "Neutral", 0.0


def extract_keywords(text: str, max_keywords: int = 10) -> list:
    """
    Extract important keywords from text using noun phrase extraction.
    
    Args:
        text: Text to extract keywords from
        max_keywords: Maximum number of keywords to return
        
    Returns:
        List of keyword strings
    """
    if not text:
        return []

    try:
        from textblob import TextBlob
        blob = TextBlob(text[:3000])
        # Get noun phrases as keywords
        noun_phrases = list(set(blob.noun_phrases))  # type: ignore
        # Filter short/irrelevant phrases and sort by length
        keywords = [kw for kw in noun_phrases if len(kw) > 3][:max_keywords]
        return keywords
    except Exception as e:
        logger.warning(f"Keyword extraction failed: {e}")
        return []
