"""
services/email.py - Reusable email service using smtplib (SMTP).
Handles OTP emails and daily digest emails.
All credentials are loaded from environment variables.
"""

import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List

from app.config import settings

logger = logging.getLogger(__name__)


def _get_smtp_connection() -> smtplib.SMTP:
    """Create and return an authenticated SMTP connection."""
    server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
    server.ehlo()
    server.starttls()  # Upgrade to TLS
    server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
    return server


def send_email(
    to_email: str,
    subject: str,
    html_body: str,
    plain_body: str = "",
) -> bool:
    """
    Send an HTML email to a single recipient.
    Returns True on success, False on failure.
    """
    if not settings.SMTP_USERNAME or not settings.SMTP_PASSWORD:
        logger.warning("SMTP credentials not configured. Skipping email.")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        msg["To"] = to_email

        # Attach plain text fallback first, then HTML
        if plain_body:
            msg.attach(MIMEText(plain_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        with _get_smtp_connection() as server:
            server.sendmail(settings.SMTP_FROM_EMAIL, to_email, msg.as_string())

        logger.info(f"Email sent to {to_email}: {subject}")
        return True

    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False


def send_otp_email(to_email: str, username: str, otp_code: str) -> bool:
    """Send a registration OTP verification email."""
    subject = "Verify Your Email - AI News Aggregator"
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: 'Segoe UI', sans-serif; background: #0f0f1a; color: #e2e8f0; padding: 40px;">
      <div style="max-width: 500px; margin: 0 auto; background: #1a1a2e; border-radius: 16px;
                  padding: 40px; border: 1px solid #2d2d4e;">
        <h1 style="color: #6ee7f7; margin-bottom: 8px; font-size: 24px;">
          📰 AI News Aggregator
        </h1>
        <p style="color: #94a3b8; margin-bottom: 32px;">Email Verification</p>

        <p style="font-size: 16px;">Hi <strong>{username}</strong>,</p>
        <p style="color: #94a3b8;">Use the code below to verify your email address.
           This code expires in <strong>{settings.OTP_EXPIRE_MINUTES} minutes</strong>.</p>

        <div style="text-align: center; margin: 32px 0;">
          <div style="display: inline-block; background: linear-gradient(135deg, #6ee7f7, #818cf8);
                      padding: 20px 40px; border-radius: 12px; font-size: 36px;
                      font-weight: 900; letter-spacing: 8px; color: #0f0f1a;">
            {otp_code}
          </div>
        </div>

        <p style="color: #64748b; font-size: 13px;">
          If you didn't request this, you can safely ignore this email.
        </p>
      </div>
    </body>
    </html>
    """
    plain_body = f"Your OTP code is: {otp_code}. Expires in {settings.OTP_EXPIRE_MINUTES} minutes."
    return send_email(to_email, subject, html_body, plain_body)


def send_daily_digest(
    to_email: str,
    username: str,
    trending_articles: List[dict],
    personalized_articles: List[dict],
) -> bool:
    """
    Send the daily news digest email with trending and personalized articles.
    Each article dict has: title, url, source, sentiment, summary.
    """
    subject = "📰 Your Daily News Digest - AI News Aggregator"

    def article_card(article: dict, idx: int) -> str:
        """Build HTML card for a single article."""
        sentiment_color = {
            "positive": "#22c55e",
            "negative": "#ef4444",
            "neutral": "#94a3b8",
        }.get(article.get("sentiment", "neutral"), "#94a3b8")

        return f"""
        <div style="background: #16213e; border-radius: 10px; padding: 20px;
                    margin-bottom: 16px; border-left: 3px solid {sentiment_color};">
          <p style="color: #94a3b8; font-size: 12px; margin: 0 0 6px 0;">
            #{idx + 1} · {article.get('source', 'Unknown')}
            <span style="color: {sentiment_color}; margin-left: 8px;">
              ● {article.get('sentiment', 'neutral').capitalize()}
            </span>
          </p>
          <a href="{article.get('url', '#')}"
             style="color: #6ee7f7; font-size: 16px; font-weight: 600; text-decoration: none;">
            {article.get('title', 'Untitled')}
          </a>
          <p style="color: #94a3b8; font-size: 13px; margin-top: 8px;">
            {article.get('summary', article.get('description', ''))[:200]}...
          </p>
        </div>
        """

    trending_html = "".join(
        article_card(a, i) for i, a in enumerate(trending_articles[:5])
    )
    personalized_html = (
        "".join(article_card(a, i) for i, a in enumerate(personalized_articles[:5]))
        if personalized_articles
        else "<p style='color:#64748b'>No personalized articles yet. Set your preferences on the dashboard.</p>"
    )

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: 'Segoe UI', sans-serif; background: #0f0f1a; color: #e2e8f0; padding: 40px;">
      <div style="max-width: 640px; margin: 0 auto;">

        <div style="background: linear-gradient(135deg, #1a1a2e, #16213e);
                    border-radius: 16px; padding: 32px; margin-bottom: 24px;
                    border: 1px solid #2d2d4e;">
          <h1 style="color: #6ee7f7; margin: 0 0 4px 0;">📰 Daily News Digest</h1>
          <p style="color: #94a3b8; margin: 0;">Good morning, <strong>{username}</strong>!</p>
        </div>

        <h2 style="color: #818cf8; margin-bottom: 16px;">🔥 Top Trending Today</h2>
        {trending_html}

        <h2 style="color: #818cf8; margin: 32px 0 16px 0;">⭐ For You</h2>
        {personalized_html}

        <p style="text-align: center; color: #475569; font-size: 12px; margin-top: 32px;">
          AI News Aggregator · <a href="#" style="color:#6ee7f7">Manage Preferences</a>
        </p>
      </div>
    </body>
    </html>
    """

    return send_email(to_email, subject, html_body)
