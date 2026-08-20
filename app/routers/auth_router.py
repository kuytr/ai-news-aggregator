"""
routers/auth_router.py - Authentication Routes

Handles user registration, OTP verification, login, and logout.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import get_db
from app.config import settings
from app.models.user import User
from app.schemas.user import UserRegister, UserLogin, OTPVerify, TokenResponse
from app.services.auth_service import hash_password, authenticate_user, create_access_token
from app.services.otp_service import create_otp, verify_otp
from app.services.email_service import send_otp_email, send_password_reset_email
from app.dependencies import get_current_user_optional
from app.services.password_reset_service import (
    create_password_reset_token,
    get_valid_reset_token,
    reset_user_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, user=Depends(get_current_user_optional)):
    """Render registration page."""
    if user:
        return RedirectResponse("/dashboard", status_code=302)
    return templates.TemplateResponse("auth/register.html", {"request": request})


@router.post("/register")
async def register(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    """Handle user registration form submission."""
    errors = []

    # Validate inputs
    if len(username) < 3:
        errors.append("Username must be at least 3 characters.")
    if len(password) < 6:
        errors.append("Password must be at least 6 characters.")

    # Check if email already exists
    if db.query(User).filter(User.email == email).first():
        errors.append("Email already registered.")

    # Check if username already exists
    if db.query(User).filter(User.username == username).first():
        errors.append("Username already taken.")

    if errors:
        return templates.TemplateResponse(
            "auth/register.html",
            {"request": request, "errors": errors, "username": username, "email": email},
            status_code=400,
        )

    # Create user (not yet verified)
    new_user = User(
        username=username.strip(),
        email=email.strip().lower(),
        hashed_password=hash_password(password),
        is_verified=False,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Generate and send OTP
    otp_code = create_otp(db, email=new_user.email, user_id=new_user.id)
    send_otp_email(email=new_user.email, otp_code=otp_code, username=new_user.username)

    # Redirect to OTP verification page
    return RedirectResponse(f"/auth/verify-otp?email={new_user.email}", status_code=302)


@router.get("/verify-otp", response_class=HTMLResponse)
async def verify_otp_page(request: Request, email: str = ""):
    """Render OTP verification page."""
    return templates.TemplateResponse("auth/verify_otp.html", {"request": request, "email": email})


@router.post("/verify-otp")
async def verify_otp_submit(
    request: Request,
    email: str = Form(...),
    otp: str = Form(...),
    db: Session = Depends(get_db),
):
    """Handle OTP verification form submission."""
    is_valid = verify_otp(db, email=email, code=otp.strip())

    if not is_valid:
        return templates.TemplateResponse(
            "auth/verify_otp.html",
            {"request": request, "email": email, "error": "Invalid or expired OTP. Please try again."},
            status_code=400,
        )

    # Activate user account
    user = db.query(User).filter(User.email == email).first()
    if user:
        user.is_verified = True
        db.commit()

    return templates.TemplateResponse(
        "auth/verify_otp.html",
        {"request": request, "email": email, "success": "Email verified! You can now log in."},
    )


@router.post("/resend-otp")
async def resend_otp(email: str = Form(...), db: Session = Depends(get_db)):
    """Resend OTP to user email."""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    otp_code = create_otp(db, email=email, user_id=user.id)
    send_otp_email(email=email, otp_code=otp_code, username=user.username)
    return {"message": "OTP resent successfully"}


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, user=Depends(get_current_user_optional)):
    """Render login page."""
    if user:
        return RedirectResponse("/dashboard", status_code=302)
    return templates.TemplateResponse("auth/login.html", {"request": request})


@router.post("/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    """Handle login form submission."""
    user = authenticate_user(db, email=email, password=password)

    if not user:
        # Check if user exists but not verified
        raw_user = db.query(User).filter(User.email == email).first()
        if raw_user and not raw_user.is_verified:
            return templates.TemplateResponse(
                "auth/login.html",
                {"request": request, "error": "Please verify your email first.", "email": email},
                status_code=400,
            )
        return templates.TemplateResponse(
            "auth/login.html",
            {"request": request, "error": "Invalid email or password.", "email": email},
            status_code=400,
        )

    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()

    # Create JWT token
    token = create_access_token(data={"sub": user.email})

    # Set cookie and redirect to dashboard
    response = RedirectResponse("/dashboard", status_code=302)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,  # Prevent JS access (XSS protection)
        max_age=86400,  # 24 hours
        samesite="lax",
    )
    return response



@router.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(request: Request):
    """Render forgot-password page."""
    return templates.TemplateResponse("auth/forgot_password.html", {"request": request})


@router.post("/forgot-password")
async def forgot_password(
    request: Request,
    email: str = Form(...),
    db: Session = Depends(get_db),
):
    """Send a password reset link without revealing whether an email exists."""
    normalized_email = email.strip().lower()
    user = db.query(User).filter(User.email == normalized_email).first()

    if user and user.is_active and user.is_verified:
        raw_token = create_password_reset_token(db, user)
        reset_url = f"{settings.app_base_url.rstrip('/')}/auth/reset-password?token={raw_token}"
        if not send_password_reset_email(user.email, user.username, reset_url):
            # Do not expose email-provider details to the user. Log the failure server-side.
            import logging
            logging.getLogger(__name__).error("Password reset email could not be sent to %s", user.email)

    return templates.TemplateResponse(
        "auth/forgot_password.html",
        {"request": request, "success": "If an account exists for that email, a password reset link has been sent."},
    )


@router.get("/reset-password", response_class=HTMLResponse)
async def reset_password_page(request: Request, token: str = "", db: Session = Depends(get_db)):
    """Render the reset-password form if the token is valid."""
    valid_token = get_valid_reset_token(db, token) if token else None
    if not valid_token:
        return templates.TemplateResponse(
            "auth/reset_password.html",
            {"request": request, "error": "This password reset link is invalid or has expired.", "token": ""},
            status_code=400,
        )
    return templates.TemplateResponse("auth/reset_password.html", {"request": request, "token": token})


@router.post("/reset-password")
async def reset_password(
    request: Request,
    token: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db),
):
    """Validate reset token and update the user's password."""
    valid_token = get_valid_reset_token(db, token)
    if not valid_token:
        return templates.TemplateResponse(
            "auth/reset_password.html",
            {"request": request, "error": "This password reset link is invalid or has expired.", "token": ""},
            status_code=400,
        )

    if len(password) < 8:
        return templates.TemplateResponse(
            "auth/reset_password.html",
            {"request": request, "error": "Password must be at least 8 characters.", "token": token},
            status_code=400,
        )

    if password != confirm_password:
        return templates.TemplateResponse(
            "auth/reset_password.html",
            {"request": request, "error": "Passwords do not match.", "token": token},
            status_code=400,
        )

    reset_user_password(db, valid_token, password)
    return templates.TemplateResponse(
        "auth/reset_password.html",
        {"request": request, "success": "Password updated successfully. You can now log in.", "token": ""},
    )

@router.get("/logout")
async def logout():
    """Clear auth cookie and redirect to home."""
    response = RedirectResponse("/", status_code=302)
    response.delete_cookie("access_token")
    return response
