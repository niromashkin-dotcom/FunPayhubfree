from __future__ import annotations

import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from bot.services import ai_agent_service

logger = logging.getLogger("bot.handlers.ai")

router = Router()


def _confirm_keyboard(action: str, item_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да", callback_data=f"confirm_{action}_{item_id}"),
            InlineKeyboardButton(text="❌ Нет", callback_data=f"cancel_{action}_{item_id}"),
        ],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")],
    ])


@router.callback_query(F.data == "ai_agent")
async def cb_ai_agent(query: CallbackQuery) -> None:
    await query.answer()
    patches = ai_agent_service._pending_patches
    lines = ["🤖 <b>AI Agent</b>", "─" * 25]
    if ai_agent_service.is_ready():
        lines.append("Статус: 🟢 АКТИВЕН")
        lines.append(f"Мониторинг: каждые {ai_agent_service._scan_interval} сек")
        lines.append(f"Патчей ожидает: {len([p for p in patches if not p.applied])}")
    else:
        lines.append("Статус: 🔴 НЕ АКТИВЕН")
        lines.append("Нет API ключа LLM")
    if patches:
        lines.append("")
        lines.append("📋 <b>Последние действия:</b>")
        for p in patches[-3:]:
            status = "✅" if p.applied else "⏳"
            lines.append(f"  {status} {p.diagnosis[:40]}")
    await query.message.edit_text(text="\n".join(lines), reply_markup=_get_ai_keyboard())


def _get_ai_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data="ai_stats"),
            InlineKeyboardButton(text="📜 Логи", callback_data="ai_logs"),
        ],
        [
            InlineKeyboardButton(text="🔔 Уведомления", callback_data="ai_notifications"),
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="ai_settings"),
        ],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")],
    ])


@router.callback_query(F.data.startswith("apply_patch_"))
async def cb_apply_patch(query: CallbackQuery) -> None:
    await query.answer()
    patch_id = query.data.split("_", 2)[-1]
    text = "⚠️ <b>Применить патч?</b>\n\nЭто изменит файлы на сервере и запустит деплой."
    await query.message.edit_text(text=text, reply_markup=_confirm_keyboard("apply_patch", patch_id))


@router.callback_query(F.data.startswith("reject_patch_"))
async def cb_reject_patch(query: CallbackQuery) -> None:
    await query.answer()
    patch_id = query.data.split("_", 2)[-1]
    text = "⚠️ <b>Отклонить патч?</b>\n\nПатч не будет применён."
    await query.message.edit_text(text=text, reply_markup=_confirm_keyboard("reject_patch", patch_id))


@router.callback_query(F.data.startswith("confirm_apply_patch_"))
async def cb_confirm_apply_patch(query: CallbackQuery) -> None:
    await query.answer()
    patch_id = query.data.replace("confirm_apply_patch_", "")
    ok = await ai_agent_service.apply_patch(patch_id, query.bot)
    text = "✅ Патч применён" if ok else "❌ Не удалось применить патч"
    await query.message.edit_text(text=text, reply_markup=_get_ai_keyboard())


@router.callback_query(F.data.startswith("confirm_reject_patch_"))
async def cb_confirm_reject_patch(query: CallbackQuery) -> None:
    await query.answer()
    patch_id = query.data.replace("confirm_reject_patch_", "")
    await ai_agent_service.reject_patch(patch_id, query.bot)
    await query.message.edit_text(text="❌ Патч отклонён", reply_markup=_get_ai_keyboard())


@router.callback_query(F.data.startswith("cancel_"))
async def cb_cancel(query: CallbackQuery) -> None:
    await query.answer("Отменено")
    await query.message.edit_text(text="🤖 <b>AI Agent</b>\nДействие отменено.", reply_markup=_get_ai_keyboard())
