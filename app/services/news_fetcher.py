"""
services/news_fetcher.py - News Fetching Service
"""

import hashlib
import logging
import re
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

import feedparser
import requests
from sqlalchemy.orm import Session

from app.config import settings
from app.models.article import Article
from app.services.sentiment_service import analyze_sentiment, extract_keywords
from app.services.summarizer_service import summarize_article
from app.services.ranking_service import compute_rank_score

logger = logging.getLogger(__name__)

CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    "IPL": [
        # IPL General
        "ipl", "indian premier league", "iplt20",
        # All IPL Teams
        "csk", "chennai super kings", "ms dhoni", "dhoni",
        "mi", "mumbai indians", "rohit sharma",
        "rcb", "royal challengers", "virat kohli",
        "kkr", "kolkata knight riders", "shreyas iyer",
        "srh", "sunrisers hyderabad", "pat cummins",
        "dc", "delhi capitals", "rishabh pant",
        "pbks", "punjab kings",
        "rr", "rajasthan royals", "sanju samson",
        "lsg", "lucknow super giants", "kl rahul",
        "gt", "gujarat titans", "hardik pandya",
        # IPL terms
        "ipl auction", "ipl schedule", "ipl points table",
        "ipl 2025", "ipl 2026", "ipl match", "ipl final",
        "ipl qualifier", "ipl eliminator", "super over ipl",
        "ipl orange cap", "ipl purple cap", "ipl century",
        "ipl hat trick", "ipl record",
    ],
    "Cricket": [
        # Indian Players
        "virat kohli", "rohit sharma", "ms dhoni", "sachin tendulkar",
        "hardik pandya", "jasprit bumrah", "shubman gill",
        "yashasvi jaiswal", "ravindra jadeja", "ravichandran ashwin",
        "team india", "indian cricket", "bcci",
        # International Players
        "ben stokes", "joe root", "steve smith", "pat cummins",
        "babar azam", "kane williamson", "david warner",
        "jos buttler", "mitchell starc",
        # Tournaments
        "ashes", "world cup cricket", "icc", "champions trophy",
        "world test championship", "wtc", "t20 world cup",
        # Cricket Terms
        "test match", "odi", "t20", "cricket",
        "century", "wicket", "innings", "over",
        "batsman", "bowler", "fielding", "powerplay",
        "drs", "lbw", "no ball", "wide", "boundary",
        "six", "four", "maiden over", "hat trick",
        # International Teams
        "australia cricket", "england cricket", "pakistan cricket",
        "south africa cricket", "new zealand cricket",
        "west indies cricket", "sri lanka cricket",
        "bangladesh cricket", "afghanistan cricket",
    ],
    "Sports": [
        # Indian Sports
        "kabaddi", "pkl", "pro kabaddi", "kho kho",
        "isl", "indian super league", "football india",
        "badminton", "pv sindhu", "saina nehwal", "kidambi srikanth",
        "wrestling", "bajrang punia", "vinesh phogat",
        "boxing", "mary kom", "neeraj chopra", "javelin",
        "hockey", "indian hockey",
        # International Sports
        "football", "soccer", "fifa", "premier league", "la liga",
        "bundesliga", "champions league",
        "tennis", "wimbledon", "us open", "french open",
        "grand slam", "atp", "wta",
        "formula 1", "f1", "grand prix",
        "nba", "basketball", "nfl",
        "olympics", "asian games", "commonwealth games",
        "sport", "match", "tournament", "championship",
        "medal", "gold", "silver", "bronze",
    ],
    "India": [
        "india", "indian", "modi", "delhi", "mumbai", "bangalore",
        "chennai", "kolkata", "hyderabad", "pune", "bjp", "congress",
        "lok sabha", "rajya sabha", "supreme court india",
        "rbi", "sebi", "isro", "tata", "reliance",
        "infosys", "wipro", "rupee",
    ],
    "Politics": [
        "politics", "government", "election", "modi", "bjp", "congress",
        "parliament", "lok sabha", "rajya sabha", "chief minister",
        "prime minister", "president", "governor", "policy", "law",
        "bill", "constitution", "court", "cbi", "ed",
        "assembly election", "vote", "campaign", "party", "minister",
        "white house", "trump", "eu", "nato", "un",
    ],
    "AI": [
        "artificial intelligence", "machine learning", "deep learning",
        "neural network", "openai", "chatgpt", "llm", "gpt", "claude",
        "gemini", "ai model", "generative ai", "automation", "robotics",
        "natural language", "computer vision", "data science",
        "ai india", "tech startup india",
    ],
    "Technology": [
        "software", "hardware", "tech", "startup", "app", "smartphone",
        "google", "apple", "microsoft", "meta", "5g", "jio",
        "airtel", "cybersecurity", "blockchain", "cloud computing",
        "semiconductor", "chip", "electric vehicle", "gadget",
        "mobile", "laptop", "internet", "upi", "fintech",
    ],
    "Business": [
        "business", "economy", "market", "stock", "sensex", "nifty",
        "bse", "nse", "rbi", "gdp", "inflation", "budget",
        "finance", "investment", "ipo", "startup", "unicorn",
        "tata", "reliance", "adani", "mahindra", "bajaj",
        "revenue", "profit", "merger", "acquisition", "trade",
    ],
    "World": [
        "world", "international", "global", "usa", "uk", "china",
        "russia", "pakistan", "ukraine", "war", "peace",
        "united nations", "nato", "eu", "climate", "g20",
        "diplomacy", "foreign", "bilateral", "sanctions",
    ],
    "Science": [
        "science", "research", "isro", "nasa", "space", "mission",
        "chandrayaan", "gaganyaan", "satellite", "physics",
        "biology", "chemistry", "study", "discovery",
        "climate change", "environment", "pollution",
    ],
    "Health": [
        "health", "medicine", "hospital", "disease", "vaccine",
        "aiims", "icmr", "covid", "drug", "treatment",
        "mental health", "cancer", "diabetes", "nutrition",
        "fitness", "surgery", "pharmacy", "ayurveda",
    ],
    "Entertainment": [
        "bollywood", "movie", "film", "actor", "actress",
        "shah rukh khan", "salman khan", "deepika", "ranveer",
        "music", "song", "album", "ott", "netflix", "amazon prime",
        "hotstar", "disney", "award", "filmfare", "oscar",
        "tv show", "web series", "streaming", "concert",
    ],
}

