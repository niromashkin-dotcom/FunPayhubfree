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
from aiohttp import web

from bot.config import get_bot_config
from bot.middlewares import AuthMiddleware
from bot.handlers.start import router as start_router
from bot.handlers.callbacks import router as callback_router
from bot.handlers.notifications import router as notifications_router
from bot.handlers.ai_agent import router as ai_router
from bot.keyboards.main import get_main_menu
from bot.formatters import format_welcome
from bot.services import ai_agent_service
from bot.services.cache_service import bot_cache

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("run_bot")


async def _start_health_server() -> web.AppRunner | None:
    """Минимальный HTTP-сервер на $PORT.

    Render создал этот сервис как Web Service, поэтому он сканирует открытый порт
    и убивает инстанс, если порт не открыт (что приводит к рестартам и 409 Conflict
    у Telegram polling). Открываем порт, чтобы бот жил стабильно.
    """
    port = os.environ.get("PORT")
    if not port:
        return None

    async def health(_request: web.Request) -> web.Response:
        return web.json_response({"status": "ok", "service": "funpayhub-tg-bot"})

    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/health", health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(port))
    await site.start()
    logger.info("Health server listening on 0.0.0.0:%s", port)
    return runner


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
    dp.update.outer_middleware(AuthMiddleware())
    dp.include_router(start_router)
    dp.include_router(ai_router)
    dp.include_router(notifications_router)
    dp.include_router(callback_router)

    # Запускаем health/HTTP-сервер МАКСИМАЛЬНО РАНО.
    # Render (даже если сервис случайно web) сканирует порт и убивает инстанс,
    # если порт не открыт — это приводит к рестартам и 409 Conflict у polling.
    # Открываем порт до любых сетевых вызовов, чтобы Render зафиксировал успешный старт.
    health_runner = None
    try:
        health_runner = await _start_health_server()
    except Exception as exc:
        logger.warning("Health server failed to start: %s", exc)

    ai_agent_service.configure(
        admin_chat_id=cfg.admin_chat_id,
        llm_api_keys=[
            {
                "name": "primary",
                "api_key": os.environ.get("LLM_API_KEY", ""),
                "api_url": os.environ.get("LLM_API_URL", ""),
                "model": os.environ.get("LLM_MODEL", "mistral-small-latest"),
            },
            {
                "name": "secondary",
                "api_key": os.environ.get("LLM_API_KEY_2", ""),
                "api_url": os.environ.get("LLM_API_URL_2", ""),
                "model": os.environ.get(
                    "LLM_MODEL_2",
                    "freellm-24ba17fbc6eef0477edbfc9755b0964bbf476eba8b3469cd",
                ),
            },
        ],
        github_token=os.environ.get("GITHUB_TOKEN", ""),
        render_api_key=os.environ.get("RENDER_API_KEY", ""),
        render_service_id=os.environ.get("RENDER_SERVICE_ID", ""),
    )
    await ai_agent_service.start(bot)

    try:
        asyncio.create_task(bot_cache.refresh_loop())
        logger.info("Bot cache background refresh started")
    except Exception as exc:
        logger.warning("Bot cache refresh start failed: %s", exc)

    try:
        me = await bot.get_me()
        logger.info("Bot connected: @%s (id=%s)", me.username, me.id)
    except Exception as exc:
        # НЕ делаем sys.exit: иначе процесс завершается, порт (для web-сервиса)
        # закрывается, Render считает старт неуспешным и убивает/перезапускает
        # инстанс → возникает 409 Conflict у polling. Логируем и идём дальше к polling.
        logger.error("get_me failed (bot may still work via polling): %s", exc)

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Webhook removed")
    except Exception as exc:
        logger.warning("Failed to remove webhook: %s", exc)

    await bot.set_my_commands([
        {"command": "start", "description": "Главное меню"},
        {"command": "menu", "description": "Главное меню"},
        {"command": "ping", "description": "Проверка связи"},
        {"command": "analyze", "description": "AI-анализ файла проекта"},
        {"command": "auth", "description": "Авторизация по паролю"},
    ])

    logger.info("Starting polling...")
    try:
        await dp.start_polling(bot)
    except asyncio.CancelledError:
        pass
    finally:
        await ai_agent_service.stop()
        if health_runner is not None:
            await health_runner.cleanup()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped")
    except Exception as exc:
        logger.error("Fatal error: %s", exc)
        sys.exit(1)
