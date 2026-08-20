"""
services/email_service.py

Handles all outgoing emails:
- OTP verification
- Password reset
- Daily news digest

Email providers:
1. Resend (primary)
2. Gmail SMTP (fallback)
"""

import logging
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List

import resend

from app.config import settings


logger = logging.getLogger(__name__)


# ============================================================
# RESEND
# ============================================================

def _send_with_resend(
    to_email: str,
    subject: str,
    html_body: str,
    text_body: str = "",
) -> bool:
    """
    Send email using Resend.
    """

    # Check API key
    if not settings.resend_api_key:
        logger.warning(
            "RESEND_API_KEY is not configured."
        )
        return False

    # Resend needs a valid sender address
    if not settings.smtp_from_email:
        logger.error(
            "SMTP_FROM_EMAIL is not configured. "
            "Set SMTP_FROM_EMAIL to a verified sender email/domain in Resend."
        )
        return False

    try:
        resend.api_key = settings.resend_api_key

        sender = (
            f"{settings.smtp_from_name} "
            f"<{settings.smtp_from_email}>"
        )

        response = resend.Emails.send(
            {
                "from": sender,
                "to": [to_email],
                "subject": subject,
                "html": html_body,
                "text": text_body or "",
            }
        )

        logger.info(
            "✅ Resend email sent successfully. "
            "To=%s Subject=%s Response=%s",
            to_email,
            subject,
            response,
        )

        return True

    except Exception as exc:
        logger.exception(
            "❌ Resend failed. To=%s Subject=%s Error=%s",
            to_email,
            subject,
            exc,
        )

        return False


# ============================================================
# SMTP
# ============================================================

def _send_with_smtp(
    to_email: str,
    subject: str,
    html_body: str,
    text_body: str = "",
) -> bool:
    """
    Send email using SMTP.

    Recommended for Gmail:
    SMTP_HOST=smtp.gmail.com
    SMTP_PORT=587
    SMTP_USERNAME=your@gmail.com
    SMTP_PASSWORD=your Gmail App Password
    SMTP_FROM_EMAIL=your@gmail.com
    """

    if not settings.smtp_username:
        logger.warning(
            "SMTP_USERNAME is not configured."
        )
        return False

    if not settings.smtp_password:
        logger.warning(
            "SMTP_PASSWORD is not configured."
        )
        return False

    if not settings.smtp_from_email:
        logger.warning(
            "SMTP_FROM_EMAIL is not configured."
        )
        return False

    try:

        message = MIMEMultipart("alternative")

        message["Subject"] = subject

        message["From"] = (
            f"{settings.smtp_from_name} "
            f"<{settings.smtp_from_email}>"
        )

        message["To"] = to_email

        # Plain text version
        if text_body:
            message.attach(
                MIMEText(
                    text_body,
                    "plain",
                    "utf-8",
                )
            )

        # HTML version
        message.attach(
            MIMEText(
                html_body,
                "html",
                "utf-8",
            )
        )

        with smtplib.SMTP(
            settings.smtp_host,
            settings.smtp_port,
            timeout=30,
        ) as server:

            server.ehlo()

            server.starttls()

            server.ehlo()

            server.login(
                settings.smtp_username,
                settings.smtp_password,
            )

            server.sendmail(
                settings.smtp_from_email,
                [to_email],
                message.as_string(),
            )

        logger.info(
            "✅ SMTP email sent successfully. "
            "To=%s Subject=%s",
            to_email,
            subject,
        )

        return True

    except Exception as exc:

        logger.exception(
            "❌ SMTP email failed. "
            "To=%s Subject=%s Error=%s",
            to_email,
            subject,
            exc,
        )

        return False


# ============================================================
# GENERAL EMAIL FUNCTION
# ============================================================

def send_email(
    to_email: str,
    subject: str,
    html_body: str,
    text_body: str = "",
) -> bool:
    """
    Send an email.

    Order:
        1. Resend
        2. SMTP

    Returns:
        True  = email successfully submitted
        False = all configured providers failed
    """

    logger.info(
        "📧 Attempting to send email to %s | Subject=%s",
        to_email,
        subject,
    )

    # --------------------------------------------------------
    # Try Resend first
    # --------------------------------------------------------

    if settings.resend_api_key:

        logger.info(
            "Trying Resend..."
        )

        if _send_with_resend(
            to_email,
            subject,
            html_body,
            text_body,
        ):
            return True

        logger.warning(
            "Resend failed. Trying SMTP fallback..."
        )

    else:

        logger.info(
            "Resend is not configured."
        )

    # --------------------------------------------------------
    # Try SMTP
    # --------------------------------------------------------

    if _send_with_smtp(
        to_email,
        subject,
        html_body,
        text_body,
    ):
        return True

    # --------------------------------------------------------
    # Everything failed
    # --------------------------------------------------------

    logger.error(
        "❌ ALL EMAIL PROVIDERS FAILED.\n"
        "Recipient: %s\n"
        "Subject: %s",
        to_email,
        subject,
    )

    return False


