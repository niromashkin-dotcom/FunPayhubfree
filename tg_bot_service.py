#!/usr/bin/env python3
"""
tg_bot_service.py

Standalone Telegram Bot Service for FunPay Hub.
Controls the hub as an independent process (not tied to app runtime).

Usage:
    python tg_bot_service.py

Environment:
    TELEGRAM_BOT_TOKEN - bot token (overrides config)
"""
import json
import os
import sys
import time
import subprocess
import atexit
import signal
import logging
import threading
import psutil
import telebot
from runtime.http_client import HTTPClient, HTTPClientError
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import bcrypt

# ============ LOGGING ============
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_PATH = os.path.join(LOG_DIR, "tg_bot.log")

logger = logging.getLogger("TGBotService")
logger.setLevel(logging.DEBUG)
_fh = logging.FileHandler(LOG_PATH, encoding="utf-8")
_fh.setLevel(logging.DEBUG)
_fh.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
logger.addHandler(_fh)
_ch = logging.StreamHandler(sys.stdout)
_ch.setLevel(logging.INFO)
_ch.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
logger.addHandler(_ch)

# ============ CONFIG ============
HUB_URL = os.getenv("FUNPAYHUB_APP_URL", "http://127.0.0.1:5000")
HUB_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "funpayhub_main.py")
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
PID_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tg_bot_service.pid")

if not BOT_TOKEN:
    try:
        cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "configs", "plugins", "telegram_notifier_plugin.json")
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        BOT_TOKEN = cfg.get("bot_token", "").strip()
    except Exception:
        pass

if not BOT_TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN not set. Set env var or configs/plugins/telegram_notifier_plugin.json")
    sys.exit(1)

# ============ PID LOCK ============
def cleanup_pid():
    try:
        if os.path.exists(PID_FILE):
            with open(PID_FILE, "r", encoding="utf-8") as f:
                pid = int(f.read().strip())
            if pid == os.getpid() or not psutil.pid_exists(pid):
                os.remove(PID_FILE)
    except Exception:
        pass

def check_pid_lock():
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r", encoding="utf-8") as f:
                pid = int(f.read().strip())
            if psutil.pid_exists(pid) and pid != os.getpid():
                try:
                    p = psutil.Process(pid)
                    cmd = " ".join(p.info.get('cmdline', []) or [])
                    if "tg_bot_service" in cmd:
                        logger.error(f"Another instance is already running (PID {pid}). Exiting.")
                        sys.exit(1)
                except Exception:
                    pass
        except Exception:
            pass

check_pid_lock()
with open(PID_FILE, "w", encoding="utf-8") as f:
    f.write(str(os.getpid()))

def sig_handler(sig, frame):
    logger.info(f"Received signal {sig}, shutting down...")
    cleanup_pid()
    sys.exit(0)

signal.signal(signal.SIGINT, sig_handler)
signal.signal(signal.SIGTERM, sig_handler)
atexit.register(cleanup_pid)

