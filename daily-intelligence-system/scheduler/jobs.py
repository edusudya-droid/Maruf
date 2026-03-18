"""APScheduler vazifalari — barcha avtomatik ishlarni rejalashtirish."""
import asyncio
from loguru import logger
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from backend.core.config import settings
from database.models import BriefType


async def job_parse_sources() -> None:
    """Har 30 daqiqada manbalardan maqolalar yig'ish."""
    logger.info("JOB: Parsing sources...")
    try:
        from parser.source_manager import SourceManager
        manager = SourceManager()
        count = await manager.run_all()
        logger.info(f"JOB: Parsed {count} new articles")
    except Exception as e:
        logger.error(f"JOB parse_sources failed: {e}")


async def job_process_articles() -> None:
    """Yangi maqolalarni AI bilan tahlil qilish."""
    logger.info("JOB: Processing articles with AI...")
    try:
        from sqlalchemy import select, and_
        from backend.core.database import AsyncSessionLocal
        from database.models import Article
        from ai.classifier import classify_article
        from ai.summarizer import summarize_article
        from ai.entity_extractor import extract_entities
        from ai.risk_detector import calculate_risk_score

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Article)
                .where(and_(Article.is_processed == False, Article.is_duplicate == False))
                .limit(50)
            )
            articles = result.scalars().all()

        logger.info(f"Processing {len(articles)} articles")

        for article in articles:
            try:
                # Tasniflash
                classification = await classify_article(article.title, article.content)
                # Qisqartirish
                summary = await summarize_article(article.title, article.content, article.language)
                # Entity ajratish
                entities = await extract_entities(f"{article.title}\n{article.content[:1000]}")

                async with AsyncSessionLocal() as session:
                    db_art = await session.get(Article, article.id)
                    if db_art:
                        from database.models import ArticleCategory, Sentiment
                        try:
                            db_art.category = ArticleCategory(classification.get("category", "economics"))
                        except ValueError:
                            db_art.category = ArticleCategory.economics
                        try:
                            db_art.sentiment = Sentiment(classification.get("sentiment", "neutral"))
                        except ValueError:
                            db_art.sentiment = Sentiment.neutral
                        db_art.importance_score = float(classification.get("importance_score", 0.3))
                        db_art.summary = summary
                        db_art.entities = entities
                        db_art.is_processed = True
                        await session.commit()

            except Exception as e:
                logger.warning(f"Article {article.id} processing failed: {e}")

    except Exception as e:
        logger.error(f"JOB process_articles failed: {e}")


async def job_detect_events() -> None:
    """Har 2 soatda voqealarni aniqlash."""
    logger.info("JOB: Detecting events...")
    try:
        from ai.event_detector import detect_events
        from ai.hidden_event_detector import detect_hidden_events
        count = await detect_events()
        hidden = await detect_hidden_events()
        logger.info(f"JOB: Detected {count} events, {len(hidden)} hidden signals")
    except Exception as e:
        logger.error(f"JOB detect_events failed: {e}")


async def job_generate_morning_brief() -> None:
    """Ertalabki brief yaratish."""
    logger.info("JOB: Generating morning brief...")
    try:
        from ai.brief_generator import generate_brief
        brief = await generate_brief(BriefType.morning)
        logger.info(f"JOB: Morning brief created: {brief.id if brief else None}")
    except Exception as e:
        logger.error(f"JOB morning_brief failed: {e}")


async def job_send_morning_brief() -> None:
    """Ertalabki briefni yuborish."""
    logger.info("JOB: Sending morning brief...")
    try:
        from sqlalchemy import select
        from backend.core.database import AsyncSessionLocal
        from database.models import Brief
        from notifications.telegram_sender import send_brief_to_all_users

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Brief)
                .where(Brief.brief_type == BriefType.morning, Brief.sent_at == None)
                .order_by(Brief.created_at.desc())
                .limit(1)
            )
            brief = result.scalar_one_or_none()

        if brief:
            await send_brief_to_all_users(brief)
        else:
            logger.warning("No unsent morning brief found")
    except Exception as e:
        logger.error(f"JOB send_morning_brief failed: {e}")


async def job_generate_midday_brief() -> None:
    logger.info("JOB: Generating midday brief...")
    try:
        from ai.brief_generator import generate_brief
        await generate_brief(BriefType.midday)
    except Exception as e:
        logger.error(f"JOB midday_brief failed: {e}")


async def job_send_midday_brief() -> None:
    logger.info("JOB: Sending midday brief...")
    try:
        from sqlalchemy import select
        from backend.core.database import AsyncSessionLocal
        from database.models import Brief
        from notifications.telegram_sender import send_brief_to_all_users

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Brief)
                .where(Brief.brief_type == BriefType.midday, Brief.sent_at == None)
                .order_by(Brief.created_at.desc())
                .limit(1)
            )
            brief = result.scalar_one_or_none()

        if brief:
            await send_brief_to_all_users(brief)
    except Exception as e:
        logger.error(f"JOB send_midday_brief failed: {e}")


