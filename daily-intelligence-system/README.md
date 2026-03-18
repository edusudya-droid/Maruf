# Daily Intelligence System

300+ manbadan avtomatik ma'lumot yig'ib, AI orqali tahlil qilib, har kuni uchta vaqtda Telegram orqali analitik brifing yuboruvchi tizim.

## Arxitektura

```
daily-intelligence-system/
├── backend/          # FastAPI admin API
├── parser/           # RSS, HTML, Telegram parserlari
├── processing/       # Matn tozalash, dublikat aniqlash
├── ai/               # AI tahlil (classifier, summarizer, event detector, brief generator)
├── bot/              # Telegram bot
├── notifications/    # Xabarnomalar
├── scheduler/        # APScheduler vazifalari
├── source_intelligence/ # Dynamic Source Scoring
└── database/         # SQLAlchemy modellari, Alembic
```

## Texnologiya steki

- **Python 3.11+** | **FastAPI** | **PostgreSQL 15** | **Redis 7**
- **python-telegram-bot 20+** | **telethon** | **feedparser**
- **Anthropic claude-sonnet-4-20250514** | **scikit-learn** (TF-IDF)
- **APScheduler** | **Docker Compose**

## Ishga tushirish

```bash
# 1. .env faylini yaratish
cp .env.example .env
# .env faylini to'ldirish

# 2. Docker bilan ishga tushirish
docker-compose up -d db redis

# 3. Migratsiyalar
alembic upgrade head

# 4. Boshlang'ich manbalar
python -m database.seeds.initial_sources

# 5. Barcha xizmatlarni ishga tushirish
docker-compose up -d

# 6. Tekshirish
curl -H "X-Admin-Key: your_key" http://localhost:8000/api/v1/stats/overview
```

## Brief jadvali

| Vaqt  | Vazifa                         |
|-------|-------------------------------|
| 07:30 | Morning Brief yaratish         |
| 08:00 | Morning Brief yuborish         |
| 12:30 | Midday Brief yaratish          |
| 13:00 | Midday Brief yuborish          |
| 18:30 | Evening Brief yaratish         |
| 19:00 | Evening Brief yuborish         |
| */30m | Manbalardan ma'lumot yig'ish   |
| */2h  | Event Detection                |
| 00:00 | Dynamic Source Score yangilash |

## API Endpointlar

```
GET  /api/v1/sources          Manbalar ro'yxati
POST /api/v1/sources          Yangi manba
GET  /api/v1/articles         Maqolalar
GET  /api/v1/events           Voqealar
POST /api/v1/events/detect    Event detection ishga tushirish
GET  /api/v1/briefs           Briflar
POST /api/v1/briefs/generate  Brief yaratish
GET  /api/v1/stats/overview   Statistika
```

## Bot buyruqlari

```
/start    - Ro'yxatdan o'tish
/digest   - So'nggi brifing
/brief    - Tematik brief [mavzu]
/topics   - Mavzularni o'zgartirish
/settings - Sozlamalar
/archive  - Arxiv
/alerts   - Ogohlantirishlar
```
