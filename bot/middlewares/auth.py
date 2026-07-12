from __future__ import annotations

import bcrypt
import json
import logging
import os
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from bot.config import get_bot_config

logger = logging.getLogger("bot.middleware.auth")

_AUTH_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "tg_bot",
    "authorized_users.json",
)


def _load_authorized() -> dict[str, Any]:
    try:
        if os.path.exists(_AUTH_PATH):
            with open(_AUTH_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _is_authorized(user_id: int | str, chat_id: int | str | None = None) -> bool:
    cfg = get_bot_config()
    admin = str(cfg.admin_chat_id)
    if admin and str(user_id) == admin:
        return True
    data = _load_authorized()
    return str(user_id) in set(data.get("authorized_users", []))


class AuthMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        if isinstance(event, Message):
            user = event.from_user
            if user is None:
                return await handler(event, data)
            if _is_authorized(user.id, event.chat.id if event.chat else None):
                return await handler(event, data)
            await event.answer("❌ Доступ запрещён. Вы не авторизованы.")
            return None

        if isinstance(event, CallbackQuery):
            user = event.from_user
            if user is None:
                return await handler(event, data)
            if _is_authorized(user.id):
                return await handler(event, data)
            try:
                await event.answer("❌ Доступ запрещён. Вы не авторизованы.", show_alert=True)
            except Exception:
                pass
            return None

        return await handler(event, data)
