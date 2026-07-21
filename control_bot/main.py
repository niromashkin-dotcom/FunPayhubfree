import asyncio
import sys
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command

from control_bot.config import BOT_TOKEN, ADMIN_CHAT_ID
from control_bot.logger import logger

if not BOT_TOKEN:
    logger.error("Error: BOT_TOKEN is empty! ❌")
    sys.exit(1)

logger.info(f"Loaded BOT_TOKEN (starts with: '{BOT_TOKEN[:8]}...')")
logger.info(f"Loaded ADMIN_CHAT_ID: '{ADMIN_CHAT_ID}'")

# Инициализируем бота и диспетчер aiogram
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def is_admin(chat_id: int) -> bool:
    if not ADMIN_CHAT_ID:
        return True
    return str(chat_id) == str(ADMIN_CHAT_ID)

@dp.message(CommandStart())
async def handle_start(message: types.Message):
    logger.info(f"Received /start (msg_id={message.message_id}) from chat_id={message.chat.id}")
    if not is_admin(message.chat.id):
        logger.warning(f"Access denied for chat_id={message.chat.id}")
        return
    
    logger.info(f"[BEFORE SEND] Replying to /start in {message.chat.id}")
    try:
        msg = await message.answer("👋 Привет! Я Control Bot v2 (aiogram 3.x).")
        logger.info(f"[AFTER SEND] Reply sent successfully via aiogram. message_id={msg.message_id}")
    except Exception:
        logger.exception("Failed to send /start reply")

@dp.message(Command("status"))
async def handle_status(message: types.Message):
    logger.info(f"Received /status (msg_id={message.message_id}) from chat_id={message.chat.id}")
    if not is_admin(message.chat.id):
        logger.warning(f"Access denied for chat_id={message.chat.id}")
        return

    logger.info(f"[BEFORE SEND] Replying to /status in {message.chat.id}")
    try:
        msg = await message.answer("📊 Бот активен и работает на движке aiogram 3!")
        logger.info(f"[AFTER SEND] Reply sent successfully via aiogram. message_id={msg.message_id}")
    except Exception:
        logger.exception("Failed to send /status reply")

async def main():
    # Аутентификация бота
    try:
        bot_info = await bot.get_me()
        logger.info(f"Aiogram Bot authenticated: @{bot_info.username} (ID: {bot_info.id})")
    except Exception:
        logger.exception("Failed to authenticate bot with Telegram API")

    # Сброс активного вебхука и застрявших обновлений
    logger.info("Clearing active webhook and pending updates...")
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Webhook cleared.")

    logger.info("Starting aiogram 3.x polling loop...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
