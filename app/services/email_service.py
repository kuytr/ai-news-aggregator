"""
services/email_service.py - Email Service

Handles all outgoing emails: OTP verification, daily digest.
Uses Resend API instead of SMTP.
"""

import resend
import logging
from typing import List
from datetime import datetime

from app.config import settings

logger = logging.getLogger(__name__)


def send_email(to_email: str, subject: str, html_body: str, text_body: str = "") -> bool:
    """
    Send an email using Resend API.
    
    Returns:
        True if sent successfully, False otherwise
    """
    if not settings.resend_api_key:
        logger.warning("Resend API key not configured. Email not sent.")
        return False

    try:
        resend.api_key = settings.resend_api_key
        resend.Emails.send({
            "from": f"{settings.smtp_from_name} <onboarding@resend.dev>",
            "to": to_email,
            "subject": subject,
            "html": html_body,
        })
        logger.info(f"Email sent to {to_email}: {subject}")
        return True

    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False


def send_otp_email(email: str, otp_code: str, username: str = "User") -> bool:
    subject = f"Your Verification Code - {settings.app_name}"

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: Arial, sans-serif; background: #0f0f1a; color: #e0e0e0; padding: 40px;">
        <div style="max-width: 500px; margin: 0 auto; background: #1a1a2e; border-radius: 12px; padding: 40px; border: 1px solid #00d4ff33;">
            <h1 style="color: #00d4ff; margin-bottom: 8px;">🔐 Verify Your Email</h1>
            <p style="color: #a0a0b0;">Hi <strong>{username}</strong>,</p>
            <p style="color: #a0a0b0;">Your one-time verification code is:</p>
            <div style="background: #16213e; border: 2px solid #00d4ff; border-radius: 8px; padding: 20px; text-align: center; margin: 20px 0;">
                <span style="font-size: 36px; font-weight: bold; color: #00d4ff; letter-spacing: 8px;">{otp_code}</span>
            </div>
            <p style="color: #a0a0b0;">This code expires in <strong>{settings.otp_expire_minutes} minutes</strong>.</p>
            <p style="color: #a0a0b0;">If you didn't request this, please ignore this email.</p>
            <hr style="border-color: #00d4ff33; margin: 20px 0;">
            <p style="color: #606070; font-size: 12px;">© {datetime.now().year} {settings.app_name}</p>
        </div>
    </body>
    </html>
    """

    text_body = f"Hi {username},\n\nYour OTP code is: {otp_code}\n\nExpires in {settings.otp_expire_minutes} minutes."
    return send_email(email, subject, html_body, text_body)


def send_daily_digest(
    email: str,
    username: str,
    trending_articles: List[dict],
    personalized_articles: List[dict]
) -> bool:
    subject = f"📰 Your Daily News Digest - {datetime.now().strftime('%B %d, %Y')}"

    def article_html(art: dict, idx: int) -> str:
        sentiment_color = {
            "Positive": "#00c853",
            "Negative": "#ff5252",
            "Neutral": "#9e9e9e"
        }.get(art.get("sentiment", "Neutral"), "#9e9e9e")

        return f"""
        <div style="background: #16213e; border-radius: 8px; padding: 16px; margin-bottom: 12px; border-left: 3px solid #00d4ff;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span style="color: #00d4ff; font-weight: bold;">#{idx}</span>
                <span style="background: {sentiment_color}22; color: {sentiment_color}; padding: 2px 8px; border-radius: 10px; font-size: 12px;">{art.get('sentiment', 'Neutral')}</span>
            </div>
            <h3 style="color: #e0e0e0; margin: 0 0 8px 0; font-size: 15px;">
                <a href="{art.get('url', '#')}" style="color: #e0e0e0; text-decoration: none;">{art.get('title', 'Untitled')}</a>
            </h3>
            <p style="color: #8080a0; font-size: 13px; margin: 0;">{art.get('summary', '')[:200]}...</p>
            <p style="color: #606070; font-size: 11px; margin: 8px 0 0 0;">📰 {art.get('source', 'Unknown')} | 📂 {art.get('category', 'General')}</p>
        </div>
        """

    trending_html = "".join(article_html(a, i + 1) for i, a in enumerate(trending_articles[:5]))
    personalized_html = "".join(article_html(a, i + 1) for i, a in enumerate(personalized_articles[:5]))

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: Arial, sans-serif; background: #0f0f1a; color: #e0e0e0; padding: 40px;">
        <div style="max-width: 600px; margin: 0 auto; background: #1a1a2e; border-radius: 12px; padding: 40px; border: 1px solid #00d4ff33;">
            <h1 style="color: #00d4ff;">📰 Daily News Digest</h1>
            <p style="color: #a0a0b0;">Good morning, <strong>{username}</strong>! Here's your personalized news for today.</p>

            <h2 style="color: #ff9800; border-bottom: 1px solid #ff980033; padding-bottom: 8px;">🔥 Trending Now</h2>
            {trending_html if trending_html else '<p style="color: #606070;">No trending articles today.</p>'}

            <h2 style="color: #00d4ff; border-bottom: 1px solid #00d4ff33; padding-bottom: 8px; margin-top: 30px;">⭐ For You</h2>
            {personalized_html if personalized_html else '<p style="color: #606070;">Set your preferences to get personalized news.</p>'}

            <hr style="border-color: #00d4ff22; margin: 30px 0;">
            <p style="color: #606070; font-size: 12px; text-align: center;">
                © {datetime.now().year} {settings.app_name} | 
                <a href="#" style="color: #00d4ff;">Manage Preferences</a>
            </p>
        </div>
    </body>
    </html>
    """

    return send_email(email, subject, html_body)