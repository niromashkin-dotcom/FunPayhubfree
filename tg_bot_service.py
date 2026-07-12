#!/usr/bin/env python3
"""
FunPay Hub Telegram Bot Service
Новый бот с чистой архитектурой - только HTTP API Hub
"""
import os
import sys
import time
import logging
import threading
import http.server
import socketserver
from typing import Optional, Dict, Any
import requests

# ============ CONFIG ============
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8811804174:AAEZyKLzfvd4MZQHdpSFylP5B7YPCcIWkWw")
ADMIN_CHAT_ID = os.environ.get("TELEGRAM_ADMIN_CHAT_ID", "6934895652")
HUB_URL = os.environ.get("FUNPAYHUB_APP_URL", "http://127.0.0.1:5000")
HUB_API_TOKEN = os.environ.get("FUNPAYHUB_API_TOKEN", "")

# ============ LOGGING ============
logger = logging.getLogger("TGBot")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
logger.addHandler(handler)

# ============ HTTP CLIENT ============
class HubClient:
    def __init__(self):
        self.base_url = HUB_URL
        self.api_token = HUB_API_TOKEN
        self.headers = {
            "Content-Type": "application/json",
            "X-API-Token": self.api_token
        }
    
    def get(self, path: str) -> Optional[Dict]:
        try:
            resp = requests.get(f"{self.base_url}{path}", headers=self.headers, timeout=15)
            if resp.status_code == 200:
                return resp.json()
            logger.error(f"GET {path} failed: {resp.status_code}")
            return None
        except Exception as e:
            logger.error(f"GET {path} error: {e}")
            return None
    
    def post(self, path: str, data: Dict = None) -> Optional[Dict]:
        try:
            resp = requests.post(f"{self.base_url}{path}", headers=self.headers, json=data or {}, timeout=30)
            if resp.status_code == 200:
                return resp.json()
            logger.error(f"POST {path} failed: {resp.status_code}")
            return None
        except Exception as e:
            logger.error(f"POST {path} error: {e}")
            return None

hub = HubClient()

# ============ TELEGRAM API ============
def send_message(chat_id: int, text: str, reply_markup=None, parse_mode="HTML"):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        resp = requests.post(url, json=payload, timeout=10)
        return resp.json().get("ok", False)
    except Exception as e:
        logger.error(f"Send message error: {e}")
        return False

def answer_callback(callback_id: str, text: str = None):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery"
        payload = {"callback_query_id": callback_id}
        if text:
            payload["text"] = text
        requests.post(url, json=payload, timeout=5)
    except Exception:
        pass

def edit_message(chat_id: int, message_id: int, text: str, reply_markup=None, parse_mode="HTML"):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": parse_mode
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        logger.error(f"Edit message error: {e}")

# ============ KEYBOARDS ============
def main_menu():
    return {
        "inline_keyboard": [
            [{"text": "🚀 Старт", "callback_data": "start"}, {"text": "🛑 Стоп", "callback_data": "stop"}],
            [{"text": "📊 Отчёт", "callback_data": "report"}, {"text": "📜 Логи", "callback_data": "logs"}],
            [{"text": "💰 Баланс", "callback_data": "balance"}, {"text": "📦 Лоты", "callback_data": "lots"}],
            [{"text": "⚙️ Состояние", "callback_data": "status"}, {"text": "🤖 AI", "callback_data": "ai"}],
            [{"text": "👛 Кошелёк", "callback_data": "wallet"}, {"text": "⚙️ Настройки", "callback_data": "settings"}],
            [{"text": "🔄 Обновить", "callback_data": "refresh"}]
        ]
    }

# ============ FORMATTERS ============
def format_error(title: str, message: str) -> str:
    return f"<b>❌ {title}</b>\n\n{message}\n\n<i>Попробуйте позже.</i>"

def format_balance(data: Dict) -> str:
    if not data:
        return format_error("Баланс", "Данные временно недоступны")
    
    balance = data.get("balance", {})
    total = balance.get("total_rub", 0)
    available = balance.get("available_rub", 0)
    
    return (
        f"<b>💰 Баланс</b>\n\n"
        f"• Доступно: <code>{available:.2f} ₽</code>\n"
        f"• Всего: <code>{total:.2f} ₽</code>"
    )

def format_report(data: Dict) -> str:
    if not data:
        return format_error("Отчёт", "Данные временно недоступны")
    
    stats = data.get("stats", {})
    orders = stats.get("day_count", 0)
    revenue = stats.get("day_sum", 0)
    
    return (
        f"<b>📊 Отчёт за сегодня</b>\n\n"
        f"• Заказов: <code>{orders}</code>\n"
        f"• Выручка: <code>{revenue:.2f} ₽</code>"
    )

def format_status(data: Dict) -> str:
    if not data:
        return format_error("Состояние", "Данные временно недоступны")
    
    status = data.get("status", "unknown")
    plugins = data.get("plugins_count", 0)
    
    return (
        f"<b>⚙️ Состояние системы</b>\n\n"
        f"• Статус: <code>{status}</code>\n"
        f"• Плагинов: <code>{plugins}</code> активных"
    )

def format_lots(data: Dict) -> str:
    if not data:
        return format_error("Лоты", "Данные временно недоступны")
    
    lots = data.get("lots", [])
    active = sum(1 for l in lots if l.get("active", False))
    total = len(lots)
    
    return (
        f"<b>📦 Лоты</b>\n\n"
        f"• Активных: <code>{active}</code>\n"
        f"• Всего: <code>{total}</code>"
    )

def format_logs(data: Dict) -> str:
    if not data:
        return format_error("Логи", "Данные временно недоступны")
    
    logs = data.get("logs", [])[-10:]  # Последние 10
    text = "<b>📜 Логи</b>\n\n"
    for log in logs:
        text += f"<code>{log}</code>\n"
    
    return text

