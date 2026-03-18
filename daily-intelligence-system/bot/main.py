"""Telegram bot ishga tushirish."""
import asyncio
from loguru import logger
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
)
from backend.core.config import settings
from bot.handlers.start import start_handler, callback_handler
from bot.handlers.digest import digest_handler
from bot.handlers.brief import brief_handler
from bot.handlers.topics import topics_handler
from bot.handlers.settings import settings_handler
from bot.handlers.archive import archive_handler
from bot.handlers.alerts import alerts_handler


def build_app() -> Application:
    app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()

    # Komandalar
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("digest", digest_handler))
    app.add_handler(CommandHandler("brief", brief_handler))
    app.add_handler(CommandHandler("topics", topics_handler))
    app.add_handler(CommandHandler("settings", settings_handler))
    app.add_handler(CommandHandler("archive", archive_handler))
    app.add_handler(CommandHandler("alerts", alerts_handler))

    # Callback handler (inline buttonlar)
    app.add_handler(CallbackQueryHandler(callback_handler))

    return app


def main() -> None:
    logger.info("Starting Telegram bot...")
    app = build_app()
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