INDIAN_SOURCES = [
    "ndtv", "times of india", "the hindu", "indian express",
    "hindustan times", "india today", "economic times", "livemint",
    "business standard", "gadgets360", "digit", "entrackr",
    "yourstory", "inc42", "espncricinfo", "cricbuzz", "crictracker",
    "sportskeeda", "sportstar", "scroll", "iplt20", "cricketworld",
]

IPL_SOURCES = [
    "iplt20", "cricbuzz", "espncricinfo", "crictracker",
    "ndtvsports", "sportskeeda", "sportstar",
]


def _generate_content_hash(title: str, url: str) -> str:
    content = f"{title.lower().strip()}{url.lower().strip()}"
    return hashlib.sha256(content.encode()).hexdigest()


def _auto_categorize(title: str, content: str, source: str = "") -> str:
    text = f"{title} {content} {source}".lower()
    scores: Dict[str, int] = {}

    for category, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text)

        # Boost IPL — highest priority
        if category == "IPL" and any(
            src in source.lower() for src in IPL_SOURCES
        ):
            score += 6
        # Extra boost if title directly mentions IPL
        if category == "IPL" and "ipl" in title.lower():
            score += 8

        # Boost Cricket
        if category == "Cricket" and any(
            src in source.lower() for src in
            ["cricinfo", "cricbuzz", "crictracker", "icc", "bcci"]
        ):
            score += 5

        # Boost Sports
        if category == "Sports" and any(
            src in source.lower() for src in
            ["espn", "sport", "sportskeeda", "sportstar", "ndtvsports"]
        ):
            score += 3

        # Boost India
        if category == "India" and any(
            src in source.lower() for src in INDIAN_SOURCES
        ):
            score += 2

        if score > 0:
            scores[category] = score

    if scores:
        return max(scores, key=scores.get)  # type: ignore
    return "India"


def _clean_html(text: str) -> str:
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text or '').strip()