def format_ai(data: Dict) -> str:
    if not data:
        return format_error("AI", "Данные временно недоступны")
    
    status = data.get("status", "unknown")
    return (
        f"<b>🤖 AI Агент</b>\n\n"
        f"• Статус: <code>{status}</code>"
    )

def format_wallet(data: Dict) -> str:
    if not data:
        return format_error("Кошелёк", "Данные временно недоступны")
    
    return (
        f"<b>👛 Кошелёк</b>\n\n"
        f"<code>{data}</code>"
    )

# ============ CALLBACK HANDLERS ============
def handle_callback(callback_data: str, chat_id: int, message_id: int) -> str:
    answer_callback(callback_data, "⏳ Обрабатываю...")
    
    if callback_data == "start":
        result = hub.post("/api/system/start")
        if result and result.get("ok"):
            return "<b>🚀 Система запущена</b>"
        return format_error("Запуск", "Не удалось запустить систему")
    
    elif callback_data == "stop":
        result = hub.post("/api/system/stop")
        if result and result.get("ok"):
            return "<b>🛑 Система остановлена</b>"
        return format_error("Остановка", "Не удалось остановить систему")
    
    elif callback_data == "report":
        data = hub.get("/api/seller/sales")
        return format_report(data)
    
    elif callback_data == "logs":
        data = hub.get("/api/logs/recent")
        return format_logs(data)
    
    elif callback_data == "balance":
        data = hub.get("/api/seller/balance/full")
        return format_balance(data)
    
    elif callback_data == "lots":
        data = hub.get("/api/lots/list")
        return format_lots(data)
    
    elif callback_data == "status":
        data = hub.get("/api/system/health")
        return format_status(data)
    
    elif callback_data == "ai":
        data = hub.get("/api/ai/status")
        return format_ai(data)
    
    elif callback_data == "wallet":
        data = hub.get("/api/seller/wallet")
        return format_wallet(data)
    
    elif callback_data == "settings":
        return "<b>⚙️ Настройки</b>\n\nВ разработке..."
    
    elif callback_data == "refresh":
        return "<b>🔄 Обновлено</b>\n\nДанные обновлены"
    
    return format_error("Ошибка", "Неизвестная команда")

# ============ MESSAGE HANDLERS ============
def handle_message(message: Dict):
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "")
    
    if not chat_id:
        return
    
    # Авторизация
    if chat_id != int(ADMIN_CHAT_ID):
        send_message(chat_id, "<b>⛔ Доступ запрещён</b>")
        return
    
    if text.startswith("/start") or text == "/menu":
        send_message(chat_id, "<b>👋 FunPay Hub Control Panel</b>", reply_markup=main_menu())
    else:
        send_message(chat_id, "<b>❓ Неизвестная команда</b>\n\nИспользуйте /start для меню", reply_markup=main_menu())

# ============ POLLING ============
def polling_loop():
    logger.info("Starting polling...")
    offset = 0
    
    while True:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
            params = {"offset": offset + 1, "timeout": 30, "allowed_updates": ["message", "callback_query"]}
            resp = requests.get(url, params=params, timeout=35)
            
            if resp.status_code != 200:
                logger.error(f"Polling error: {resp.status_code}")
                time.sleep(5)
                continue
            
            data = resp.json()
            if not data.get("ok"):
                logger.error(f"Polling error: {data.get('description')}")
                time.sleep(5)
                continue
            
            updates = data.get("result", [])
            for upd in updates:
                offset = max(offset, upd.get("update_id", 0))
                
                if "message" in upd:
                    handle_message(upd["message"])
                elif "callback_query" in upd:
                    cb = upd["callback_query"]
                    chat_id = cb.get("message", {}).get("chat", {}).get("id")
                    message_id = cb.get("message", {}).get("message_id")
                    callback_id = cb.get("id")
                    callback_data = cb.get("data", "")
                    
                    if chat_id and message_id:
                        result = handle_callback(callback_data, chat_id, message_id)
                        edit_message(chat_id, message_id, result, reply_markup=main_menu())
                    
                    answer_callback(callback_id)
        
        except Exception as e:
            logger.error(f"Polling exception: {e}")
            time.sleep(5)

# ============ HEALTH CHECK ============
class HealthHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"ok","service":"telegram_bot"}')
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        pass

def start_health_server():
    try:
        port = int(os.environ.get("PORT", "10000"))
        socketserver.TCPServer.allow_reuse_address = True
        httpd = socketserver.TCPServer(("0.0.0.0", port), HealthHandler)
        t = threading.Thread(target=httpd.serve_forever, daemon=True)
        t.start()
        logger.info(f"Health check server on port {port}")
    except Exception as e:
        logger.error(f"Health server error: {e}")

# ============ MAIN ============
def main():
    logger.info("Starting FunPay Hub Telegram Bot...")
    logger.info(f"Bot Token: {BOT_TOKEN[:10]}...")
    logger.info(f"Admin Chat ID: {ADMIN_CHAT_ID}")
    logger.info(f"Hub URL: {HUB_URL}")
    
    # Проверяем подключение к Hub
    try:
        health = hub.get("/api/system/health")
        if health:
            logger.info("✅ Hub connected")
        else:
            logger.warning("⚠️ Hub not responding")
    except Exception as e:
        logger.error(f"Hub connection error: {e}")
    
    # Удаляем webhook
    try:
        requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook", timeout=5)
        logger.info("Webhook removed")
    except Exception as e:
        logger.warning(f"Webhook removal error: {e}")
    
    # Запускаем health check
    start_health_server()
    
    # Запускаем polling
    polling_loop()

if __name__ == "__main__":
    main()