# ============ HUB CONTROLLER ============
class HubController:
    def is_hub_running(self):
        for proc in psutil.process_iter(['name', 'cmdline']):
            try:
                cmdline = proc.info.get('cmdline') or []
                if any('funpayhub_main.py' in str(cmd) for cmd in cmdline):
                    return True, proc.pid
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False, None

    def start_hub(self):
        running, _ = self.is_hub_running()
        if running:
            return False, "Hub уже запущен"
        try:
            subprocess.Popen(
                [sys.executable, HUB_SCRIPT],
                cwd=os.path.dirname(os.path.abspath(__file__)),
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
            logger.info("Hub started via button")
            return True, "FunPay Hub запущен"
        except Exception as e:
            logger.error(f"Failed to start Hub: {e}")
            return False, f"Ошибка запуска: {e}"

    def stop_hub(self):
        running, pid = self.is_hub_running()
        if not running:
            return False, "Hub не запущен"
        try:
            p = psutil.Process(pid)
            p.terminate()
            p.wait(timeout=10)
            logger.info(f"Hub stopped (PID {pid})")
            return True, "FunPay Hub остановлен"
        except Exception as e:
            logger.error(f"Failed to stop Hub: {e}")
            return False, f"Ошибка остановки: {e}"

    def call_api(self, endpoint, method="GET", payload=None):
        url = HUB_URL + endpoint
        _http = HTTPClient()
        try:
            if method == "GET":
                data = _http.get(url, timeout=15)
            else:
                data = _http.post(url, json=payload or {}, timeout=15)
            if data is not None:
                return True, data
            return False, {"error": "Empty response"}
        except HTTPClientError:
            return False, "Hub не отвечает (возможно не запущен)"
        except Exception as e:
            logger.error(f"API call failed {endpoint}: {e}")
            return False, f"Ошибка: {e}"

controller = HubController()
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML", allow_sending_without_reply=True, num_threads=2)

# ============ FLASK PING ENDPOINT ============
try:
    from flask import Flask as _FlaskForPing
    ping_flask = _FlaskForPing("tg_bot_ping")
    @ping_flask.route("/bot/ping_order", methods=["POST"])
    def _bot_ping_order():
        try:
            data = request.get_json(silent=True) or {}
            text = data.get("text", "🔔 Ping from FunPay Hub")
            chat_id = data.get("chat_id") or _get_admin_chat_id()
            if chat_id and text:
                _safe_send(chat_id, text)
            return jsonify({"ok": True})
        except Exception as e:
            logger.error(f"/bot/ping_order error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    def _get_admin_chat_id():
        try:
            cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "configs", "plugins", "telegram_notifier_plugin.json")
            with open(cfg_path, encoding="utf-8") as f:
                return json.load(f).get("chat_id", "")
        except Exception:
            return ""

    def _start_ping_server():
        try:
            t = threading.Thread(target=lambda: ping_flask.run(host="127.0.0.1", port=5001, debug=False, use_reloader=False), daemon=True)
            t.start()
            logger.info("Ping server started on http://127.0.0.1:5001")
        except Exception as e:
            logger.error(f"Ping server failed: {e}")
except Exception as e:
    ping_flask = None
    def _start_ping_server():
        pass

# ============ KEYBOARDS ============
def main_menu():
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("🚀 Старт системы", callback_data="start_hub"),
        InlineKeyboardButton("🛑 Стоп системы", callback_data="stop_hub")
    )
    kb.add(
        InlineKeyboardButton("📊 Отчёт сейчас", callback_data="report"),
        InlineKeyboardButton("📜 Логи", callback_data="logs_view")
    )
    kb.add(
        InlineKeyboardButton("💰 Баланс", callback_data="balance"),
        InlineKeyboardButton("🔥 Симуляция", callback_data="simulation")
    )
    kb.add(
        InlineKeyboardButton("⚠️ Состояние", callback_data="system_status"),
        InlineKeyboardButton("📦 Лоты", callback_data="create_lots")
    )
    kb.add(
        InlineKeyboardButton("🤖 AI агент", callback_data="ai_agent"),
        InlineKeyboardButton("💳 Кошелёк", callback_data="wallet")
    )
    return kb

