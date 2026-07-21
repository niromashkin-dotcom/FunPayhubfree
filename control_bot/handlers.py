import logging
import telebot
from typing import Any
from functools import wraps
from control_bot.services.core_service import CoreService
from control_bot.services.monitor_service import MonitorService
from control_bot import keyboards

logger = logging.getLogger("ControlBot.Handlers")

def escape_html(text: Any) -> str:
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def safe_send_message(bot: telebot.TeleBot, chat_id: int, text: str, **kwargs) -> Any:
    try:
        print(f"[DEBUG] Sending message to {chat_id}: {text[:50]}...")
        msg = bot.send_message(chat_id, text, **kwargs)
        print(f"[DEBUG] SUCCESS: Message sent (id={msg.message_id})")
        return msg
    except Exception as e:
        print(f"[ERROR] FAIL send_message: {e}")
        logger.exception("send_message failed")
        return None

def safe_edit_message(bot: telebot.TeleBot, text: str, chat_id: int, message_id: int, **kwargs) -> Any:
    try:
        print(f"[DEBUG] Editing message {message_id} in {chat_id}...")
        msg = bot.edit_message_text(text, chat_id=chat_id, message_id=message_id, **kwargs)
        print(f"[DEBUG] SUCCESS: Message edited")
        return msg
    except Exception as e:
        print(f"[ERROR] FAIL edit_message_text: {e}")
        logger.exception("edit_message_text failed")
        return None

def safe_answer_callback(bot: telebot.TeleBot, callback_id: str, text: str = None, show_alert: bool = False):
    try:
        bot.answer_callback_query(callback_id, text=text, show_alert=show_alert)
        print(f"[DEBUG] SUCCESS: Answered callback {callback_id}")
    except Exception as e:
        print(f"[ERROR] FAIL answer_callback_query: {e}")
        logger.exception("answer_callback_query failed")

