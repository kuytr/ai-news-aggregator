"""
services/summarizer_service.py - AI Summarization Service

Uses OpenAI API to generate concise 3-5 line summaries of news articles.
Falls back gracefully if API is unavailable.
"""

import logging
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)

# Global flag to disable OpenAI after quota exceeded
_openai_quota_exceeded = False


def summarize_article(title: str, content: str) -> Optional[str]:
    """
    Generate a concise AI summary of an article using OpenAI GPT.
    Falls back to extractive summary if OpenAI is unavailable.
    """
    global _openai_quota_exceeded

    # Skip OpenAI if quota already exceeded this session
    if _openai_quota_exceeded:
        return _fallback_summary(content or title)

    if not settings.openai_api_key:
        logger.warning("OpenAI API key not configured. Skipping summarization.")
        return _fallback_summary(content or title)

    if not content or len(content.strip()) < 100:
        return _fallback_summary(content or title)

    try:
        from openai import OpenAI
        client = OpenAI(api_key=settings.openai_api_key)

        truncated_content = content[:4000]

        prompt = f"""Summarize the following news article in exactly 3-5 concise sentences.
Focus on the key facts, who is involved, and the significance.
Do not use bullet points. Write in plain English.

Title: {title}

Content: {truncated_content}

Summary:"""

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a professional news editor who creates concise, factual article summaries."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200,
            temperature=0.3,
        )

        summary = response.choices[0].message.content.strip()
        logger.debug(f"Summary generated for: {title[:50]}")
        return summary

    except Exception as e:
        error_str = str(e)

        # If quota exceeded, disable OpenAI for rest of session
        if "insufficient_quota" in error_str or "429" in error_str:
            _openai_quota_exceeded = True
            logger.warning("OpenAI quota exceeded — switching to fallback summaries for this session.")
        else:
            logger.error(f"OpenAI summarization failed: {e}")

        return _fallback_summary(content or title)


def _fallback_summary(content: str, max_chars: int = 400) -> str:
    """
    Simple fallback: return the first paragraph as summary.
    Used when OpenAI API is unavailable or quota exceeded.
    """
    if not content:
        return ""
    truncated = content[:max_chars]
    last_period = truncated.rfind(".")
    if last_period > 100:
        return truncated[:last_period + 1]
    return truncated + "..."