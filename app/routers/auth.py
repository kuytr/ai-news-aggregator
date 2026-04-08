"""
routers/auth.py - Authentication endpoints: register, verify OTP, login, logout.
"""

from datetime import datetime
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.services.auth import hash_password, verify_password, create_access_token
from app.services.otp import create_otp, verify_otp
from app.services.email import send_otp_email
from app.dependencies import get_current_user_optional

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Render the registration form."""
    return templates.TemplateResponse(
        "auth/register.html",
        {"request": request, "error": None, "success": None},
    )


@router.post("/register")
async def register(
    request: Request,
    email: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    """Handle registration form submission."""
    # Validation
    if len(password) < 8:
        return templates.TemplateResponse(
            "auth/register.html",
            {"request": request, "error": "Password must be at least 8 characters.", "success": None},
        )

    # Check if email/username already taken
    if db.query(User).filter(User.email == email).first():
        return templates.TemplateResponse(
            "auth/register.html",
            {"request": request, "error": "Email already registered.", "success": None},
        )
    if db.query(User).filter(User.username == username).first():
        return templates.TemplateResponse(
            "auth/register.html",
            {"request": request, "error": "Username already taken.", "success": None},
        )

    # Create user (not verified yet)
    user = User(
        email=email,
        username=username.strip(),
        hashed_password=hash_password(password),
        is_verified=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Generate and email OTP
    otp_code = create_otp(db, user.id, purpose="registration")
    send_otp_email(email, username, otp_code)

    # Redirect to OTP verification page
    return RedirectResponse(
        url=f"/verify-otp?email={email}",
        status_code=303,
    )


@router.get("/verify-otp", response_class=HTMLResponse)
async def verify_otp_page(request: Request, email: str = ""):
    """Render OTP verification page."""
    return templates.TemplateResponse(
        "auth/verify_otp.html",
        {"request": request, "email": email, "error": None},
    )


@router.post("/verify-otp")
async def verify_otp_submit(
    request: Request,
    email: str = Form(...),
    otp: str = Form(...),
    db: Session = Depends(get_db),
):
    """Verify submitted OTP and activate user account."""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return templates.TemplateResponse(
            "auth/verify_otp.html",
            {"request": request, "email": email, "error": "User not found."},
        )

    if not verify_otp(db, user.id, otp.strip(), purpose="registration"):
        return templates.TemplateResponse(
            "auth/verify_otp.html",
            {"request": request, "email": email, "error": "Invalid or expired OTP."},
        )

    # Activate user account
    user.is_verified = True
    db.commit()

    return RedirectResponse(url="/login?verified=1", status_code=303)


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, verified: str = ""):
    """Render the login form."""
    success_msg = "Email verified! You can now log in." if verified == "1" else None
    return templates.TemplateResponse(
        "auth/login.html",
        {"request": request, "error": None, "success": success_msg},
    )


@router.post("/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    """Handle login form and set JWT cookie."""
    user = db.query(User).filter(User.email == email).first()

    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            "auth/login.html",
            {"request": request, "error": "Invalid email or password.", "success": None},
        )

    if not user.is_verified:
        return templates.TemplateResponse(
            "auth/login.html",
            {"request": request, "error": "Please verify your email first.", "success": None},
        )

    # Update last login timestamp
    user.last_login = datetime.utcnow()
    db.commit()

    # Create JWT and store in HTTP-only cookie
    token = create_access_token({"sub": str(user.id)})
    response = RedirectResponse(url="/dashboard", status_code=303)
    response.set_cookie(
        key="access_token",
        value=f"Bearer {token}",
        httponly=True,       # Not accessible via JS (XSS protection)
        max_age=86400,       # 24 hours
        samesite="lax",
    )
    return response


@router.get("/logout")
async def logout():
    """Clear the auth cookie and redirect to home."""
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("access_token")
    return response


@router.post("/resend-otp")
async def resend_otp(
    request: Request,
    email: str = Form(...),
    db: Session = Depends(get_db),
):
    """Resend OTP to user's email."""
    user = db.query(User).filter(User.email == email).first()
    if user and not user.is_verified:
        otp_code = create_otp(db, user.id, purpose="registration")
        send_otp_email(email, user.username, otp_code)

    return RedirectResponse(
        url=f"/verify-otp?email={email}&resent=1",
        status_code=303,
    )