async def job_generate_evening_brief() -> None:
    logger.info("JOB: Generating evening brief...")
    try:
        from ai.brief_generator import generate_brief
        await generate_brief(BriefType.evening)
    except Exception as e:
        logger.error(f"JOB evening_brief failed: {e}")


async def job_send_evening_brief() -> None:
    logger.info("JOB: Sending evening brief...")
    try:
        from sqlalchemy import select
        from backend.core.database import AsyncSessionLocal
        from database.models import Brief
        from notifications.telegram_sender import send_brief_to_all_users

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Brief)
                .where(Brief.brief_type == BriefType.evening, Brief.sent_at == None)
                .order_by(Brief.created_at.desc())
                .limit(1)
            )
            brief = result.scalar_one_or_none()

        if brief:
            await send_brief_to_all_users(brief)
    except Exception as e:
        logger.error(f"JOB send_evening_brief failed: {e}")


async def job_update_source_scores() -> None:
    """Har kuni 00:00 da Dynamic Source Score yangilash."""
    logger.info("JOB: Updating source scores...")
    try:
        from source_intelligence.dynamic_scorer import update_source_scores
        await update_source_scores()
    except Exception as e:
        logger.error(f"JOB update_source_scores failed: {e}")


async def job_check_alerts() -> None:
    """Yuborilmagan alertlarni tekshirib yuborish."""
    try:
        from notifications.alert_manager import check_and_send_alerts
        await check_and_send_alerts()
    except Exception as e:
        logger.error(f"JOB check_alerts failed: {e}")


def build_scheduler() -> AsyncIOScheduler:
    """Barcha vazifalarni ro'yxatdan o'tkazib scheduler qaytarish."""
    scheduler = AsyncIOScheduler(timezone="Asia/Tashkent")

    # Parsing — har 30 daqiqada
    scheduler.add_job(
        job_parse_sources, CronTrigger(minute="*/30"),
        id="parse_sources", replace_existing=True,
    )

    # AI processing — har 30 daqiqada (parsingdan 5 daqiqa keyin)
    scheduler.add_job(
        job_process_articles, CronTrigger(minute="5,35"),
        id="process_articles", replace_existing=True,
    )

    # Event detection — har 2 soatda
    scheduler.add_job(
        job_detect_events, CronTrigger(hour="*/2", minute="10"),
        id="detect_events", replace_existing=True,
    )

    # Morning brief yaratish — 07:30
    morning_h, morning_m = settings.MORNING_BRIEF_TIME.split(":")
    scheduler.add_job(
        job_generate_morning_brief,
        CronTrigger(hour=int(morning_h), minute=int(morning_m)),
        id="gen_morning_brief", replace_existing=True,
    )

    # Morning brief yuborish — 08:00
    scheduler.add_job(
        job_send_morning_brief, CronTrigger(hour=8, minute=0),
        id="send_morning_brief", replace_existing=True,
    )

    # Midday brief yaratish — 12:30
    midday_h, midday_m = settings.MIDDAY_BRIEF_TIME.split(":")
    scheduler.add_job(
        job_generate_midday_brief,
        CronTrigger(hour=int(midday_h), minute=int(midday_m)),
        id="gen_midday_brief", replace_existing=True,
    )

    # Midday brief yuborish — 13:00
    scheduler.add_job(
        job_send_midday_brief, CronTrigger(hour=13, minute=0),
        id="send_midday_brief", replace_existing=True,
    )

    # Evening brief yaratish — 18:30
    evening_h, evening_m = settings.EVENING_BRIEF_TIME.split(":")
    scheduler.add_job(
        job_generate_evening_brief,
        CronTrigger(hour=int(evening_h), minute=int(evening_m)),
        id="gen_evening_brief", replace_existing=True,
    )

    # Evening brief yuborish — 19:00
    scheduler.add_job(
        job_send_evening_brief, CronTrigger(hour=19, minute=0),
        id="send_evening_brief", replace_existing=True,
    )

    # Source scoring — har kuni 00:00
    scheduler.add_job(
        job_update_source_scores, CronTrigger(hour=0, minute=0),
        id="update_source_scores", replace_existing=True,
    )

    # Alert check — har 15 daqiqada
    scheduler.add_job(
        job_check_alerts, CronTrigger(minute="*/15"),
        id="check_alerts", replace_existing=True,
    )

    return scheduler


async def main() -> None:
    logger.info("Starting scheduler...")
    scheduler = build_scheduler()
    scheduler.start()
    logger.info("Scheduler started. Jobs:")
    for job in scheduler.get_jobs():
        logger.info(f"  - {job.id}: {job.next_run_time}")

    try:
        while True:
            await asyncio.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logger.info("Scheduler stopped")


if __name__ == "__main__":
    asyncio.run(main())
