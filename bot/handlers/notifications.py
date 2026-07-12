from __future__ import annotations

import logging

from aiogram import Router, F
from aiogram.types import CallbackQuery

from bot.formatters import format_error
from bot.keyboards.main import get_back_button

logger = logging.getLogger("bot.handlers.notifications")

router = Router()


@router.callback_query(F.data == "notifications")
async def cb_notifications(query: CallbackQuery) -> None:
    try:
        await query.answer("🔔 Уведомления")
        await query.message.edit_text(
            text="🔔 <b>Уведомления</b>\nЗдесь будут отображаться системные уведомления.",
            reply_markup=get_back_button(),
        )
    except Exception as exc:
        logger.error("notifications error: %s", exc)
        await query.answer("❌ Ошибка", show_alert=True)