def _parse_date(date_str: Any) -> Optional[datetime]:
    if not date_str:
        return None
    try:
        if isinstance(date_str, datetime):
            if date_str.tzinfo is None:
                return date_str.replace(tzinfo=timezone.utc)
            return date_str
        from dateutil import parser
        dt = parser.parse(str(date_str))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def _save_article(db: Session, article_data: dict) -> Optional[Article]:
    url = article_data.get("url", "").strip()
    title = article_data.get("title", "").strip()

    if not url or not title:
        return None

    content_hash = _generate_content_hash(title, url)

    existing = db.query(Article).filter(
        (Article.url == url) | (Article.content_hash == content_hash)
    ).first()

    if existing:
        logger.debug(f"Duplicate skipped: {title[:60]}")
        return None

    content = article_data.get("content", "") or ""
    source = article_data.get("source", "")
    category = article_data.get("category") or _auto_categorize(
        title, content, source
    )
    summary = summarize_article(title, content)
    sentiment_text = f"{title} {content}"
    sentiment, sentiment_score = analyze_sentiment(sentiment_text)
    keywords = extract_keywords(sentiment_text)

    article = Article(
        title=title,
        url=url,
        content=content[:10000],
        summary=summary,
        image_url=article_data.get("image_url"),
        source=source,
        author=article_data.get("author"),
        category=category,
        published_at=_parse_date(article_data.get("published_at")),
        sentiment=sentiment,
        sentiment_score=sentiment_score,
        keywords=",".join(keywords),
        content_hash=content_hash,
        view_count=0,
    )

    article.rank_score = compute_rank_score(article)
    db.add(article)
    db.commit()
    db.refresh(article)
    logger.info(f"Saved: {title[:60]} [{category}]")
    return article


def fetch_from_rss(db: Session) -> int:
    saved_count = 0
    feed_urls = settings.get_rss_feed_list()

    for feed_url in feed_urls:
        try:
            logger.info(f"Fetching RSS: {feed_url}")
            feed = feedparser.parse(feed_url)
            source_name = feed.feed.get("title", feed_url.split("/")[2])

            for entry in feed.entries[:30]:
                image_url = None
                if hasattr(entry, "media_content") and entry.media_content:
                    image_url = entry.media_content[0].get("url")
                elif hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
                    image_url = entry.media_thumbnail[0].get("url")

                content = ""
                if hasattr(entry, "content") and entry.content:
                    content = _clean_html(entry.content[0].get("value", ""))
                elif hasattr(entry, "summary"):
                    content = _clean_html(entry.summary)

                article_data = {
                    "title": _clean_html(entry.get("title", "")),
                    "url": entry.get("link", ""),
                    "content": content,
                    "source": source_name,
                    "author": entry.get("author", ""),
                    "published_at": entry.get("published", entry.get("updated")),
                    "image_url": image_url,
                }

                result = _save_article(db, article_data)
                if result:
                    saved_count += 1

        except Exception as e:
            logger.error(f"RSS fetch failed for {feed_url}: {e}")
            continue

    logger.info(f"RSS fetch complete. Saved {saved_count} new articles.")
    return saved_count


