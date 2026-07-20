# e:\Projects\FunPayHub\control_bot\main.py
import os
import sys
import telebot
from telebot import types

# Добавляем корень проекта в пути импорта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from control_bot.monitor import (
    load_environment,
    get_core_status,
    get_funpay_balance,
    get_smm_balances,
    get_orders_stats,
    get_lots_stats,
    get_last_errors
)

# Загружаем окружение
load_environment()

BOT_TOKEN = os.environ.get("TG_BOT_TOKEN", "")
ADMIN_CHAT_ID = os.environ.get("TG_CHAT_ID", "")

if not BOT_TOKEN:
    print("Error: TG_BOT_TOKEN is not set in .env! ❌")
    sys.exit(1)

bot = telebot.TeleBot(BOT_TOKEN)

def is_admin(chat_id):
    """Проверяет, является ли пользователь администратором."""
    if not ADMIN_CHAT_ID:
        return True # Если чат не задан, разрешаем всем (в целях MVP/тестов)
    return str(chat_id) == str(ADMIN_CHAT_ID)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    if not is_admin(message.chat.id):
        bot.reply_to(message, "⛔ Доступ запрещен.")
        return
    welcome_text = (
        "🤖 **Control Bot v2 (FunPayHub)**\n\n"
        "Доступные команды:\n"
        "📊 /status — Проверить статус системы, балансы и ошибки."
    )
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

@bot.message_handler(commands=['status'])
def send_status(message):
    if not is_admin(message.chat.id):
        bot.reply_to(message, "⛔ Доступ запрещен.")
        return
    
    status_msg = bot.reply_to(message, "🔄 Сбор статистики, подождите...")
    
    try:
        # 1. Статус службы
        core = get_core_status()
        core_icon = "🟢" if core.get("active") else "🔴"
        core_info = f"{core_icon} **Ядро {core['name']}**: {core['status'].upper()} ({core['sub_status']})\nPID: `{core['pid']}` | Запуск: `{core['uptime']}`"
        
        # 2. Балансы
        fp = get_funpay_balance()
        if "error" in fp:
            fp_info = f"🔴 **FunPay**: Ошибка ({fp['error']})"
        else:
            fp_info = f"💰 **FunPay**: `{fp['balance']} {fp['currency']}` (Источник: {fp['source']})"
            
        smm = get_smm_balances()
        tb_info = f"📶 **TwitBoost**: `{smm['twitboost']}`"
        ls_info = f"📶 **LookSMM**: `{smm['looksmm']}`"
        
        # 3. Статистика
        orders = get_orders_stats()
        orders_info = (
            f"📦 **Заказы**:\n"
            f"  └ Всего: `{orders['total']}`\n"
            f"  └ Активных: `{orders['active']}`\n"
            f"  └ Выполнено: `{orders['completed']}`\n"
            f"  └ Возвращено: `{orders['refunded']}`"
        )
        
        lots = get_lots_stats()
        lots_info = f"💎 **Лоты**: всего `{lots['total']}`, активных `{lots['active']}`"
        
        # 4. Ошибки
        errors = get_last_errors()
        if errors:
            errors_str = "\n".join([f"⚠️ `{line[:100]}`" for line in errors])
            errors_info = f"🚨 **Последние ошибки в логах**:\n{errors_str}"
        else:
            errors_info = "✅ **Критических ошибок в логах за последнее время не обнаружено.**"
            
        # Формируем итоговый текст
        report = (
            f"📊 **СТАТУС СИСТЕМЫ FUNPAYHUB**\n\n"
            f"{core_info}\n\n"
            f"💳 **Балансы**:\n"
            f"  ├ {fp_info}\n"
            f"  ├ {tb_info}\n"
            f"  └ {ls_info}\n\n"
            f"{orders_info}\n"
            f"{lots_info}\n\n"
            f"{errors_info}"
        )
        
        bot.edit_message_text(report, chat_id=message.chat.id, message_id=status_msg.message_id, parse_mode="Markdown")
        
    except Exception as e:
        bot.edit_message_text(f"❌ Ошибка сбора статуса: {e}", chat_id=message.chat.id, message_id=status_msg.message_id)

if __name__ == "__main__":
    print("Control Bot v2 is starting...")
    bot.infinity_polling()
