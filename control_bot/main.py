import os
import sys
import logging
import telebot

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

from control_bot.services.core_service import CoreService
from control_bot.services.monitor_service import MonitorService
from control_bot.handlers import register_handlers

# Инициализируем сервисы
monitor_service = MonitorService()
# Загружаем имя службы из конфига
core_service_name = monitor_service.config.get("core_service_name", "funpayhub-core")
core_service = CoreService(service_name=core_service_name)

BOT_TOKEN = os.environ.get("TG_BOT_TOKEN", "")
ADMIN_CHAT_ID = os.environ.get("TG_CHAT_ID", "").strip().strip('"').strip("'")

print(f"[DEBUG] BOT_TOKEN first 5 chars: '{BOT_TOKEN[:5]}'")
print(f"[DEBUG] ADMIN_CHAT_ID loaded: '{ADMIN_CHAT_ID}'")

if not BOT_TOKEN:
    print("Error: TG_BOT_TOKEN is not set in .env! ❌")
    sys.exit(1)

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
    logger.info("Control Bot v2 (Modular Panel) is starting...")
    bot.infinity_polling()
