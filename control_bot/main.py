# e:\Projects\FunPayHub\control_bot\main.py
import os
import sys
import logging
import telebot
from telebot import types

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ControlBot")

# Патч для обхода бага с двойным массивом в Telegram API getUpdates
original_get_updates = telebot.apihelper.get_updates
def patched_get_updates(*args, **kwargs):
    res = original_get_updates(*args, **kwargs)
    if res and isinstance(res, list) and len(res) > 0 and isinstance(res[0], list):
        res = [item for sublist in res for item in sublist]
    return res
telebot.apihelper.get_updates = patched_get_updates


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
ADMIN_CHAT_ID = os.environ.get("TG_CHAT_ID", "").strip().strip('"').strip("'")

print(f"[DEBUG] BOT_TOKEN first 5 chars: '{BOT_TOKEN[:5]}'")
print(f"[DEBUG] ADMIN_CHAT_ID loaded: '{ADMIN_CHAT_ID}'")

if not BOT_TOKEN:
    print("Error: TG_BOT_TOKEN is not set in .env! ❌")
    sys.exit(1)

bot = telebot.TeleBot(BOT_TOKEN)

def is_admin(chat_id):
    """Проверяет, является ли пользователь администратором."""
    if not ADMIN_CHAT_ID:
        return True # Если чат не задан, разрешаем всем (в целях MVP/тестов)
    return str(chat_id) == str(ADMIN_CHAT_ID)

# Middleware для логирования всех входящих сообщений в stderr/stdout
@bot.middleware_handler(update_types=['message'])
def log_incoming_message(bot_instance, message):
    print(f"[LOG] Incoming message: chat_id={message.chat.id}, text='{message.text}', is_admin={is_admin(message.chat.id)}")


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    logger.info(f"Command /start or /help received from chat_id={message.chat.id}")
    try:
        if not is_admin(message.chat.id):
            bot.send_message(message.chat.id, "⛔ Доступ запрещен.")
            return
        welcome_text = (
            "🤖 <b>Control Bot v2 (FunPayHub)</b>\n\n"
            "Доступные команды:\n"
            "📊 /status — Проверить статус системы, балансы и ошибки."
        )
        bot.send_message(message.chat.id, welcome_text, parse_mode="HTML")
    except Exception:
        logger.exception("Error in send_welcome handler")

@bot.message_handler(commands=['status'])
def send_status(message):
    logger.info(f"Command /status received from chat_id={message.chat.id}")
    try:
        if not is_admin(message.chat.id):
            bot.send_message(message.chat.id, "⛔ Доступ запрещен.")
            return
        
        status_msg = bot.send_message(message.chat.id, "🔄 Сбор статистики, подождите...")
        
        try:
            # 1. Статус службы
            core = get_core_status()
            core_icon = "🟢" if core.get("active") else "🔴"
            core_sub = str(core.get("sub_status", "")).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            core_info = f"{core_icon} <b>Ядро {core['name']}</b>: {core['status'].upper()} ({core_sub})\nPID: <code>{core['pid']}</code> | Запуск: <code>{core['uptime']}</code>"
            
            # 2. Балансы
            fp = get_funpay_balance()
            if "error" in fp:
                fp_err = str(fp['error']).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                fp_info = f"🔴 <b>FunPay</b>: Ошибка (<code>{fp_err}</code>)"
            else:
                fp_info = f"💰 <b>FunPay</b>: <code>{fp['balance']} {fp['currency']}</code> (Источник: {fp['source']})"
                
            smm = get_smm_balances()
            tb_balance = str(smm.get('twitboost', 'N/A')).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            looksmm_balance = str(smm.get('looksmm', 'N/A')).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            tb_info = f"📶 <b>TwitBoost</b>: <code>{tb_balance}</code>"
            ls_info = f"📶 <b>LookSMM</b>: <code>{looksmm_balance}</code>"
            
            # 3. Статистика
            orders = get_orders_stats()
            orders_info = (
                f"📦 <b>Заказы</b>:\n"
                f"  └ Всего: <code>{orders.get('total', 0)}</code>\n"
                f"  └ Активных: <code>{orders.get('active', 0)}</code>\n"
                f"  └ Выполнено: <code>{orders.get('completed', 0)}</code>\n"
                f"  └ Возвращено: <code>{orders.get('refunded', 0)}</code>"
            )
            
            lots = get_lots_stats()
            lots_info = f"💎 <b>Лоты</b>: всего <code>{lots.get('total', 0)}</code>, активных <code>{lots.get('active', 0)}</code>"
            
            # 4. Ошибки
            errors = get_last_errors()
            if errors:
                escaped_errors = []
                for line in errors:
                    esc = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    escaped_errors.append(f"⚠️ <code>{esc[:100]}</code>")
                errors_str = "\n".join(escaped_errors)
                errors_info = f"🚨 <b>Последние ошибки в логах</b>:\n{errors_str}"
            else:
                errors_info = "✅ <b>Критических ошибок в логах за последнее время не обнаружено.</b>"
                
            # Формируем итоговый текст
            report = (
                f"📊 <b>СТАТУС СИСТЕМЫ FUNPAYHUB</b>\n\n"
                f"{core_info}\n\n"
                f"💳 <b>Балансы</b>:\n"
                f"  ├ {fp_info}\n"
                f"  ├ {tb_info}\n"
                f"  └ {ls_info}\n\n"
                f"{orders_info}\n"
                f"{lots_info}\n\n"
                f"{errors_info}"
            )
            
            bot.edit_message_text(report, chat_id=message.chat.id, message_id=status_msg.message_id, parse_mode="HTML")
            
        except Exception as inner_e:
            logger.exception("Error during status accumulation")
            err_msg = str(inner_e).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            try:
                bot.edit_message_text(f"❌ Ошибка сбора статуса: {err_msg}", chat_id=message.chat.id, message_id=status_msg.message_id, parse_mode="HTML")
            except Exception:
                logger.exception("Failed to send error message to Telegram")
            
    except Exception:
        logger.exception("Fatal error in send_status handler")

if __name__ == "__main__":
    logger.info("Control Bot v2 is starting...")
    bot.infinity_polling()
