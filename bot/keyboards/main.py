from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🚀 Старт системы", callback_data="start_hub"),
            InlineKeyboardButton(text="🛑 Стоп системы", callback_data="stop_hub"),
        ],
        [
            InlineKeyboardButton(text="📊 Отчёт сейчас", callback_data="report"),
            InlineKeyboardButton(text="📜 Логи", callback_data="logs_view"),
        ],
        [
            InlineKeyboardButton(text="💰 Баланс", callback_data="balance"),
            InlineKeyboardButton(text="🔥 Симуляция", callback_data="simulation"),
        ],
        [
            InlineKeyboardButton(text="⚠️ Состояние", callback_data="system_status"),
            InlineKeyboardButton(text="🛒 Лоты", callback_data="lots_menu"),
        ],
        [
            InlineKeyboardButton(text="🤖 AI агент", callback_data="ai_agent"),
            InlineKeyboardButton(text="💳 Кошелёк", callback_data="wallet"),
        ],
        [
            InlineKeyboardButton(text="📈 Статистика", callback_data="stats"),
            InlineKeyboardButton(text="⚙️ Система", callback_data="system"),
        ],
        [
            InlineKeyboardButton(text="🔔 Уведомления", callback_data="notifications"),
            InlineKeyboardButton(text="📦 Плагины", callback_data="plugins_panel"),
        ],
    ])


def get_lots_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Создать все лоты", callback_data="lots_create_all"),
            InlineKeyboardButton(text="🔄 Пересоздать лоты", callback_data="lots_recreate"),
        ],
        [
            InlineKeyboardButton(text="❌ Снять все лоты", callback_data="lots_remove_all"),
            InlineKeyboardButton(text="📋 Проверить лоты", callback_data="lots"),
        ],
        [
            InlineKeyboardButton(text="📈 Статистика лотов", callback_data="lots_stats"),
            InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu"),
        ],
    ])


def get_back_button() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_menu")]
    ])


def get_logs_keyboard(filter_name: str | None = None) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(text="🔴 Ошибки", callback_data="logs_filter_errors"),
            InlineKeyboardButton(text="🟡 Предупреждения", callback_data="logs_filter_warnings"),
        ],
        [
            InlineKeyboardButton(text="🔵 Все", callback_data="logs_filter_all"),
            InlineKeyboardButton(text="🔄 Обновить", callback_data="logs_refresh"),
        ],
    ]
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_plugins_keyboard(autosmm_enabled: bool, autodonate_enabled: bool) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=f"{'🟢' if autosmm_enabled else '🔴'} АвтоСММ",
                callback_data="autosmm",
            ),
            InlineKeyboardButton(
                text=f"{'🟢' if autodonate_enabled else '🔴'} АвтоДонат",
                callback_data="autodonate",
            ),
        ],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")],
    ])


def get_plugin_detail_keyboard(plugin_name: str, is_active: bool) -> InlineKeyboardMarkup:
    alias = "autosmm" if plugin_name == "autosmm_plugin" else "autodonate" if plugin_name == "autodonate_plugin" else plugin_name
    action = "⏹️ Остановить" if is_active else "▶️ Запустить"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=action, callback_data=f"{alias}_toggle")],
        [InlineKeyboardButton(text="🚫 Деактивировать лоты", callback_data=f"{alias}_deactivate")],
        [
            InlineKeyboardButton(text="📊 Статус", callback_data=f"{alias}_status"),
            InlineKeyboardButton(text="⬅️ Назад", callback_data="plugins_panel"),
        ],
    ])


def get_confirm_keyboard(action: str, item_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да", callback_data=f"confirm_{action}_{item_id}"),
            InlineKeyboardButton(text="❌ Нет", callback_data=f"cancel_{action}_{item_id}"),
        ],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")],
    ])


def get_refresh_keyboard(interval: int = 0) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(text="🔄 5с", callback_data="refresh_5"),
            InlineKeyboardButton(text="🔄 10с", callback_data="refresh_10"),
        ],
        [
            InlineKeyboardButton(text="🔄 30с", callback_data="refresh_30"),
            InlineKeyboardButton(text="🔄 60с", callback_data="refresh_60"),
        ],
        [InlineKeyboardButton(text="⏹ Выкл", callback_data="refresh_off")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)