def register_handlers(bot: telebot.TeleBot, core_service: CoreService, monitor_service: MonitorService, admin_chat_id: str):
    
    def is_admin(chat_id: int) -> bool:
        if not admin_chat_id:
            return True
        return str(chat_id) == str(admin_chat_id)

    def admin_check(func):
        """Декоратор для проверки прав администратора в хэндлерах."""
        @wraps(func)
        def wrapper(message_or_call, *args, **kwargs):
            chat_id = message_or_call.chat.id if hasattr(message_or_call, "chat") else message_or_call.message.chat.id
            is_adm = is_admin(chat_id)
            print(f"[DEBUG] admin_check wrapper called for {func.__name__}. chat_id={chat_id}, is_admin={is_adm}")
            if not is_adm:
                print(f"[DEBUG] Access denied for chat_id={chat_id}")
                if hasattr(message_or_call, "chat"):
                    safe_send_message(bot, chat_id, "⛔ Доступ запрещен.")
                else:
                    safe_answer_callback(bot, message_or_call.id, "⛔ Доступ запрещен.", show_alert=True)
                return
            return func(message_or_call, *args, **kwargs)
        return wrapper

    # ==========================================
    # ВХОДНЫЕ КОМАНДЫ (COMMANDS)
    # ==========================================

    @bot.message_handler(commands=['start', 'help'])
    @admin_check
    def send_welcome(message):
        print(f"[DEBUG] Entering send_welcome for chat_id={message.chat.id}")
        # ТЕСТ: Отправка чистого текста без HTML и без клавиатуры
        safe_send_message(bot, message.chat.id, "TEST")

    @bot.message_handler(commands=['status'])
    @admin_check
    def cmd_status(message):
        print(f"[DEBUG] Entering cmd_status. chat_id={message.chat.id}")
        msg = safe_send_message(bot, message.chat.id, "🔄 Сбор информации, подождите...")
        if not msg:
            print("[ERROR] Failed to send initial status message")
            return

        core = core_service.status()
        core_icon = "🟢" if core.get("active") else "🔴"
        core_sub = escape_html(core.get("sub_status", ""))
        
        fp = monitor_service.get_funpay_balance()
        if "error" in fp:
            fp_info = f"🔴 FunPay: Ошибка (<code>{escape_html(fp['error'])}</code>)"
        else:
            fp_info = f"💰 FunPay: <code>{fp['balance']} {fp['currency']}</code>"

        text = (
            f"📊 <b>КРАТКИЙ СТАТУС</b>\n\n"
            f"{core_icon} <b>Ядро</b>: {core['status'].upper()} ({core_sub})\n"
            f"{fp_info}"
        )
        safe_edit_message(bot, text, chat_id=message.chat.id, message_id=msg.message_id, parse_mode="HTML")

    # ==========================================
    # НАВИГАЦИЯ МЕЖДУ МЕНЮ (NAVIGATION CALLBACKS)
    # ==========================================

    @bot.callback_query_handler(func=lambda call: call.data == "back_to_main")
    @admin_check
    def cb_back_to_main(call):
        safe_answer_callback(bot, call.id)
        safe_edit_message(
            bot,
            "🤖 <b>Панель управления FunPayHub v2</b>\n\n"
            "Выберите интересующий вас раздел:",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode="HTML",
            reply_markup=keyboards.main_menu()
        )

    @bot.callback_query_handler(func=lambda call: call.data == "menu_core")
    @admin_check
    def cb_menu_core(call):
        safe_answer_callback(bot, call.id)
        safe_edit_message(
            bot,
            "⚙️ <b>Управление ядром (systemd)</b>\n\n"
            "Здесь вы можете запустить, остановить или перезапустить службу ядра.",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode="HTML",
            reply_markup=keyboards.core_menu()
        )

    @bot.callback_query_handler(func=lambda call: call.data == "menu_balances")
    @admin_check
    def cb_menu_balances(call):
        safe_answer_callback(bot, call.id)
        safe_edit_message(
            bot,
            "💰 <b>Балансы систем</b>\n\n"
            "Выберите систему для просмотра баланса:",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode="HTML",
            reply_markup=keyboards.balances_menu()
        )

    @bot.callback_query_handler(func=lambda call: call.data == "menu_monitor")
    @admin_check
    def cb_menu_monitor(call):
        safe_answer_callback(bot, call.id)
        safe_edit_message(
            bot,
            "📈 <b>Мониторинг сервера</b>\n\n"
            "Выберите метрику для просмотра:",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode="HTML",
            reply_markup=keyboards.monitoring_menu()
        )

    @bot.callback_query_handler(func=lambda call: call.data == "menu_lots")
    @admin_check
    def cb_menu_lots(call):
        safe_answer_callback(bot, call.id)
        safe_edit_message(
            bot,
            "📦 <b>Управление лотами</b>\n\n"
            "Здесь вы можете генерировать, публиковать и снимать лоты с FunPay.",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode="HTML",
            reply_markup=keyboards.lots_menu()
        )

    # ==========================================
    # ДЕЙСТВИЯ И ПОДМЕНЮ (ACTIONS & SUBMENUS)
    # ==========================================

    @bot.callback_query_handler(func=lambda call: call.data == "core_status")
    @admin_check
    def cb_core_status(call):
        safe_answer_callback(bot, call.id)
        core = core_service.status()
        icon = "🟢" if core.get("active") else "🔴"
        sub = escape_html(core.get("sub_status", ""))
        text = (
            f"⚙️ <b>СТАТУС ЯДРА</b>\n"
            f"────────────────────\n"
            f"👤 Служба: <code>{core['name']}</code>\n"
            f"📊 Состояние: {icon} <b>{core['status'].upper()}</b> ({sub})\n"
            f"🆔 Main PID: <code>{core['pid']}</code>\n"
            f"⏱️ Запуск: <code>{core['uptime']}</code>"
        )
        safe_edit_message(
            bot,
            text,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode="HTML",
            reply_markup=keyboards.back_to_submenu("core")
        )

    @bot.callback_query_handler(func=lambda call: call.data == "core_start")
    @admin_check
    def cb_core_start(call):
        safe_answer_callback(bot, call.id)
        safe_edit_message(bot, "🔄 Запуск ядра, пожалуйста, подождите...", chat_id=call.message.chat.id, message_id=call.message.message_id)
        ok = core_service.start()
        res_text = "🟢 Ядро успешно запущено!" if ok else "🔴 Не удалось запустить ядро. Проверьте системные логи."
        safe_edit_message(bot, res_text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=keyboards.back_to_submenu("core"))

    @bot.callback_query_handler(func=lambda call: call.data in ["core_stop", "core_restart"])
    @admin_check
    def cb_core_dangerous(call):
        safe_answer_callback(bot, call.id)
        action = call.data
        action_name = "остановить" if action == "core_stop" else "перезапустить"
        safe_edit_message(
            bot,
            f"⚠️ <b>Подтверждение действия</b>\n\n"
            f"Вы действительно хотите <b>{action_name}</b> службу ядра?",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode="HTML",
            reply_markup=keyboards.confirm_menu(action)
        )

    @bot.callback_query_handler(func=lambda call: call.data == "balance_funpay")
    @admin_check
    def cb_balance_funpay(call):
        safe_answer_callback(bot, call.id)
        fp = monitor_service.get_funpay_balance()
        if "error" in fp:
            text = f"💰 <b>Баланс FunPay</b>\n\n🔴 Ошибка получения: <code>{escape_html(fp['error'])}</code>"
        else:
            text = (
                f"💰 <b>Баланс FunPay</b>\n\n"
                f"💵 Доступно: <code>{fp['balance']} {fp['currency']}</code>\n"
                f"ℹ️ Источник: {fp['source']}"
            )
        safe_edit_message(
            bot,
            text,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode="HTML",
            reply_markup=keyboards.back_to_submenu("balances")
        )

    @bot.callback_query_handler(func=lambda call: call.data in ["balance_twitboost", "balance_looksmm"])
    @admin_check
    def cb_balance_smm(call):
        safe_answer_callback(bot, call.id)
        smm = monitor_service.get_smm_balances()
        if call.data == "balance_twitboost":
            text = f"📶 <b>Баланс TwitBoost</b>\n\n💳 Баланс: <code>{escape_html(smm['twitboost'])}</code>"
        else:
            text = f"📶 <b>Баланс LookSMM</b>\n\n💳 Баланс: <code>{escape_html(smm['looksmm'])}</code>"
        
        safe_edit_message(
            bot,
            text,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode="HTML",
            reply_markup=keyboards.back_to_submenu("balances")
        )

    @bot.callback_query_handler(func=lambda call: call.data == "monitor_resources")
    @admin_check
    def cb_monitor_resources(call):
        safe_answer_callback(bot, call.id)
        res = monitor_service.get_system_resources()
        text = (
            f"💻 <b>РЕСУРСЫ СЕРВЕРА</b>\n"
            f"────────────────────\n"
            f"⚡ CPU: <code>{res['cpu']}</code>\n"
            f"💾 RAM (использовано/всего): <code>{res['ram']}</code>\n"
            f"💽 Диск (использовано/всего): <code>{res['disk']}</code>\n"
            f"⏱️ Аптайм VPS: <code>{res['uptime']}</code>"
        )
        safe_edit_message(
            bot,
            text,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode="HTML",
            reply_markup=keyboards.back_to_submenu("monitor")
        )

    @bot.callback_query_handler(func=lambda call: call.data in ["monitor_logs", "logs_refresh"])
    @admin_check
    def cb_monitor_logs(call):
        safe_answer_callback(bot, call.id)
        errors = monitor_service.get_last_errors(limit=20)
        
        if errors:
            escaped_errors = []
            for line in errors:
                esc = escape_html(line)
                escaped_errors.append(f"⚠️ <code>{esc[:90]}</code>")
            errors_str = "\n".join(escaped_errors)
            text = f"🚨 <b>ПОСЛЕДНИЕ ОШИБКИ ИЗ ЛОГОВ</b>\n────────────────────\n{errors_str}"
        else:
            text = "✅ <b>Критических ошибок в логах за последнее время не обнаружено.</b>"
            
        markup = telebot.types.InlineKeyboardMarkup()
        markup.row(
            telebot.types.InlineKeyboardButton("🔄 Обновить", callback_data="logs_refresh"),
            telebot.types.InlineKeyboardButton("⬅️ Назад", callback_data="menu_monitor")
        )
        
        safe_edit_message(
            bot,
            text,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode="HTML",
            reply_markup=markup
        )

    @bot.callback_query_handler(func=lambda call: call.data == "lots_check")
    @admin_check
    def cb_lots_check(call):
        safe_answer_callback(bot, call.id)
        lots = monitor_service.get_lots_stats()
        text = (
            f"📋 <b>СТАТУС ЛОТОВ НА FUNPAY</b>\n"
            f"────────────────────\n"
            f"💎 Всего лотов в базе: <code>{lots['total']}</code>\n"
            f"🟢 Активных на продаже: <code>{lots['active']}</code>"
        )
        safe_edit_message(
            bot,
            text,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode="HTML",
            reply_markup=keyboards.back_to_submenu("lots")
        )

    @bot.callback_query_handler(func=lambda call: call.data in ["lots_recreate", "lots_remove"])
    @admin_check
    def cb_lots_dangerous(call):
        safe_answer_callback(bot, call.id)
        action = call.data
        action_name = "пересоздать (деактивировать и создать заново) все" if action == "lots_recreate" else "снять (деактивировать) все"
        safe_edit_message(
            bot,
            f"⚠️ <b>Подтверждение действия</b>\n\n"
            f"Вы действительно хотите <b>{action_name}</b> лоты на FunPay?",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode="HTML",
            reply_markup=keyboards.confirm_menu(action)
        )

    # ==========================================
    # ПОДТВЕРЖДЕНИЯ ДЕЙСТВИЙ (CONFIRMATIONS)
    # ==========================================

    @bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_yes_"))
    @admin_check
    def cb_confirm_yes(call):
        safe_answer_callback(bot, call.id)
        action = call.data.replace("confirm_yes_", "")
        safe_edit_message(bot, "🔄 Выполнение операции, пожалуйста, подождите...", chat_id=call.message.chat.id, message_id=call.message.message_id)
        
        if action == "core_stop":
            ok = core_service.stop()
            text = "🛑 Служба ядра успешно остановлена!" if ok else "🔴 Не удалось остановить службу ядра."
            submenu = "core"
        elif action == "core_restart":
            ok = core_service.restart()
            text = "⟳ Служба ядра успешно перезапущена!" if ok else "🔴 Не удалось перезапустить службу ядра."
            submenu = "core"
        elif action == "lots_recreate":
            ok = monitor_service.recreate_all_lots()
            text = "🔄 Лоты успешно пересозданы (деактивированы и запущены заново)!" if ok else "🔴 Возникли ошибки при пересоздании лотов."
            submenu = "lots"
        elif action == "lots_remove":
            ok = monitor_service.deactivate_all_lots()
            text = "❌ Все лоты успешно деактивированы и сняты с продажи!" if ok else "🔴 Возникли ошибки при снятии лотов."
            submenu = "lots"
        else:
            text = "❓ Неизвестное действие."
            submenu = "main"

        markup = keyboards.back_to_submenu(submenu) if submenu != "main" else keyboards.main_menu()
        safe_edit_message(bot, text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_no_"))
    @admin_check
    def cb_confirm_no(call):
        safe_answer_callback(bot, call.id)
        action = call.data.replace("confirm_no_", "")
        
        if action.startswith("core_"):
            submenu = "core"
            text = "⚙️ <b>Управление ядром (systemd)</b>\n\nЗдесь вы можете запустить, остановить или перезапустить службу ядра."
            markup = keyboards.core_menu()
        elif action.startswith("lots_"):
            submenu = "lots"
            text = "📦 <b>Управление лотами</b>\n\nЗдесь вы можете генерировать, публиковать и снимать лоты с FunPay."
            markup = keyboards.lots_menu()
        else:
            submenu = "main"
            text = "🤖 <b>Панель управления FunPayHub v2</b>\n\nВыберите интересующий вас раздел:"
            markup = keyboards.main_menu()
            
        safe_edit_message(
            bot,
            text,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode="HTML",
            reply_markup=markup
        )
