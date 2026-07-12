#!/usr/bin/env python3
"""
run_bot.py — Entrypoint for the new aiogram-based Telegram Control Bot.
"""

import asyncio
import logging
import os
import sys

from dotenv import load_dotenv
load_dotenv()

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from bot.config import get_bot_config
from bot.handlers.start import router as start_router
from bot.handlers.callbacks import router as callback_router
from bot.handlers.notifications import router as notifications_router
from bot.handlers.ai_agent import router as ai_router
from bot.keyboards.main import get_main_menu
from bot.formatters import format_welcome
from bot.services import ai_agent_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("run_bot")


async def main():
    cfg = get_bot_config()
    if not cfg.token:
        logger.error("TELEGRAM_BOT_TOKEN is not set")
        sys.exit(1)

    bot = Bot(
        token=cfg.token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.include_router(start_router)
    dp.include_router(ai_router)
    dp.include_router(notifications_router)
    dp.include_router(callback_router)

    ai_agent_service.configure(
        admin_chat_id=cfg.admin_chat_id,
        llm_api_keys=[
            {
                "name": "primary",
                "api_key": os.environ.get("LLM_API_KEY", ""),
                "api_url": os.environ.get("LLM_API_URL", ""),
                "model": "freellm-24ba17fbc6eef0477edbfc9755b0964bbf476eba8b3469cd",
            },
            {
                "name": "secondary",
                "api_key": os.environ.get("LLM_API_KEY_2", ""),
                "api_url": os.environ.get("LLM_API_URL_2", ""),
                "model": os.environ.get("LLM_MODEL_2", "gpt-4o-mini"),
            },
        ],
        github_token=os.environ.get("GITHUB_TOKEN", ""),
        render_api_key=os.environ.get("RENDER_API_KEY", ""),
        render_service_id=os.environ.get("RENDER_SERVICE_ID", ""),
    )
    await ai_agent_service.start(bot)

    try:
        me = await bot.get_me()
        logger.info("Bot connected: @%s (id=%s)", me.username, me.id)
    except Exception as exc:
        logger.error("Failed to connect to Telegram: %s", exc)
        sys.exit(1)

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Webhook removed")
    except Exception as exc:
        logger.warning("Failed to remove webhook: %s", exc)

    await bot.set_my_commands([
        {"command": "start", "description": "Главное меню"},
        {"command": "menu", "description": "Главное меню"},
        {"command": "ping", "description": "Проверка связи"},
        {"command": "auth", "description": "Авторизация по паролю"},
    ])

    logger.info("Starting polling...")
    try:
        await dp.start_polling(bot)
    except asyncio.CancelledError:
        pass
    finally:
        await ai_agent_service.stop()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped")
    except Exception as exc:
        logger.error("Fatal error: %s", exc)
        sys.exit(1)
