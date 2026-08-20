"""
config.py - Application Configuration
"""

from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List


class Settings(BaseSettings):

    # --- Application ---
    app_name: str = "AI News Aggregator"
    app_secret_key: str = "change-this-secret-key"
    debug: bool = False
    app_base_url: str = "http://localhost:8000"

    # --- Database ---
    database_url: str = "sqlite:///./news_aggregator.db"

    # --- JWT Authentication ---
    jwt_secret_key: str = "change-this-jwt-secret"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 1440

    # --- OpenAI ---
    openai_api_key: str = ""

    # --- NewsAPI ---
    newsapi_key: str = ""

    # --- Email (SMTP) ---
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    smtp_from_name: str = "AI News Aggregator"
    resend_api_key: str = ""

    # --- OTP ---
    otp_expire_minutes: int = 10
    password_reset_expire_minutes: int = 30

    # --- RSS Feeds ---
    rss_feeds: str = (
        # ========== IPL (Top Priority) ==========
        "https://www.iplt20.com/news/rss,"
        "https://www.espncricinfo.com/rss/content/story/feeds/6.xml,"
        "https://cricbuzz.com/rss-feeds/ipl-news,"
        "https://www.crictracker.com/category/ipl/feed/,"
        "https://feeds.feedburner.com/ndtvsports-ipl,"
        "https://timesofindia.indiatimes.com/sports/cricket/ipl/rssfeeds/4719148.cms,"
        "https://www.sportskeeda.com/ipl/feed,"
        "https://sportstar.thehindu.com/cricket/ipl/feed/,"
        "https://indianexpress.com/section/sports/ipl/feed/,"
        "https://www.hindustantimes.com/feeds/rss/ipl/rssfeed.xml,"
        # ========== CRICKET (Primary) ==========
        "https://www.espncricinfo.com/rss/content/story/feeds/0.xml,"
        "https://cricbuzz.com/rss-feeds/cricket-news,"
        "https://www.crictracker.com/feed/,"
        "https://feeds.feedburner.com/ndtvsports-cricket,"
        "https://www.thehindu.com/sport/cricket/feeder/default.rss,"
        "https://indianexpress.com/section/sports/cricket/feed/,"
        "https://www.cricketworld.com/feed/,"
        "https://www.icc-cricket.com/media-releases/feed,"
        "https://www.cricket.com.au/news/feed,"
        "https://www.ecb.co.uk/news/rss,"
        # ========== INDIAN SPORTS (Primary) ==========
        "https://feeds.feedburner.com/ndtvsports-latest,"
        "https://timesofindia.indiatimes.com/rssfeeds/4719161.cms,"
        "https://www.thehindu.com/sport/feeder/default.rss,"
        "https://indianexpress.com/section/sports/feed/,"
        "https://sportstar.thehindu.com/feed/,"
        "https://www.sportskeeda.com/feed,"
        "https://scroll.in/field/feed,"
        "https://www.prokabaddi.com/news/rss,"
        "https://www.indiansuperleague.com/news/rss,"
        # ========== INTERNATIONAL SPORTS (Secondary) ==========
        "https://feeds.bbci.co.uk/sport/cricket/rss.xml,"
        "https://feeds.bbci.co.uk/sport/football/rss.xml,"
        "https://feeds.bbci.co.uk/sport/tennis/rss.xml,"
        "https://feeds.bbci.co.uk/sport/formula1/rss.xml,"
        "https://feeds.bbci.co.uk/sport/rss.xml,"
        "https://www.espn.com/espn/rss/news,"
        "https://rss.nytimes.com/services/xml/rss/nyt/Sports.xml,"
        # ========== INDIAN GENERAL NEWS ==========
        "https://feeds.feedburner.com/ndtvnews-top-stories,"
        "https://timesofindia.indiatimes.com/rssfeedstopstories.cms,"
        "https://www.thehindu.com/feeder/default.rss,"
        "https://indianexpress.com/feed/,"
        "https://www.indiatoday.in/rss/home,"
        "https://feeds.feedburner.com/ndtvnews-india-news,"
        "https://www.thehindu.com/news/national/feeder/default.rss,"
        "https://feeds.feedburner.com/gadgets360-latest,"
        "https://entrackr.com/feed/,"
        "https://inc42.com/feed/,"
        "https://economictimes.indiatimes.com/rssfeedsdefault.cms,"
        "https://www.livemint.com/rss/news,"
        # ========== INTERNATIONAL NEWS (Secondary) ==========
        "https://feeds.bbci.co.uk/news/world/rss.xml,"
        "https://techcrunch.com/feed/,"
        "https://www.theverge.com/rss/index.xml,"
        "https://openai.com/blog/rss.xml"
    )

    # --- Scheduler ---
    news_fetch_interval_minutes: int = 30
    daily_email_hour: int = 8
    daily_email_minute: int = 0

    # --- Pagination ---
    articles_per_page: int = 12

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"

    def get_rss_feed_list(self) -> List[str]:
        return [url.strip() for url in self.rss_feeds.split(",") if url.strip()]

    def get_categories(self) -> List[str]:
        return [
            "IPL",
            "Cricket",
            "Sports",
            "India",
            "Politics",
            "AI",
            "Technology",
            "Business",
            "World",
            "Science",
            "Health",
            "Entertainment",
        ]

    @property
    def articles_per_page_val(self) -> int:
        return 12


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()