# ============================================================
# OTP EMAIL
# ============================================================

def send_otp_email(
    email: str,
    otp_code: str,
    username: str = "User",
) -> bool:

    subject = (
        f"Your Verification Code - "
        f"{settings.app_name}"
    )

    html_body = f"""
<!DOCTYPE html>
<html>

<head>
    <meta charset="UTF-8">
    <title>Email Verification</title>
</head>

<body style="
    margin:0;
    padding:40px 20px;
    background:#f6f8fc;
    font-family:Arial,Helvetica,sans-serif;
">

<div style="
    max-width:500px;
    margin:auto;
    background:#ffffff;
    border-radius:16px;
    padding:40px;
    border:1px solid #dbeafe;
">

    <h1 style="
        margin:0 0 20px;
        color:#2563eb;
        font-size:28px;
    ">
        🔐 Verify Your Email
    </h1>

    <p style="
        color:#475569;
        font-size:16px;
    ">
        Hi <strong>{username}</strong>,
    </p>

    <p style="
        color:#475569;
        line-height:1.6;
    ">
        Thank you for registering with
        <strong>{settings.app_name}</strong>.
    </p>

    <p style="
        color:#475569;
        line-height:1.6;
    ">
        Your verification code is:
    </p>

    <div style="
        background:#eff6ff;
        border:2px solid #2563eb;
        border-radius:12px;
        padding:22px;
        text-align:center;
        margin:25px 0;
    ">

        <span style="
            font-size:36px;
            font-weight:bold;
            color:#2563eb;
            letter-spacing:8px;
        ">
            {otp_code}
        </span>

    </div>

    <p style="
        color:#475569;
        line-height:1.6;
    ">
        This verification code expires in
        <strong>{settings.otp_expire_minutes} minutes</strong>.
    </p>

    <p style="
        color:#64748b;
        font-size:14px;
    ">
        If you did not request this verification code,
        you can safely ignore this email.
    </p>

    <hr style="
        border:0;
        border-top:1px solid #e2e8f0;
        margin:30px 0;
    ">

    <p style="
        color:#94a3b8;
        font-size:12px;
        text-align:center;
    ">
        © {datetime.now().year} {settings.app_name}
    </p>

</div>

</body>
</html>
"""

    text_body = (
        f"Hi {username},\n\n"
        f"Your verification code is: {otp_code}\n\n"
        f"This code expires in "
        f"{settings.otp_expire_minutes} minutes.\n\n"
        f"If you did not request this code, "
        f"you can safely ignore this email."
    )

    return send_email(
        email,
        subject,
        html_body,
        text_body,
    )


# ============================================================
# PASSWORD RESET EMAIL
# ============================================================

def send_password_reset_email(
    email: str,
    username: str,
    reset_url: str,
) -> bool:

    subject = (
        f"Reset Your Password - "
        f"{settings.app_name}"
    )

    html_body = f"""
<!DOCTYPE html>
<html>

<head>
    <meta charset="UTF-8">
    <title>Reset Password</title>
</head>

<body style="
    margin:0;
    padding:40px 20px;
    background:#f5f7fb;
    font-family:Arial,Helvetica,sans-serif;
">

<div style="
    max-width:520px;
    margin:auto;
    background:#ffffff;
    border-radius:16px;
    padding:40px;
    border:1px solid #e5e7eb;
">

    <h1 style="
        color:#0284c7;
        margin-bottom:20px;
    ">
        🔑 Reset Your Password
    </h1>

    <p style="color:#475569;">
        Hi <strong>{username}</strong>,
    </p>

    <p style="
        color:#475569;
        line-height:1.6;
    ">
        We received a request to reset your
        <strong>{settings.app_name}</strong>
        password.
    </p>

    <p style="
        color:#475569;
        line-height:1.6;
    ">
        Click the button below to create a new password.
    </p>

    <div style="
        text-align:center;
        margin:30px 0;
    ">

        <a href="{reset_url}"
           style="
           display:inline-block;
           background:#0284c7;
           color:#ffffff;
           text-decoration:none;
           padding:14px 26px;
           border-radius:10px;
           font-weight:bold;
           ">
            Reset Password
        </a>

    </div>

    <p style="
        color:#64748b;
        font-size:13px;
        line-height:1.6;
    ">
        This reset link expires in
        <strong>
            {settings.password_reset_expire_minutes}
            minutes
        </strong>
        and can only be used once.
    </p>

    <p style="
        color:#94a3b8;
        font-size:12px;
    ">
        If you did not request a password reset,
        you can safely ignore this email.
    </p>

    <hr style="
        border:0;
        border-top:1px solid #e5e7eb;
        margin:30px 0;
    ">

    <p style="
        color:#94a3b8;
        font-size:12px;
        text-align:center;
    ">
        © {datetime.now().year} {settings.app_name}
    </p>

</div>

</body>
</html>
"""

    text_body = (
        f"Hi {username},\n\n"
        f"Reset your password using this link:\n"
        f"{reset_url}\n\n"
        f"This link expires in "
        f"{settings.password_reset_expire_minutes} minutes "
        f"and can only be used once."
    )

    return send_email(
        email,
        subject,
        html_body,
        text_body,
    )


