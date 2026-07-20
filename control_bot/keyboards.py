from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

def main_menu() -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("⚙️ Core (Ядро)", callback_data="menu_core"),
        InlineKeyboardButton("💰 Балансы", callback_data="menu_balances")
    )
    markup.row(
        InlineKeyboardButton("📦 Лоты", callback_data="menu_lots"),
        InlineKeyboardButton("📈 Мониторинг", callback_data="menu_monitor")
    )
    return markup

def core_menu() -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("▶️ Запустить", callback_data="core_start"),
        InlineKeyboardButton("⟳ Перезапустить", callback_data="core_restart")
    )
    markup.row(
        InlineKeyboardButton("⏹️ Остановить", callback_data="core_stop"),
        InlineKeyboardButton("📊 Статус", callback_data="core_status")
    )
    markup.row(
        InlineKeyboardButton("⬅️ Назад в меню", callback_data="back_to_main")
    )
    return markup

def balances_menu() -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("💰 FunPay", callback_data="balance_funpay"),
        InlineKeyboardButton("📶 TwitBoost", callback_data="balance_twitboost")
    )
    markup.row(
        InlineKeyboardButton("📶 LookSMM", callback_data="balance_looksmm"),
        InlineKeyboardButton("⬅️ Назад в меню", callback_data="back_to_main")
    )
    return markup

def monitoring_menu() -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("💻 Ресурсы сервера", callback_data="monitor_resources"),
        InlineKeyboardButton("🚨 Последние логи", callback_data="monitor_logs")
    )
    markup.row(
        InlineKeyboardButton("⬅️ Назад в меню", callback_data="back_to_main")
    )
    return markup

def lots_menu() -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("🔄 Пересоздать лоты", callback_data="lots_recreate"),
        InlineKeyboardButton("📋 Проверить лоты", callback_data="lots_check")
    )
    markup.row(
        InlineKeyboardButton("❌ Снять все лоты", callback_data="lots_remove"),
        InlineKeyboardButton("⬅️ Назад в меню", callback_data="back_to_main")
    )
    return markup

def confirm_menu(action: str) -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("✅ Да, выполнить", callback_data=f"confirm_yes_{action}"),
        InlineKeyboardButton("❌ Нет, отмена", callback_data=f"confirm_no_{action}")
    )
    return markup

def back_to_submenu(submenu: str) -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("⬅️ Назад", callback_data=f"menu_{submenu}")
    )
    return markup
