"""
services/scheduler_service.py - Background Task Scheduler
"""

import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from app.config import settings

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(timezone="UTC")
_email_interval_minutes = None
_last_digest_article_ids = set()  # Track which articles were sent last time


def get_email_interval() -> int:
    return _email_interval_minutes or settings.news_fetch_interval_minutes


def update_email_schedule(interval_minutes: int) -> bool:
    global _email_interval_minutes
    try:
        _email_interval_minutes = interval_minutes
        if scheduler.running:
            scheduler.reschedule_job(
                job_id="daily_digest",
                trigger=IntervalTrigger(minutes=interval_minutes),
            )
            logger.info(f"[Scheduler] Email rescheduled to every {interval_minutes} mins.")
        return True
    except Exception as e:
        logger.error(f"[Scheduler] Reschedule failed: {e}")
        return False


def _fetch_news_job() -> None:
    from app.database import SessionLocal
    from app.services.news_fetcher import fetch_all_news
    from app.services.ranking_service import recompute_rankings

    db = SessionLocal()
    try:
        count = fetch_all_news(db)
        recompute_rankings(db)
        logger.info(f"[Scheduler] Fetched {count} new articles.")
    except Exception as e:
        logger.error(f"[Scheduler] Fetch job failed: {e}")
    finally:
        db.close()


def _send_daily_digests_job() -> None:
    global _last_digest_article_ids

    from app.database import SessionLocal
    from app.models.user import User
    from app.models.article import Article, ArticleView
    from app.services.email_service import send_daily_digest
    from app.services.ranking_service import get_trending_articles
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import desc, or_

    db = SessionLocal()
    try:
        # ── Get trending articles ──
        trending = get_trending_articles(db, limit=5)
        trending_data = [
            {
                "title": a.title,
                "url": a.url,
                "summary": a.summary or "",
                "source": a.source or "",
                "category": a.category,
                "sentiment": a.sentiment,
            }
            for a in trending
        ]

        users = db.query(User).filter(
            User.is_active == True,
            User.is_verified == True
        ).all()

        sent_count = 0

        for user in users:
            try:
                preferred = user.get_preferred_categories()

                # ── Get user's viewed article IDs ──
                viewed_ids_rows = (
                    db.query(ArticleView.article_id)
                    .filter(ArticleView.user_id == user.id)
                    .all()
                )
                viewed_ids = [row.article_id for row in viewed_ids_rows]

                # ── Try NEW articles first (last 2 hours, not viewed, not sent before) ──
                two_hours_ago = datetime.now(timezone.utc) - timedelta(hours=2)

                new_query = db.query(Article).filter(
                    Article.created_at >= two_hours_ago
                )
                if preferred:
                    new_query = new_query.filter(
                        Article.category.in_(preferred)
                    )
                # Exclude already viewed
                if viewed_ids:
                    new_query = new_query.filter(
                        Article.id.notin_(viewed_ids)
                    )
                # Exclude already sent in last digest
                if _last_digest_article_ids:
                    new_query = new_query.filter(
                        Article.id.notin_(list(_last_digest_article_ids))
                    )

                new_articles = (
                    new_query
                    .order_by(desc(Article.view_count), desc(Article.rank_score))
                    .limit(5)
                    .all()
                )

                # ── If no new articles → use personalized not yet viewed ──
                if not new_articles:
                    fallback_query = db.query(Article)
                    if preferred:
                        fallback_query = fallback_query.filter(
                            Article.category.in_(preferred)
                        )
                    if viewed_ids:
                        fallback_query = fallback_query.filter(
                            Article.id.notin_(viewed_ids)
                        )
                    if _last_digest_article_ids:
                        fallback_query = fallback_query.filter(
                            Article.id.notin_(list(_last_digest_article_ids))
                        )
                    new_articles = (
                        fallback_query
                        .order_by(desc(Article.rank_score))
                        .limit(5)
                        .all()
                    )

                # ── If still nothing → show top ranked (avoid empty email) ──
                if not new_articles:
                    new_articles = (
                        db.query(Article)
                        .order_by(desc(Article.rank_score))
                        .limit(5)
                        .all()
                    )

                personalized_data = [
                    {
                        "title": a.title,
                        "url": a.url,
                        "summary": a.summary or "",
                        "source": a.source or "",
                        "category": a.category,
                        "sentiment": a.sentiment,
                    }
                    for a in new_articles
                ]

                # Track sent article IDs
                _last_digest_article_ids.update([a.id for a in new_articles])

                success = send_daily_digest(
                    email=user.email,
                    username=user.username,
                    trending_articles=trending_data,
                    personalized_articles=personalized_data,
                )
                if success:
                    sent_count += 1

            except Exception as e:
                logger.error(f"[Scheduler] Digest failed for {user.email}: {e}")
                continue

        logger.info(f"[Scheduler] Digests sent to {sent_count}/{len(users)} users.")

    except Exception as e:
        logger.error(f"[Scheduler] Digest job failed: {e}")
    finally:
        db.close()


def start_scheduler() -> None:
    if scheduler.running:
        return

    scheduler.add_job(
        func=_fetch_news_job,
        trigger=IntervalTrigger(minutes=settings.news_fetch_interval_minutes),
        id="fetch_news",
        name="Fetch News Articles",
        replace_existing=True,
        max_instances=1,
    )

    scheduler.add_job(
        func=_send_daily_digests_job,
        trigger=IntervalTrigger(minutes=get_email_interval()),
        id="daily_digest",
        name="Send Email Digests",
        replace_existing=True,
        max_instances=1,
    )

    scheduler.start()
    logger.info(
        f"Scheduler started. "
        f"News fetch every {settings.news_fetch_interval_minutes} mins. "
        f"Email digest every {get_email_interval()} mins."
    )


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler stopped.")