"""
services/scheduler.py - APScheduler background jobs.
Runs two recurring tasks:
  1. Fetch news every N minutes (configurable)
  2. Send daily email digests at a configured time
"""

import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from app.config import settings

logger = logging.getLogger(__name__)

# Global scheduler instance
_scheduler = BackgroundScheduler(timezone="UTC")


def _news_fetch_job() -> None:
    """Background job: fetch news from all sources and process articles."""
    logger.info("Scheduler: Starting news fetch job...")
    try:
        from app.database import SessionLocal
        from app.services.news_fetcher import fetch_all_news
        from app.services.summarizer import summarize_pending_articles
        from app.services.sentiment import analyze_pending_articles
        from app.services.ranking import update_article_ranks

        db = SessionLocal()
        try:
            fetch_all_news(db)
            analyze_pending_articles(db)
            summarize_pending_articles(db, batch_size=5)
            update_article_ranks(db)
        finally:
            db.close()

    except Exception as e:
        logger.error(f"Scheduler news fetch job failed: {e}")


def _daily_digest_job() -> None:
    """Background job: send daily email digest to all active, verified users."""
    logger.info("Scheduler: Starting daily digest job...")
    try:
        from app.database import SessionLocal
        from app.models.user import User
        from app.models.article import Article
        from app.services.email import send_daily_digest
        from sqlalchemy import desc

        db = SessionLocal()
        try:
            # Get top trending articles (highest rank score, last 24h)
            trending = (
                db.query(Article)
                .order_by(desc(Article.rank_score))
                .limit(10)
                .all()
            )
            trending_dicts = [
                {
                    "title": a.title,
                    "url": a.url,
                    "source": a.source,
                    "sentiment": a.sentiment,
                    "summary": a.summary or a.description or "",
                }
                for a in trending
            ]

            # Send to each verified, active user
            users = (
                db.query(User)
                .filter(User.is_verified == True, User.is_active == True)  # noqa
                .all()
            )

            for user in users:
                # Build personalized articles based on user's preferred categories
                preferred = user.preferred_categories_list
                if "All" in preferred:
                    personalized = trending[:5]
                else:
                    personalized = (
                        db.query(Article)
                        .filter(Article.category.in_(preferred))
                        .order_by(desc(Article.rank_score))
                        .limit(5)
                        .all()
                    )

                personalized_dicts = [
                    {
                        "title": a.title,
                        "url": a.url,
                        "source": a.source,
                        "sentiment": a.sentiment,
                        "summary": a.summary or a.description or "",
                    }
                    for a in personalized
                ]

                send_daily_digest(
                    to_email=user.email,
                    username=user.username,
                    trending_articles=trending_dicts,
                    personalized_articles=personalized_dicts,
                )

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Scheduler daily digest job failed: {e}")


def start_scheduler() -> None:
    """
    Register all jobs and start the background scheduler.
    Called once at application startup.
    """
    if _scheduler.running:
        logger.warning("Scheduler is already running.")
        return

    # Job 1: Fetch news every N minutes
    _scheduler.add_job(
        func=_news_fetch_job,
        trigger=IntervalTrigger(minutes=settings.NEWS_FETCH_INTERVAL_MINUTES),
        id="news_fetch",
        name="Fetch News Articles",
        replace_existing=True,
        max_instances=1,  # Prevent overlapping runs
    )

    # Job 2: Daily digest at configured time (UTC)
    _scheduler.add_job(
        func=_daily_digest_job,
        trigger=CronTrigger(
            hour=settings.DAILY_DIGEST_HOUR,
            minute=settings.DAILY_DIGEST_MINUTE,
        ),
        id="daily_digest",
        name="Send Daily Email Digest",
        replace_existing=True,
        max_instances=1,
    )

    _scheduler.start()
    logger.info(
        f"Scheduler started. News fetch every {settings.NEWS_FETCH_INTERVAL_MINUTES}m, "
        f"digest at {settings.DAILY_DIGEST_HOUR:02d}:{settings.DAILY_DIGEST_MINUTE:02d} UTC"
    )


def stop_scheduler() -> None:
    """Gracefully shut down the scheduler."""
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped.")
