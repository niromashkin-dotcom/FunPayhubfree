import os
import sys
import logging
import telebot
import requests

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ControlBot")

# Добавляем корень проекта в пути импорта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from control_bot.services.core_service import CoreService
from control_bot.services.monitor_service import MonitorService
from control_bot.handlers import register_handlers

# Инициализируем сервисы
monitor_service = MonitorService()
core_service_name = monitor_service.config.get("core_service_name", "funpayhub-core")
core_service = CoreService(service_name=core_service_name)

# Приоритет: CONTROL_BOT_TOKEN из env -> telegram_token из config -> TG_BOT_TOKEN из env
BOT_TOKEN = (
    os.environ.get("CONTROL_BOT_TOKEN") 
    or monitor_service.config.get("telegram_token") 
    or os.environ.get("TG_BOT_TOKEN", "")
).strip().strip('"').strip("'")

ADMIN_CHAT_ID = (
    os.environ.get("ADMIN_CHAT_ID") 
    or monitor_service.config.get("admin_chat_id") 
    or os.environ.get("TG_CHAT_ID", "")
).strip().strip('"').strip("'")

print(f"[DEBUG] Full BOT_TOKEN loaded: '{BOT_TOKEN}'")
print(f"[DEBUG] ADMIN_CHAT_ID loaded: '{ADMIN_CHAT_ID}'")

if not BOT_TOKEN:
    logger.error("Error: CONTROL_BOT_TOKEN / telegram_token is not set! ❌")
    sys.exit(1)

# Проверка подключения через requests напрямую
try:
    res = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getMe", timeout=10).json()
    if res.get("ok"):
        bot_info = res["result"]
        logger.info(f"Bot authenticated successfully: @{bot_info.get('username')} (ID: {bot_info.get('id')})")
    else:
        logger.error(f"Failed to authenticate bot via Telegram API: {res}")
except Exception:
    logger.exception("Network check failed during bot startup")

bot = telebot.TeleBot(BOT_TOKEN)

# Middleware для логирования всех входящих обновлений в консоль
@bot.middleware_handler(update_types=['message'])
def log_incoming_message(bot_instance, message):
    is_adm = (not ADMIN_CHAT_ID) or (str(message.chat.id) == str(ADMIN_CHAT_ID))
    print(f"[LOG] Incoming message: chat_id={message.chat.id}, text='{message.text}', is_admin={is_adm}")

@bot.middleware_handler(update_types=['callback_query'])
def log_incoming_callback(bot_instance, call):
    is_adm = (not ADMIN_CHAT_ID) or (str(call.message.chat.id) == str(ADMIN_CHAT_ID))
    print(f"[LOG] Incoming callback: chat_id={call.message.chat.id}, data='{call.data}', is_admin={is_adm}")

# Регистрируем хэндлеры
register_handlers(
    bot=bot,
    core_service=core_service,
    monitor_service=monitor_service,
    admin_chat_id=ADMIN_CHAT_ID
)

if __name__ == "__main__":
    logger.info("Removing any active webhooks before starting polling...")
    try:
        bot.remove_webhook(drop_pending_updates=True)
        logger.info("Webhook removed successfully.")
    except Exception:
        logger.exception("Failed to remove webhook")

    logger.info("Control Bot v2 (Modular Panel) is starting polling...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