# ============================================================
# DAILY NEWS DIGEST
# ============================================================

def send_daily_digest(
    email: str,
    username: str,
    trending_articles: List[dict],
    personalized_articles: List[dict],
) -> bool:

    subject = (
        f"📰 Your Daily News Digest - "
        f"{datetime.now().strftime('%B %d, %Y')}"
    )

    def article_html(
        article: dict,
        index: int,
    ) -> str:

        sentiment = article.get(
            "sentiment",
            "Neutral",
        )

        sentiment_color = {
            "Positive": "#00c853",
            "Negative": "#ff5252",
            "Neutral": "#9e9e9e",
        }.get(
            sentiment,
            "#9e9e9e",
        )

        title = article.get(
            "title",
            "Untitled",
        )

        url = article.get(
            "url",
            "#",
        )

        summary = article.get(
            "summary",
            "",
        )

        source = article.get(
            "source",
            "Unknown",
        )

        category = article.get(
            "category",
            "General",
        )

        return f"""
<div style="
    background:#16213e;
    border-radius:10px;
    padding:18px;
    margin-bottom:15px;
    border-left:4px solid #2563eb;
">

    <div style="
        margin-bottom:10px;
    ">

        <span style="
            color:#60a5fa;
            font-weight:bold;
        ">
            #{index}
        </span>

        <span style="
            background:{sentiment_color}22;
            color:{sentiment_color};
            padding:4px 9px;
            border-radius:10px;
            font-size:12px;
            margin-left:8px;
        ">
            {sentiment}
        </span>

    </div>

    <h3 style="
        margin:0 0 10px;
        font-size:16px;
    ">

        <a href="{url}"
           style="
           color:#ffffff;
           text-decoration:none;
           ">
            {title}
        </a>

    </h3>

    <p style="
        color:#cbd5e1;
        font-size:13px;
        line-height:1.5;
    ">
        {summary[:250]}
    </p>

    <p style="
        color:#94a3b8;
        font-size:11px;
    ">
        📰 {source}
        &nbsp; | &nbsp;
        📂 {category}
    </p>

</div>
"""

    trending_html = "".join(
        article_html(
            article,
            index + 1,
        )
        for index, article in enumerate(
            trending_articles[:5]
        )
    )

    personalized_html = "".join(
        article_html(
            article,
            index + 1,
        )
        for index, article in enumerate(
            personalized_articles[:5]
        )
    )

    if not trending_html:
        trending_html = """
        <p style="color:#64748b;">
            No trending articles available today.
        </p>
        """

    if not personalized_html:
        personalized_html = """
        <p style="color:#64748b;">
            Set your preferences to receive
            personalized news.
        </p>
        """

    html_body = f"""
<!DOCTYPE html>
<html>

<head>
    <meta charset="UTF-8">
    <title>Daily News Digest</title>
</head>

<body style="
    margin:0;
    padding:40px 20px;
    background:#f6f8fc;
    font-family:Arial,Helvetica,sans-serif;
">

<div style="
    max-width:600px;
    margin:auto;
    background:#ffffff;
    border-radius:16px;
    padding:40px;
    border:1px solid #dbeafe;
">

    <h1 style="
        color:#2563eb;
    ">
        📰 Daily News Digest
    </h1>

    <p style="
        color:#475569;
        line-height:1.6;
    ">
        Good morning,
        <strong>{username}</strong>!
    </p>

    <p style="
        color:#475569;
    ">
        Here is your personalized news digest.
    </p>

    <h2 style="
        color:#f59e0b;
        border-bottom:1px solid #fde68a;
        padding-bottom:10px;
    ">
        🔥 Trending Now
    </h2>

    {trending_html}

    <h2 style="
        color:#2563eb;
        border-bottom:1px solid #bfdbfe;
        padding-bottom:10px;
        margin-top:35px;
    ">
        ⭐ For You
    </h2>

    {personalized_html}

    <hr style="
        border:0;
        border-top:1px solid #e2e8f0;
        margin:30px 0;
    ">

    <p style="
        color:#94a3b8;
        font-size:12px;
        text-align:center;
    ">
        © {datetime.now().year} {settings.app_name}
    </p>

</div>

</body>
</html>
"""

    return send_email(
        email,
        subject,
        html_body,
    )