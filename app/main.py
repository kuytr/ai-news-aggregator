"""
main.py - FastAPI Application Entry Point

Initializes the app, registers routers, mounts static files,
sets up templating, and starts the scheduler.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.routers import auth_router, news_router, api_router
from app.services.scheduler_service import start_scheduler, stop_scheduler

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting AI News Aggregator...")

    # Initialize database tables
    init_db()
    logger.info("✅ Database initialized.")

    # Start background scheduler
    start_scheduler()
    logger.info("✅ Scheduler started.")

    # Do an immediate first fetch on startup
    try:
        from app.database import SessionLocal
        from app.services.news_fetcher import fetch_all_news
        db = SessionLocal()
        count = fetch_all_news(db)
        db.close()
        logger.info(f"✅ Initial news fetch complete: {count} articles.")
    except Exception as e:
        logger.error(f"⚠️ Initial news fetch failed: {e}")

    yield  # App is running

    # Shutdown
    stop_scheduler()
    logger.info("🛑 Scheduler stopped. Goodbye!")


# Create FastAPI app instance
app = FastAPI(
    title=settings.app_name,
    description="AI-powered News Aggregator with personalization",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Jinja2 template engine
templates = Jinja2Templates(directory="app/templates")

# Register routers
app.include_router(auth_router.router)
app.include_router(news_router.router)
app.include_router(api_router.router)


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return templates.TemplateResponse(
        "404.html", {"request": request}, status_code=404
    )


@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    logger.error(f"500 error: {exc}")
    return templates.TemplateResponse(
        "500.html", {"request": request}, status_code=500
    )