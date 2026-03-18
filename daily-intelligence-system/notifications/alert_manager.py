"""Muhim xabarnomalar boshqaruvchisi."""
from loguru import logger
from telegram import Bot
from sqlalchemy import select
from backend.core.config import settings
from backend.core.database import AsyncSessionLocal
from database.models import Alert, Event, User, AlertType
from datetime import datetime


async def check_and_send_alerts() -> int:
    """Yuborilmagan alertlarni topib yuborish."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Alert).where(Alert.sent_at == None).limit(10)
        )
        alerts = result.scalars().all()

    if not alerts:
        return 0

    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)

    async with AsyncSessionLocal() as session:
        users_result = await session.execute(
            select(User).where(User.is_active == True)
        )
        users = users_result.scalars().all()

    sent_total = 0
    for alert in alerts:
        icon = "🚨" if alert.alert_type == AlertType.urgent else "⚠️"
        text = f"{icon} <b>{alert.title}</b>\n\n{alert.message}"

        count = 0
        for user in users:
            try:
                await bot.send_message(
                    chat_id=user.telegram_id,
                    text=text,
                    parse_mode="HTML",
                )
                count += 1
            except Exception as e:
                logger.warning(f"Alert send error to {user.telegram_id}: {e}")

        async with AsyncSessionLocal() as session:
            db_alert = await session.get(Alert, alert.id)
            if db_alert:
                db_alert.sent_at = datetime.utcnow()
                db_alert.recipient_count = count
                await session.commit()

        sent_total += count
        logger.info(f"Alert '{alert.title[:40]}' sent to {count} users")

    return sent_total


async def create_alert(event: Event, alert_type: AlertType) -> Alert:
    """Voqea uchun alert yaratish."""
    type_labels = {
        AlertType.urgent: "Shoshilinch",
        AlertType.risk: "Risk",
        AlertType.opportunity: "Imkoniyat",
    }
    label = type_labels.get(alert_type, "Xabar")

    async with AsyncSessionLocal() as session:
        alert = Alert(
            event_id=event.id,
            alert_type=alert_type,
            title=f"{label}: {event.title[:100]}",
            message=event.description[:500],
        )
        session.add(alert)
        await session.commit()
        await session.refresh(alert)
        logger.info(f"Alert created for event {event.id}")
        return alert
