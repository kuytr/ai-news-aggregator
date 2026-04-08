# ⚡ AI News Aggregator

> A production-ready AI-powered news aggregator built with FastAPI, OpenAI, and Bootstrap 5.

![Tech Stack](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--3.5-412991?logo=openai)
![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-7952B3?logo=bootstrap)

## ✨ Features

- 📰 **Multi-source News** — RSS feeds + NewsAPI.org
- 🤖 **AI Summaries** — OpenAI GPT-3.5 generates 3–5 line summaries
- 😊 **Sentiment Analysis** — TextBlob tags each article Positive/Neutral/Negative
- 🔐 **Email OTP Auth** — Secure registration with email verification
- 🎯 **Personalization** — Category preferences + view history tracking
- 📧 **Daily Digests** — Automated email with trending + personalized news
- ⚡ **Auto-Fetch** — APScheduler fetches news every 30 minutes
- 🔍 **Search & Filter** — Full-text search across all articles
- 📊 **Smart Ranking** — Recency + keywords + engagement score
- 📱 **REST API** — JSON API at `/api/v1` for mobile apps
- 🌙 **Dark Premium UI** — Elegant Bootstrap 5 dark theme

---

## 🗂 Project Structure

```
ai_news_aggregator/
├── app/
│   ├── main.py                 # FastAPI app entry point
│   ├── config.py               # All settings via env vars
│   ├── database.py             # SQLAlchemy setup
│   ├── dependencies.py         # FastAPI DI (auth, db)
│   │
│   ├── models/
│   │   ├── user.py             # User, OTPCode models
│   │   └── article.py          # Article, ArticleView models
│   │
│   ├── schemas/
│   │   ├── user.py             # Pydantic user schemas
│   │   └── article.py          # Pydantic article schemas
│   │
│   ├── services/
│   │   ├── auth_service.py     # JWT + bcrypt
│   │   ├── otp_service.py      # OTP generation/verification
│   │   ├── email_service.py    # SMTP email sending
│   │   ├── news_fetcher.py     # RSS + NewsAPI fetching
│   │   ├── summarizer_service.py  # OpenAI summarization
│   │   ├── sentiment_service.py   # TextBlob sentiment
│   │   ├── ranking_service.py     # Article rank scoring
│   │   └── scheduler_service.py   # APScheduler jobs
│   │
│   ├── routers/
│   │   ├── auth_router.py      # /auth/* routes
│   │   ├── news_router.py      # / and /dashboard routes
│   │   └── api_router.py       # /api/v1/* REST API
│   │
│   ├── templates/              # Jinja2 HTML templates
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── dashboard.html
│   │   ├── article_detail.html
│   │   ├── 404.html / 500.html
│   │   └── auth/
│   │       ├── login.html
│   │       ├── register.html
│   │       └── verify_otp.html
│   │
│   └── static/
│       ├── css/style.css
│       └── js/app.js
│
├── .env.sample                 # Environment variable template
├── requirements.txt
└── README.md
```

---

## 🚀 Local Setup

### 1. Clone and enter the project

```bash
git clone <repo-url>
cd ai_news_aggregator
```

### 2. Create a virtual environment

```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt

# Download TextBlob corpora (required once)
python -c "import textblob; textblob.download_corpora()"
# Or: python -m textblob.download_corpora
```

### 4. Configure environment variables

```bash
cp .env.sample .env
# Edit .env with your actual credentials
```

Required variables:
| Variable | Description |
|---|---|
| `OPENAI_API_KEY` | From https://platform.openai.com |
| `NEWSAPI_KEY` | From https://newsapi.org (free tier OK) |
| `SMTP_USERNAME` | Gmail address |
| `SMTP_PASSWORD` | Gmail App Password (not your login password) |
| `APP_SECRET_KEY` | Any long random string |
| `JWT_SECRET_KEY` | Any long random string |

> 💡 **Gmail Setup**: Enable 2FA → Generate App Password at https://myaccount.google.com/apppasswords

### 5. Run the application

```bash
uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000 in your browser.

---

## 🌐 Deploy on Render

1. Create account at https://render.com
2. New Web Service → Connect your GitHub repo
3. Configure:
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt && python -c "import textblob; textblob.download_corpora()"`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Add all environment variables from `.env.sample`
5. Click Deploy

---

## 🚂 Deploy on Railway

1. Create account at https://railway.app
2. New Project → Deploy from GitHub
3. Add environment variables in Settings → Variables
4. Railway auto-detects Python and deploys

Custom start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

---

## 📱 REST API for Mobile Apps

Base URL: `https://your-domain.com/api/v1`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/articles` | List articles (paginated) |
| `GET` | `/articles/{id}` | Get single article |
| `POST` | `/auth/login` | Get JWT token |
| `GET` | `/me` | Get current user |
| `GET` | `/categories` | List categories |

**Query Parameters for `/articles`:**
- `page` — Page number (default: 1)
- `category` — Filter by category
- `search` — Full-text search
- `sort` — `latest` | `trending` | `ranked`

**Authentication:**
```
Authorization: Bearer <access_token>
```

**Example:**
```bash
curl "https://your-domain.com/api/v1/articles?category=AI&sort=ranked&page=1"
```

---

## 📈 Scaling to Production

### Database
- Swap SQLite for **PostgreSQL**: change `DATABASE_URL` to `postgresql://...`
- Add connection pooling with `create_engine(..., pool_size=10, max_overflow=20)`

### Performance
- Add **Redis caching** for frequently accessed articles
- Use **Celery + Redis** instead of APScheduler for distributed task queues
- Add **CDN** (Cloudflare) for static assets

### Security
- Set `DEBUG=False` in production
- Use HTTPS with SSL certificate (Render/Railway provide this)
- Restrict `CORS allow_origins` to your domain
- Add rate limiting with `slowapi`

### Monitoring
- Add **Sentry** for error tracking: `pip install sentry-sdk[fastapi]`
- Use **Prometheus + Grafana** for metrics
- Set up **health check endpoint** at `/health`

### Search
- Replace SQLite LIKE search with **Elasticsearch** or **Typesense** for fast full-text search

### AI
- Cache OpenAI responses to avoid duplicate API calls
- Use **GPT-4** for higher quality summaries (update model in `summarizer_service.py`)
- Add **async** OpenAI calls with `AsyncOpenAI`

---

## 🔧 Development Tips

Run with hot reload:
```bash
uvicorn app.main:app --reload
```

Manually trigger news fetch:
```python
from app.database import SessionLocal
from app.services.news_fetcher import fetch_all_news
db = SessionLocal()
fetch_all_news(db)
db.close()
```

View API docs (auto-generated by FastAPI):
```
http://localhost:8000/docs
http://localhost:8000/redoc
```

---

## 📄 License

MIT License — Free for personal and commercial use.
