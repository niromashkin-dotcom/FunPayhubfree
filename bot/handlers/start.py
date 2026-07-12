from __future__ import annotations

import logging
import os

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.exceptions import TelegramBadRequest

from bot.formatters import format_welcome
from bot.keyboards.main import get_main_menu
from bot.config import get_bot_config

logger = logging.getLogger("bot.handlers.start")

router = Router()


@router.message(Command("start", "menu"))
async def cmd_start(message: Message) -> None:
    try:
        await message.answer(
            text=format_welcome(),
            reply_markup=get_main_menu(),
        )
    except TelegramBadRequest:
        await message.reply("Главное меню", reply_markup=get_main_menu())


@router.message(Command("ping"))
async def cmd_ping(message: Message) -> None:
    await message.reply("pong ✅")


@router.message(Command("auth"))
async def cmd_auth(message: Message) -> None:
    text = (message.text or "").strip()
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply("❌ Использование: /auth <пароль>")
        return

    password = parts[1]
    cfg = get_bot_config()
    auth_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "tg_bot",
        "authorized_users.json",
    )
    try:
        if not os.path.exists(auth_path):
            await message.reply("❌ Файл конфигурации авторизации не найден.")
            return
        with open(auth_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        stored_hash = config.get("password_hash", "")
        enable_auth = config.get("enable_password_auth", True)

        if not enable_auth:
            await message.reply("⚠️ Авторизация по паролю отключена в конфигурации.")
            return

        if not stored_hash:
            # Если хеша нет — сохраняем текущий пароль как первый
            hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            config["password_hash"] = hashed
            with open(auth_path, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            await message.reply("✅ Пароль установлен. Авторизация прошла успешно.")
            return

        if bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8")):
            user_id = message.from_user.id
            users = set(config.get("authorized_users", []))
            users.add(user_id)
            config["authorized_users"] = sorted(users)
            with open(auth_path, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            await message.reply(
                f"✅ Авторизация успешна! Ваш user_id: {user_id}\n"
                "Доступ сохранён и переживёт перезапуск бота."
            )
        else:
            await message.reply("❌ Неверный пароль.")
    except Exception as exc:
        logger.error("Auth error: %s", exc)
        await message.reply("❌ Ошибка авторизации.")
