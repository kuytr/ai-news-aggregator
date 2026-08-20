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


def _send_with_smtp(to_email: str, subject: str, html_body: str, text_body: str = "") -> bool:
    """Send using the SMTP credentials already supported by the project."""
    if not settings.smtp_username or not settings.smtp_password or not settings.smtp_from_email:
        return False

    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
        msg["To"] = to_email
        if text_body:
            msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(settings.smtp_username, settings.smtp_password)
            server.sendmail(settings.smtp_from_email, to_email, msg.as_string())
        logger.info("Email sent via SMTP to %s: %s", to_email, subject)
        return True
    except Exception as exc:
        logger.exception("SMTP email failed for %s: %s", to_email, exc)
        return False


def send_email(to_email: str, subject: str, html_body: str, text_body: str = "") -> bool:
    """Send email using Resend first, then SMTP as a reliable fallback."""
    if settings.resend_api_key:
        try:
            resend.api_key = settings.resend_api_key
            sender_email = settings.smtp_from_email or "onboarding@resend.dev"
            resend.Emails.send({
                "from": f"{settings.smtp_from_name} <{sender_email}>",
                "to": to_email,
                "subject": subject,
                "html": html_body,
                "text": text_body or None,
            })
            logger.info("Email sent via Resend to %s: %s", to_email, subject)
            return True
        except Exception as exc:
            logger.warning("Resend email failed; trying SMTP fallback: %s", exc)

    if _send_with_smtp(to_email, subject, html_body, text_body):
        return True

    logger.error("All configured email providers failed for %s: %s", to_email, subject)
    return False

def send_otp_email(email: str, otp_code: str, username: str = "User") -> bool:
    subject = f"Your Verification Code - {settings.app_name}"

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: Arial, sans-serif; background: #f6f8fc; color: #172033; padding: 40px;">
        <div style="max-width: 500px; margin: 0 auto; background: #ffffff; border-radius: 12px; padding: 40px; border: 1px solid #dbeafe;">
            <h1 style="color: #2563eb; margin-bottom: 8px;">🔐 Verify Your Email</h1>
            <p style="color: #526071;">Hi <strong>{username}</strong>,</p>
            <p style="color: #526071;">Your one-time verification code is:</p>
            <div style="background: #eff6ff; border: 2px solid #2563eb; border-radius: 8px; padding: 20px; text-align: center; margin: 20px 0;">
                <span style="font-size: 36px; font-weight: bold; color: #2563eb; letter-spacing: 8px;">{otp_code}</span>
            </div>
            <p style="color: #526071;">This code expires in <strong>{settings.otp_expire_minutes} minutes</strong>.</p>
            <p style="color: #526071;">If you didn't request this, please ignore this email.</p>
            <hr style="border-color: #00d4ff33; margin: 20px 0;">
            <p style="color: #7b8794; font-size: 12px;">© {datetime.now().year} {settings.app_name}</p>
        </div>
    </body>
    </html>
    """

    text_body = f"Hi {username},\n\nYour OTP code is: {otp_code}\n\nExpires in {settings.otp_expire_minutes} minutes."
    return send_email(email, subject, html_body, text_body)



def send_password_reset_email(email: str, username: str, reset_url: str) -> bool:
    subject = f"Reset Your Password - {settings.app_name}"
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: Arial, sans-serif; background: #f5f7fb; color: #1f2937; padding: 40px;">
        <div style="max-width: 520px; margin: 0 auto; background: #ffffff; border-radius: 16px; padding: 40px; border: 1px solid #e5e7eb; box-shadow: 0 8px 30px rgba(15,23,42,.08);">
            <h1 style="color: #0284c7; margin-bottom: 8px;">Reset Your Password</h1>
            <p style="color: #64748b;">Hi <strong>{username}</strong>,</p>
            <p style="color: #64748b; line-height: 1.6;">We received a request to reset your {settings.app_name} password. Click the button below to choose a new password.</p>
            <div style="text-align:center; margin: 28px 0;">
                <a href="{reset_url}" style="display:inline-block; background:#0284c7; color:#ffffff; text-decoration:none; padding:13px 24px; border-radius:9px; font-weight:700;">Reset Password</a>
            </div>
            <p style="color: #64748b; font-size: 13px;">This link expires in <strong>{settings.password_reset_expire_minutes} minutes</strong> and can only be used once.</p>
            <p style="color: #94a3b8; font-size: 12px;">If you did not request this, you can safely ignore this email.</p>
            <hr style="border:0; border-top:1px solid #e5e7eb; margin:24px 0;">
            <p style="color:#94a3b8; font-size:12px; text-align:center;">© {datetime.now().year} {settings.app_name}</p>
        </div>
    </body>
    </html>
    """
    text_body = (
        f"Hi {username},\n\nReset your password here: {reset_url}\n\n"
        f"This link expires in {settings.password_reset_expire_minutes} minutes and can only be used once."
    )
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
                <span style="color: #2563eb; font-weight: bold;">#{idx}</span>
                <span style="background: {sentiment_color}22; color: {sentiment_color}; padding: 2px 8px; border-radius: 10px; font-size: 12px;">{art.get('sentiment', 'Neutral')}</span>
            </div>
            <h3 style="color: #e0e0e0; margin: 0 0 8px 0; font-size: 15px;">
                <a href="{art.get('url', '#')}" style="color: #e0e0e0; text-decoration: none;">{art.get('title', 'Untitled')}</a>
            </h3>
            <p style="color: #8080a0; font-size: 13px; margin: 0;">{art.get('summary', '')[:200]}...</p>
            <p style="color: #7b8794; font-size: 11px; margin: 8px 0 0 0;">📰 {art.get('source', 'Unknown')} | 📂 {art.get('category', 'General')}</p>
        </div>
        """

    trending_html = "".join(article_html(a, i + 1) for i, a in enumerate(trending_articles[:5]))
    personalized_html = "".join(article_html(a, i + 1) for i, a in enumerate(personalized_articles[:5]))

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: Arial, sans-serif; background: #f6f8fc; color: #172033; padding: 40px;">
        <div style="max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; padding: 40px; border: 1px solid #dbeafe;">
            <h1 style="color: #2563eb;">📰 Daily News Digest</h1>
            <p style="color: #526071;">Good morning, <strong>{username}</strong>! Here's your personalized news for today.</p>

            <h2 style="color: #ff9800; border-bottom: 1px solid #ff980033; padding-bottom: 8px;">🔥 Trending Now</h2>
            {trending_html if trending_html else '<p style="color: #7b8794;">No trending articles today.</p>'}

            <h2 style="color: #2563eb; border-bottom: 1px solid #00d4ff33; padding-bottom: 8px; margin-top: 30px;">⭐ For You</h2>
            {personalized_html if personalized_html else '<p style="color: #7b8794;">Set your preferences to get personalized news.</p>'}

            <hr style="border-color: #00d4ff22; margin: 30px 0;">
            <p style="color: #7b8794; font-size: 12px; text-align: center;">
                © {datetime.now().year} {settings.app_name} | 
                <a href="#" style="color: #2563eb;">Manage Preferences</a>
            </p>
        </div>
    </body>
    </html>
    """

    return send_email(email, subject, html_body)