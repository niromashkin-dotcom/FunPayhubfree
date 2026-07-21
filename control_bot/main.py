import sys
import telebot
import requests

from control_bot.config import BOT_TOKEN, ADMIN_CHAT_ID
from control_bot.logger import logger

if not BOT_TOKEN:
    logger.error("Error: BOT_TOKEN is empty! ❌")
    sys.exit(1)

logger.info(f"Loaded BOT_TOKEN (starts with: '{BOT_TOKEN[:8]}...')")
logger.info(f"Loaded ADMIN_CHAT_ID: '{ADMIN_CHAT_ID}'")

# Проверка связи с Telegram API
try:
    auth_check = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getMe", timeout=10).json()
    if auth_check.get("ok"):
        bot_user = auth_check["result"]
        logger.info(f"Bot connected: @{bot_user.get('username')} (ID: {bot_user.get('id')})")
    else:
        logger.error(f"Telegram API getMe failed: {auth_check}")
except Exception:
    logger.exception("Failed to connect to Telegram API")

bot = telebot.TeleBot(BOT_TOKEN)

def is_admin(chat_id: int) -> bool:
    if not ADMIN_CHAT_ID:
        return True
    return str(chat_id) == str(ADMIN_CHAT_ID)

@bot.message_handler(commands=['start'])
def handle_start(message):
    logger.info(f"Received /start (msg_id={message.message_id}) from chat_id={message.chat.id}")
    if not is_admin(message.chat.id):
        logger.warning(f"Access denied for chat_id={message.chat.id}")
        return
    
    logger.info(f"[BEFORE SEND] Replying to /start msg_id={message.message_id} in {message.chat.id}")
    try:
        msg = bot.reply_to(message, "👋 Привет! Я Control Bot v2.")
        logger.info(f"[AFTER SEND] Reply sent successfully. message_id={msg.message_id}")
    except Exception:
        logger.exception("Failed to send /start reply")

@bot.message_handler(commands=['status'])
def handle_status(message):
    logger.info(f"Received /status (msg_id={message.message_id}) from chat_id={message.chat.id}")
    if not is_admin(message.chat.id):
        logger.warning(f"Access denied for chat_id={message.chat.id}")
        return

    logger.info(f"[BEFORE SEND] Replying to /status msg_id={message.message_id} in {message.chat.id}")
    try:
        msg = bot.reply_to(message, "📊 Бот активен и работает!")
        logger.info(f"[AFTER SEND] Reply sent successfully. message_id={msg.message_id}")
    except Exception:
        logger.exception("Failed to send /status reply")

if __name__ == "__main__":
    logger.info("Removing webhook before starting polling...")
    try:
        bot.remove_webhook(drop_pending_updates=True)
        logger.info("Webhook removed successfully.")
    except Exception:
        logger.exception("Failed to remove webhook")

    logger.info("Starting infinity_polling...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