def fetch_from_newsapi(db: Session) -> int:
    if not settings.newsapi_key:
        logger.warning("NewsAPI key not configured. Skipping.")
        return 0

    saved_count = 0

    # ── IPL specific topics (Highest Priority) ──
    ipl_topics = [
        "IPL 2025 match",
        "IPL 2026 cricket",
        "Indian Premier League",
        "IPL points table",
        "IPL auction",
        "CSK Chennai Super Kings",
        "MI Mumbai Indians IPL",
        "RCB Royal Challengers IPL",
        "KKR Kolkata Knight Riders",
        "SRH Sunrisers Hyderabad IPL",
        "DC Delhi Capitals IPL",
        "RR Rajasthan Royals IPL",
        "LSG Lucknow Super Giants",
        "GT Gujarat Titans IPL",
        "PBKS Punjab Kings IPL",
        "Virat Kohli IPL",
        "Rohit Sharma IPL",
        "MS Dhoni IPL",
        "Hardik Pandya IPL",
        "IPL orange cap purple cap",
    ]

    for topic in ipl_topics:
        try:
            response = requests.get(
                "https://newsapi.org/v2/everything",
                params={
                    "apiKey": settings.newsapi_key,
                    "q": topic,
                    "language": "en",
                    "sortBy": "publishedAt",
                    "pageSize": 15,
                },
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()

            for item in data.get("articles", []):
                if item.get("title") == "[Removed]":
                    continue
                article_data = {
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "content": item.get("content") or item.get("description") or "",
                    "source": item.get("source", {}).get("name", "NewsAPI"),
                    "author": item.get("author", ""),
                    "published_at": item.get("publishedAt"),
                    "image_url": item.get("urlToImage"),
                    "category": "IPL",
                }
                result = _save_article(db, article_data)
                if result:
                    saved_count += 1

        except Exception as e:
            logger.error(f"NewsAPI IPL fetch failed for '{topic}': {e}")
            continue

    # ── Cricket topics ──
    cricket_topics = [
        "India cricket team match",
        "BCCI cricket India",
        "ICC cricket world cup",
        "Test cricket India",
        "T20 cricket India",
        "Virat Kohli cricket",
        "Rohit Sharma cricket",
        "Jasprit Bumrah cricket",
        "cricket ashes England Australia",
        "cricket champions trophy",
        "world test championship",
    ]

    for topic in cricket_topics:
        try:
            response = requests.get(
                "https://newsapi.org/v2/everything",
                params={
                    "apiKey": settings.newsapi_key,
                    "q": topic,
                    "language": "en",
                    "sortBy": "publishedAt",
                    "pageSize": 10,
                },
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()

            for item in data.get("articles", []):
                if item.get("title") == "[Removed]":
                    continue
                article_data = {
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "content": item.get("content") or item.get("description") or "",
                    "source": item.get("source", {}).get("name", "NewsAPI"),
                    "author": item.get("author", ""),
                    "published_at": item.get("publishedAt"),
                    "image_url": item.get("urlToImage"),
                    "category": "Cricket",
                }
                result = _save_article(db, article_data)
                if result:
                    saved_count += 1

        except Exception as e:
            logger.error(f"NewsAPI cricket fetch failed for '{topic}': {e}")
            continue

    # ── Other Indian topics ──
    indian_topics = [
        "India sports kabaddi football",
        "India politics Modi parliament",
        "India AI technology startup",
        "India business economy Sensex",
        "India ISRO space science",
        "India entertainment Bollywood",
    ]

    for topic in indian_topics:
        try:
            response = requests.get(
                "https://newsapi.org/v2/everything",
                params={
                    "apiKey": settings.newsapi_key,
                    "q": topic,
                    "language": "en",
                    "sortBy": "publishedAt",
                    "pageSize": 10,
                },
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()

            for item in data.get("articles", []):
                if item.get("title") == "[Removed]":
                    continue
                article_data = {
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "content": item.get("content") or item.get("description") or "",
                    "source": item.get("source", {}).get("name", "NewsAPI"),
                    "author": item.get("author", ""),
                    "published_at": item.get("publishedAt"),
                    "image_url": item.get("urlToImage"),
                }
                result = _save_article(db, article_data)
                if result:
                    saved_count += 1

        except Exception as e:
            logger.error(f"NewsAPI topic fetch failed for '{topic}': {e}")
            continue

    # ── International categories (Secondary) ──
    for cat in ["sports", "technology", "science", "health", "business"]:
        try:
            response = requests.get(
                "https://newsapi.org/v2/top-headlines",
                params={
                    "apiKey": settings.newsapi_key,
                    "category": cat,
                    "language": "en",
                    "pageSize": 5,
                },
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()

            for item in data.get("articles", []):
                if item.get("title") == "[Removed]":
                    continue
                article_data = {
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "content": item.get("content") or item.get("description") or "",
                    "source": item.get("source", {}).get("name", "NewsAPI"),
                    "author": item.get("author", ""),
                    "published_at": item.get("publishedAt"),
                    "image_url": item.get("urlToImage"),
                    "category": cat.capitalize(),
                }
                result = _save_article(db, article_data)
                if result:
                    saved_count += 1

        except Exception as e:
            logger.error(f"NewsAPI category fetch failed for '{cat}': {e}")
            continue

    logger.info(f"NewsAPI fetch complete. Saved {saved_count} new articles.")
    return saved_count


def fetch_all_news(db: Session) -> int:
    logger.info("Starting news fetch cycle...")
    total = 0
    total += fetch_from_rss(db)
    total += fetch_from_newsapi(db)
    logger.info(f"News fetch complete. Total new articles: {total}")
    return total