def _logs_keyboard(current_filter=None):
    kb = InlineKeyboardMarkup()
    f = current_filter or "all"
    kb.add(
        InlineKeyboardButton("🔴 Только ошибки", callback_data="logs_filter_errors"),
        InlineKeyboardButton("🟡 Только предупреждения", callback_data="logs_filter_warnings")
    )
    kb.add(
        InlineKeyboardButton("🔵 Все", callback_data="logs_filter_all"),
        InlineKeyboardButton("🔄 Обновить", callback_data="logs_refresh")
    )
    kb.add(InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu"))
    return kb

def _plugins_keyboard(plugins_data):
    kb = InlineKeyboardMarkup()
    autosmm = plugins_data.get("autosmm", {})
    autodonate = plugins_data.get("autodonate", {})
    status_smm = "🟢" if autosmm.get("enabled") else "🔴"
    status_donate = "🟢" if autodonate.get("enabled") else "🔴"
    kb.add(
        InlineKeyboardButton(f"{status_smm} АвтоСММ", callback_data="autosmm"),
        InlineKeyboardButton(f"{status_donate} АвтоДонат", callback_data="autodonate")
    )
    kb.add(InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu"))
    return kb

def _plugin_detail_keyboard(plugin_name, is_active):
    kb = InlineKeyboardMarkup()
    action = "⏹️ Остановить" if is_active else "▶️ Запустить"
    kb.add(
        InlineKeyboardButton(action, callback_data=f"{plugin_name}_toggle")
    )
    kb.add(
        InlineKeyboardButton("🚫 Деактивировать лоты", callback_data=f"{plugin_name}_deactivate")
    )
    kb.add(
        InlineKeyboardButton("📊 Статус", callback_data=f"{plugin_name}_status"),
        InlineKeyboardButton("⬅️ Назад", callback_data="plugins_panel")
    )
    return kb

def _format_logs_summary(data):
    if not isinstance(data, dict):
        return "📜 Логи:\nНет данных"
    lines = data.get("lines", [])
    if not lines:
        return "📜 Логи:\nНет записей"
    text = f"📜 <b>Логи</b> (фильтр: {data.get('filter', 'all')})\n"
    for l in lines[:50]:
        lvl = l.get("level", "INFO")
        message = l.get("message", "")
        ts = l.get("timestamp", "")
        if lvl == "ERROR":
            text += f"🔴 `{ts}` {message}\n"
        elif lvl == "WARNING":
            text += f"🟡 `{ts}` {message}\n"
        elif lvl == "INFO":
            text += f"🔵 `{ts}` {message}\n"
        else:
            text += f"⚪ `{ts}` {message}\n"
    text += f"\nВсего записей: {data.get('total', len(lines))}"
    return text

def _format_plugins_summary(data):
    if not isinstance(data, dict):
        return "🔌 Плагины:\nНет данных"
    autosmm = data.get("autosmm", {})
    autodonate = data.get("autodonate", {})
    lines = ["🔌 <b>Плагины</b>:", ""]
    for name, info in [("АвтоСММ", autosmm), ("АвтоДонат", autodonate)]:
        status = "🟢 АКТИВЕН" if info.get("enabled") else "🔴 ОТКЛЮЧЁН"
        lines.append(f"<b>{name}</b> — {status}")
        lots = info.get("lots_count", 0)
        lines.append(f"  Лотов: {lots}")
    return "\n".join(lines)

# ============ AUTHENTICATION ============
def load_authorized_users():
    """Загружает список авторизованных пользователей"""
    try:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tg_bot", "authorized_users.json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return set(data.get("authorized_users", []))
        return set()
    except Exception as e:
        logger.error(f"Failed to load authorized users: {e}")
        return set()

def is_user_authorized(user_id):
    """Проверяет, авторизован ли пользователь"""
    return user_id in load_authorized_users()

def persist_authorized_user(user_id):
    """Сохраняет user_id в authorized_users.json, чтобы авторизация переживала перезапуск бота"""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tg_bot", "authorized_users.json")
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                config = json.load(f)
        else:
            config = {}
        users = set(config.get("authorized_users", []))
        users.add(user_id)
        config["authorized_users"] = sorted(users)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp_path = path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
        return True
    except Exception as e:
        logger.error(f"Failed to persist authorized user {user_id}: {e}")
        return False

def get_admin_chat_id() -> str:
    # First try environment variable (set in .env)
    admin_id = os.environ.get("TELEGRAM_ADMIN_CHAT_ID", "").strip()
    if admin_id:
        return admin_id
    # Fallback to plugin config (for backward compatibility)
    try:
        cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "configs", "plugins", "telegram_notifier_plugin.json")
        with open(cfg_path, encoding="utf-8") as f:
            return json.load(f).get("chat_id", "")
    except Exception:
        return ""

def auth_middleware(func):
    """Декоратор для проверки авторизации"""
    def wrapper(message):
        admin_id = get_admin_chat_id()
        if admin_id and str(message.from_user.id) == str(admin_id):
            return func(message)
        if message.chat.type == "private" and not is_user_authorized(message.from_user.id):
            logger.warning(f"Unauthorized access attempt from user_id={message.from_user.id}")
            try:
                bot.send_message(message.chat.id, "❌ Доступ запрещён. Вы не авторизованы.")
            except Exception:
                pass
            return
        return func(message)
    return wrapper

def auth_callback_middleware(func):
    """Декоратор для проверки авторизации callback-запросов"""
    def wrapper(call):
        admin_id = get_admin_chat_id()
        if admin_id and str(call.from_user.id) == str(admin_id):
            return func(call)
        if not is_user_authorized(call.from_user.id):
            logger.warning(f"Unauthorized callback attempt from user_id={call.from_user.id}")
            try:
                bot.answer_callback_query(call.id, "❌ Доступ запрещён. Вы не авторизованы.", show_alert=True)
            except Exception:
                pass
            return
        return func(call)
    return wrapper

# ============ HANDLERS ============
@bot.message_handler(commands=["start", "menu"])
@auth_middleware
def cmd_start(message):
    logger.info(f"START COMMAND RECEIVED user={message.from_user.id} chat={message.chat.id}")
    try:
        bot.send_message(message.chat.id, "FunPayHub Control Panel", reply_markup=main_menu())
    except Exception as e:
        logger.error(f"Failed to send start reply: {e}")

@bot.message_handler(commands=["auth"])
def cmd_auth(message):
    """Авторизация через пароль"""
    logger.info(f"/auth from user_id={message.from_user.id}")
    
    if not message.text or len(message.text.split()) < 2:
        bot.reply_to(message, "❌ Использование: /auth <пароль>")
        return
    
    password = message.text.split()[1]
    # Загружаем конфиг
    try:
        auth_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tg_bot", "authorized_users.json")
        if os.path.exists(auth_path):
            with open(auth_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            
            stored_hash = config.get("password_hash", "")
            enable_auth = config.get("enable_password_auth", True)
            
            if not enable_auth:
                bot.reply_to(message, "⚠️ Авторизация по паролю отключена в конфигурации.")
                return
            
            # Проверка пароля с использованием bcrypt
            try:
                if bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8')):
                    # Пароль верный — сохраняем пользователя в whitelist на диск,
                    # чтобы авторизация не терялась при перезапуске бота
                    user_id = message.from_user.id
                    if persist_authorized_user(user_id):
                        logger.info(f"User {user_id} успешно авторизован (сохранено на диск)")
                        bot.reply_to(
                            message,
                            f"✅ Авторизация успешна! Ваш user_id: {user_id}\n"
                            f"Доступ сохранён и переживёт перезапуск бота."
                        )
                    else:
                        logger.error(f"User {user_id} прошёл пароль, но не удалось сохранить в файл")
                        bot.reply_to(
                            message,
                            "⚠️ Пароль верный, но не удалось сохранить доступ на диск. "
                            "Проверьте права на запись в tg_bot/authorized_users.json."
                        )
                else:
                    logger.warning(f"Неверный пароль от user_id={message.from_user.id}")
                    bot.reply_to(message, "❌ Неверный пароль.")
            except Exception as e:
                logger.error(f"Ошибка проверки пароля: {e}")
                bot.reply_to(message, "❌ Ошибка проверки пароля.")
        else:
            bot.reply_to(message, "❌ Файл конфигурации авторизации не найден.")
    except Exception as e:
        logger.error(f"Auth error: {e}")
        bot.reply_to(message, "❌ Ошибка авторизации.")

@bot.message_handler(commands=["ping"])
@auth_middleware
def cmd_ping(message):
    logger.info(f"/ping from chat_id={message.chat.id}")
    try:
        bot.reply_to(message, "pong ✅")
    except Exception as e:
        logger.error(f"Failed to reply to ping: {e}")

@bot.message_handler(func=lambda m: True)
def debug_all_messages(message):
    try:
        logger.info(f"UPDATE RECEIVED type={message.content_type} chat_id={message.chat.id} user_id={message.from_user.id}")
    except Exception:
        pass

def _safe_edit(bot, chat_id, message_id, text, reply_markup=None, parse_mode=None):
    """Безопасное редактирование сообщения с обработкой ошибок"""
    try:
        # Обрезаем до безопасной длины
        if len(text) > 4000:
            text = text[:3990] + "\n\n... (обрезано)"

        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode  # ВАЖНО: None = без markdown
        )
    except Exception as e:
        error_msg = str(e)
        # Игнорируем "message is not modified" — это не ошибка
        if "message is not modified" in error_msg:
            logger.debug(f"Message not modified (ignored): {error_msg}")
            return
        # Игнорируем "message can't be edited" (старые сообщения)
        if "message can't be edited" in error_msg:
            logger.warning(f"Cannot edit message {message_id}: {error_msg}")
            return
        # Остальные ошибки логируем
        logger.error(f"edit_message_text failed: {error_msg}")

def _safe_send(chat_id, text, reply_markup=None):
    try:
        if len(text) > 4000:
            text = text[:3990] + "\n\n... (обрезано)"
        bot.send_message(chat_id, text, reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"send_message failed: {e}")

@bot.callback_query_handler(func=lambda call: True)
@auth_callback_middleware
def callback_handler(call):
    try:
        logger.info(f"Callback: chat_id={call.message.chat.id} data={call.data}")
        bot.answer_callback_query(call.id)
        cmd = call.data
        chat_id = call.message.chat.id
        mid = call.message.message_id

        if cmd == "start_hub":
            try:
                ok, msg = controller.start_hub()
                text = f"🚀 {msg}"
                reply = main_menu() if ok else None
                _safe_edit(bot, chat_id, mid, text, reply)
            except Exception as e:
                logger.error(f"start_hub error: {e}")
                _safe_edit(bot, chat_id, mid, f"🚀 Ошибка: {e}", main_menu())

        elif cmd == "stop_hub":
            try:
                ok, msg = controller.stop_hub()
                text = f"🛑 {msg}"
                _safe_edit(bot, chat_id, mid, text, main_menu())
            except Exception as e:
                logger.error(f"stop_hub error: {e}")
                _safe_edit(bot, chat_id, mid, f"🛑 Ошибка: {e}", main_menu())

        elif cmd == "market_status":
            try:
                ok, result = controller.call_api("/api/market/analyze_niches_global", "POST", {"budget": 500, "force_refresh": False})
                text = f"📊 Ниши (глобальный поиск):\n<pre>{json.dumps(result, indent=2, ensure_ascii=False)}</pre>" if ok else f"❌ {result}"
                _safe_edit(bot, chat_id, mid, text, main_menu())
            except Exception as e:
                logger.error(f"market_status error: {e}")
                _safe_edit(bot, chat_id, mid, f"❌ Ошибка: {e}", main_menu())

        elif cmd == "balance":
            try:
                ok, result = controller.call_api("/api/seller/balance/full")
                if ok:
                    rub = result.get("available_rub") or result.get("balance") or result.get("total_rub", 0)
                    text = f"💰 Баланс:\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
                    _safe_edit(bot, chat_id, mid, text, reply_markup=main_menu())
                else:
                    _safe_edit(bot, chat_id, mid, f"❌ {result}", reply_markup=main_menu())
            except Exception as e:
                logger.error(f"balance error: {e}")
                _safe_edit(bot, chat_id, mid, f"❌ Ошибка: {e}", parse_mode=None)

        elif cmd == "report":
            try:
                ok, result = controller.call_api("/api/seller/overview")
                text = f"📋 Отчёт:\n<pre>{json.dumps(result, indent=2, ensure_ascii=False)}</pre>" if ok else f"❌ {result}"
                _safe_edit(bot, chat_id, mid, text, main_menu())
            except Exception as e:
                logger.error(f"report error: {e}")
                _safe_edit(bot, chat_id, mid, f"❌ Ошибка: {e}", main_menu())

        elif cmd == "system_status":
            try:
                ok, result = controller.call_api("/api/system/health")
                if ok:
                    lines = ["🔧 <b>Состояние системы</b>:", ""]
                    for k in ["flask", "plugin_manager", "seller_service", "eventbus"]:
                        v = result.get(k, "unknown")
                        if v and ("ok" in str(v).lower() or "active" in str(v).lower()):
                            emoji = "✅"
                        elif v and "not_connected" in str(v).lower():
                            emoji = "⚠️"
                        else:
                            emoji = "🔴"
                        lines.append(f"{emoji} <b>{k}</b>: {v}")
                    lines.append("")
                    lines.append(f"🕐 <i>{result.get('timestamp', '')}</i>")
                    text = "\n".join(lines)
                else:
                    text = f"❌ Ошибка получения статуса: {result}"
                _safe_edit(bot, chat_id, mid, text, main_menu())
            except Exception as e:
                logger.error(f"system_status error: {e}")
                _safe_edit(bot, chat_id, mid, f"❌ Ошибка: {e}", main_menu())

        elif cmd == "create_lots":
            try:
                ok, result = controller.call_api("/dashboard/api/generate_lots", "POST", {
                    "copies_per_position": 15,
                    "max_price": 150,
                    "plugins": ["autosmm", "autodonate"],
                    "dry_run": True
                })
                if ok:
                    text = f"📦 {result.get('message', 'Лоты созданы')}"
                else:
                    text = f"❌ {result}"
                _safe_edit(bot, chat_id, mid, text, main_menu())
            except Exception as e:
                logger.error(f"create_lots error: {e}")
                _safe_edit(bot, chat_id, mid, f"❌ Ошибка: {e}", main_menu())

        elif cmd == "remove_all_lots":
            try:
                ok, result = controller.call_api("/dashboard/api/remove_lots", "POST", {
                    "plugins": ["autosmm", "autodonate"]
                })
                if ok:
                    text = f"🗑️ Лоты сняты!\n📈 АвтоСММ: снято {result.get('autosmm_removed', 0)} лотов\n💰 АвтоДонат: снято {result.get('autodonate_removed', 0)} лотов\nИтого: {result.get('total_removed', 0)} лотов снято"
                else:
                    text = f"❌ {result}"
                _safe_edit(bot, chat_id, mid, text, main_menu())
            except Exception as e:
                logger.error(f"remove_all_lots error: {e}")
                _safe_edit(bot, chat_id, mid, f"❌ Ошибка: {e}", main_menu())

        elif cmd == "auto_create_toggle":
            try:
                ok, result = controller.call_api("/api/plugins/autosmm/toggle_auto", "POST", {"enabled": True})
                if ok:
                    enabled = result.get("enabled", False)
                    status = "включено" if enabled else "выключено"
                    text = f"✅ Авто-создание {status}"
                else:
                    text = f"❌ {result}"
                _safe_edit(bot, chat_id, mid, text, main_menu())
            except Exception as e:
                logger.error(f"auto_create_toggle error: {e}")
                _safe_edit(bot, chat_id, mid, f"❌ Ошибка: {e}", main_menu())

        elif cmd == "simulation":
            try:
                ok, result = controller.call_api("/dashboard/api/run_simulation", "POST")
                text = f"🧪 Симуляция:\n<pre>{json.dumps(result, indent=2, ensure_ascii=False)}</pre>" if ok else f"❌ {result}"
                _safe_edit(bot, chat_id, mid, text, main_menu())
            except Exception as e:
                logger.error(f"simulation error: {e}")
                _safe_edit(bot, chat_id, mid, f"❌ Ошибка: {e}", main_menu())

        elif cmd == "logs_view":
            try:
                ok, result = controller.call_api("/dashboard/api/logs", "GET", payload=None)
                if ok:
                    text = _format_logs_summary(result)
                    filters = result.get("available_filters") if isinstance(result, dict) else None
                    kb = _logs_keyboard(result.get("filter") if isinstance(result, dict) else None)
                    _safe_edit(bot, chat_id, mid, text, kb)
                else:
                    _safe_edit(bot, chat_id, mid, f"❌ Не удалось загрузить логи: {result}", main_menu())
            except Exception as e:
                logger.error(f"logs_view error: {e}")
                _safe_edit(bot, chat_id, mid, f"❌ Ошибка: {e}", main_menu())

        elif cmd == "plugins_panel":
            try:
                ok, result = controller.call_api("/dashboard/api/plugins/summary", "GET")
                if ok and isinstance(result, dict):
                    text = _format_plugins_summary(result)
                    kb = _plugins_keyboard(result)
                    _safe_edit(bot, chat_id, mid, text, kb)
                else:
                    _safe_edit(bot, chat_id, mid, "❌ Не удалось загрузить список плагинов", main_menu())
            except Exception as e:
                logger.error(f"plugins_panel error: {e}")
                _safe_edit(bot, chat_id, mid, f"❌ Ошибка: {e}", main_menu())

        elif cmd == "logs_filter_errors":
            try:
                ok, result = controller.call_api("/dashboard/api/logs?level=ERROR", "GET")
                if ok:
                    text = _format_logs_summary(result)
                    _safe_edit(bot, chat_id, mid, text, _logs_keyboard("ERROR"))
                else:
                    _safe_edit(bot, chat_id, mid, f"❌ {result}", main_menu())
            except Exception as e:
                _safe_edit(bot, chat_id, mid, f"❌ Ошибка: {e}", main_menu())

        elif cmd == "logs_filter_warnings":
            try:
                ok, result = controller.call_api("/dashboard/api/logs?level=WARNING", "GET")
                if ok:
                    text = _format_logs_summary(result)
                    _safe_edit(bot, chat_id, mid, text, _logs_keyboard("WARNING"))
                else:
                    _safe_edit(bot, chat_id, mid, f"❌ {result}", main_menu())
            except Exception as e:
                _safe_edit(bot, chat_id, mid, f"❌ Ошибка: {e}", main_menu())

        elif cmd == "logs_filter_all":
            try:
                ok, result = controller.call_api("/dashboard/api/logs", "GET")
                if ok:
                    text = _format_logs_summary(result)
                    _safe_edit(bot, chat_id, mid, text, _logs_keyboard("all"))
                else:
                    _safe_edit(bot, chat_id, mid, f"❌ {result}", main_menu())
            except Exception as e:
                _safe_edit(bot, chat_id, mid, f"❌ Ошибка: {e}", main_menu())

        elif cmd == "ai_agent":
            try:
                ok, result = controller.call_api("/api/ai/status", "GET")
                if ok:
                    status = result.get("status", "unknown")
                    text = f"🤖 <b>AI Agent статус</b>:\n<pre>{json.dumps(result, indent=2, ensure_ascii=False)}</pre>"
                else:
                    text = f"❌ {result}"
                _safe_edit(bot, chat_id, mid, text, main_menu())
            except Exception as e:
                logger.error(f"ai_agent error: {e}")
                _safe_edit(bot, chat_id, mid, f"❌ Ошибка: {e}", main_menu())

        elif cmd == "wallet":
            try:
                ok, result = controller.call_api("/api/wallet/balance", "GET")
                if ok:
                    balance = result.get("balance", 0)
                    currency = result.get("currency", "₽")
                    text = f"💳 <b>Кошелёк</b>:\nБаланс: {balance:.2f} {currency}\nДетали:\n<pre>{json.dumps(result, indent=2, ensure_ascii=False)}</pre>"
                else:
                    text = f"❌ {result}"
                _safe_edit(bot, chat_id, mid, text, main_menu())
            except Exception as e:
                logger.error(f"wallet error: {e}")
                _safe_edit(bot, chat_id, mid, f"❌ Ошибка: {e}", main_menu())

        elif cmd == "settings":
            # Placeholder for settings
            text = "⚙ <b>Настройки</b>:\nЗдесь будут настройки бота (в разработке)."
            _safe_edit(bot, chat_id, mid, text, main_menu())

        elif cmd == "logs_refresh":
            try:
                ok, result = controller.call_api("/dashboard/api/logs", "GET")
                if ok:
                    text = _format_logs_summary(result)
                    _safe_edit(bot, chat_id, mid, text, _logs_keyboard(result.get("filter") if isinstance(result, dict) else None))
                else:
                    _safe_edit(bot, chat_id, mid, f"❌ {result}", main_menu())
            except Exception as e:
                _safe_edit(bot, chat_id, mid, f"❌ Ошибка: {e}", main_menu())

        elif cmd in ("autosmm", "autodonate"):
            try:
                ok, result = controller.call_api(f"/dashboard/api/plugins/{cmd}/status", "GET")
                if ok and isinstance(result, dict):
                    is_active = result.get("enabled", False)
                    text = (
                        f"<b>{'📈 АвтоСММ' if cmd == 'autosmm' else '💰 АвтоДонат'}</b>\n"
                        f"Статус: {'🟢 АКТИВЕН' if is_active else '🔴 ОТКЛЮЧЁН'}\n"
                        f"Обработано заказов: {result.get('orders_count', 0)}\n"
                        f"Ошибок: {result.get('errors', 0)}\n"
                    )
                    _safe_edit(bot, chat_id, mid, text, _plugin_detail_keyboard(cmd, is_active))
                else:
                    _safe_edit(bot, chat_id, mid, f"❌ Не удалось загрузить статус: {result}", _plugins_keyboard({}))
            except Exception as e:
                logger.error(f"plugin detail error: {e}")
                _safe_edit(bot, chat_id, mid, f"❌ Ошибка: {e}", main_menu())

        elif cmd in ("autosmm_toggle", "autodonate_toggle"):
            plugin = cmd.replace("_toggle", "")
            try:
                ok, result = controller.call_api(f"/dashboard/api/plugins/{plugin}/toggle", "POST")
                if ok:
                    is_active = result.get("enabled", False)
                    status = "запущен" if is_active else "остановлен"
                    text = f"✅ {'📈 АвтоСММ' if plugin == 'autosmm' else '💰 АвтоДонат'} {status}"
                    kb = _plugin_detail_keyboard(plugin, is_active)
                    _safe_edit(bot, chat_id, mid, text, kb)
                else:
                    _safe_edit(bot, chat_id, mid, f"❌ Ошибка: {result}", main_menu())
            except Exception as e:
                _safe_edit(bot, chat_id, mid, f"❌ Ошибка: {e}", main_menu())

        elif cmd in ("autosmm_deactivate", "autodonate_deactivate"):
            plugin = cmd.replace("_deactivate", "")
            try:
                ok, result = controller.call_api(f"/dashboard/api/plugins/{plugin}/deactivate_lots", "POST")
                if ok:
                    text = f"🗑️ Снято лотов: {result.get('removed', 0)} для {'📈 АвтоСММ' if plugin == 'autosmm' else '💰 АвтоДонат'}"
                    kb = _plugin_detail_keyboard(plugin, True)
                    _safe_edit(bot, chat_id, mid, text, kb)
                else:
                    _safe_edit(bot, chat_id, mid, f"❌ Ошибка: {result}", main_menu())
            except Exception as e:
                _safe_edit(bot, chat_id, mid, f"❌ Ошибка: {e}", main_menu())

        elif cmd in ("autosmm_status", "autodonate_status"):
            plugin = cmd.replace("_status", "")
            try:
                ok, result = controller.call_api(f"/dashboard/api/plugins/{plugin}/status", "GET")
                if ok:
                    text = f"📊 Статус {'📈 АвтоСММ' if plugin == 'autosmm' else '💰 АвтоДонат'}:\n<pre>{json.dumps(result, indent=2, ensure_ascii=False)}</pre>"
                    kb = _plugin_detail_keyboard(plugin, result.get("enabled", False))
                    _safe_edit(bot, chat_id, mid, text, kb)
                else:
                    _safe_edit(bot, chat_id, mid, f"❌ Ошибка: {result}", main_menu())
            except Exception as e:
                _safe_edit(bot, chat_id, mid, f"❌ Ошибка: {e}", main_menu())

        elif cmd == "ai_agent":
            try:
                ok, result = controller.call_api("/api/ai/status", "GET")
                if ok:
                    status = result.get("status", "unknown")
                    text = f"🤖 <b>AI Agent статус</b>:\n<pre>{json.dumps(result, indent=2, ensure_ascii=False)}</pre>"
                else:
                    text = f"❌ {result}"
                _safe_edit(bot, chat_id, mid, text, main_menu())
            except Exception as e:
                logger.error(f"ai_agent error: {e}")
                _safe_edit(bot, chat_id, mid, f"❌ Ошибка: {e}", main_menu())

        elif cmd == "wallet":
            try:
                ok, result = controller.call_api("/api/wallet/balance", "GET")
                if ok:
                    balance = result.get("balance", 0)
                    currency = result.get("currency", "₽")
                    text = f"💳 <b>Кошелёк</b>:\nБаланс: {balance:.2f} {currency}\nДетали:\n<pre>{json.dumps(result, indent=2, ensure_ascii=False)}</pre>"
                else:
                    text = f"❌ {result}"
                _safe_edit(bot, chat_id, mid, text, main_menu())
            except Exception as e:
                logger.error(f"wallet error: {e}")
                _safe_edit(bot, chat_id, mid, f"❌ Ошибка: {e}", main_menu())

        elif cmd == "settings":
            # Placeholder for settings
            text = "⚙ Настройки пока не реализованы."
            _safe_edit(bot, chat_id, mid, text, main_menu())

        elif cmd == "back_to_menu":
            _safe_edit(bot, chat_id, mid, "🎮 FunPay Hub Control Panel", main_menu())

        else:
            _safe_edit(bot, chat_id, mid, "❓ Неизвестная команда", main_menu())

    except Exception as e:
        logger.error(f"Callback error: {e}", exc_info=True)
        try:
            _safe_edit(bot, call.message.chat.id, call.message.message_id, f"❌ Ошибка: {e}", main_menu())
        except Exception:
            pass

# ============ MAIN ============
def main():
    """Запуск бота"""
    logger.info("Starting Telegram Bot Service...")
    logger.info("ADMIN LOADED: chat_id: ******")

    # Удаляем webhook (на всякий случай)
    try:
        bot.remove_webhook()
        logger.info("Webhook removed")
    except Exception as e:
        logger.warning(f"Failed to remove webhook: {e}")

    # Проверяем что Hub запущен
    running, _ = controller.is_hub_running()
    if running:
        logger.info("✅ Hub is already running")
    else:
        logger.info("ℹ️ Hub is not running. Use Start button.")

    # Запускаем ping server в фоне
    _start_ping_server()

    # Обработчик ошибок polling
    def handle_polling_exception(exception):
        error_msg = str(exception)
        if "409" in error_msg and "Conflict" in error_msg:
            logger.error("🚨 CONFLICT detected! Killing other instances...")
            # Пытаемся убить другие процессы
            current_pid = os.getpid()
            for proc in psutil.process_iter(['pid', 'cmdline']):
                try:
                    if proc.pid != current_pid:
                        cmdline = ' '.join(proc.cmdline() or [])
                        if 'tg_bot_service' in cmdline:
                            logger.info(f"💀 Killing PID {proc.pid}")
                            proc.kill()
                except Exception:
                    pass
            time.sleep(3)
            return True  # Продолжить polling

        logger.error(f"Polling error: {exception}")
        time.sleep(5)
        return True

    # Запускаем polling с обработчиком ошибок
    logger.info("Starting infinity_polling...")
    bot.infinity_polling(
        exception_handler=handle_polling_exception,
        timeout=60,
        long_polling_timeout=60,
        allowed_updates=['message', 'callback_query']
    )

if __name__ == "__main__":
    main()
