import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage

from bot.handlers import admin, analyze, channel_listener, history, logs, posts, report, settings, start
from bot.middlewares.auth_middleware import AuthMiddleware
from config import settings as app_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    bot = Bot(
        token=app_settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    storage = RedisStorage.from_url(app_settings.redis_url)
    dp = Dispatcher(storage=storage)

    # Register middleware
    dp.update.middleware(AuthMiddleware())

    # Register routers
    dp.include_router(channel_listener.router)
    dp.include_router(start.router)
    dp.include_router(posts.router)
    dp.include_router(analyze.router)
    dp.include_router(report.router)
    dp.include_router(history.router)
    dp.include_router(logs.router)
    dp.include_router(settings.router)
    dp.include_router(admin.router)

    tasks = [
        dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types()),
    ]

    # Telethon kanal monitoru — sozlangan bo'lsa parallel ishlatiladi
    if app_settings.telegram_api_id and app_settings.telethon_session:
        from infrastructure.telegram.monitor import start_channel_monitor
        tasks.append(start_channel_monitor())
        logger.info("Telethon kanal monitoru ulandi.")
    else:
        logger.info(
            "Telethon sozlanmagan — faqat Bot API ishlatiladi "
            "(views=0 bo'lishi mumkin)."
        )

    logger.info("Bot ishga tushmoqda...")
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
