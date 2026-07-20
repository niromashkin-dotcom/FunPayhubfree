import logging
import telebot
from typing import Any
from control_bot.services.core_service import CoreService
from control_bot.services.monitor_service import MonitorService
from control_bot import keyboards

logger = logging.getLogger("ControlBot.Handlers")

def escape_html(text: Any) -> str:
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def register_handlers(bot: telebot.TeleBot, core_service: CoreService, monitor_service: MonitorService, admin_chat_id: str):
    
    def is_admin(chat_id: int) -> bool:
        if not admin_chat_id:
            return True
        return str(chat_id) == str(admin_chat_id)

    def admin_check(func):
        """Декоратор для проверки прав администратора в хэндлерах."""
        def wrapper(message_or_call, *args, **kwargs):
            chat_id = message_or_call.chat.id if hasattr(message_or_call, "chat") else message_or_call.message.chat.id
            if not is_admin(chat_id):
                if hasattr(message_or_call, "chat"):
                    bot.send_message(chat_id, "⛔ Доступ запрещен.")
                else:
                    bot.answer_callback_query(message_or_call.id, "⛔ Доступ запрещен.", show_alert=True)
                return
            return func(message_or_call, *args, **kwargs)
        return wrapper

    # ==========================================
    # ВХОДНЫЕ КОМАНДЫ (COMMANDS)
    # ==========================================

    @bot.message_handler(commands=['start', 'help'])
    @admin_check
    def send_welcome(message):
        bot.send_message(
            message.chat.id,
            "🤖 <b>Панель управления FunPayHub v2</b>\n\n"
            "Выберите интересующий вас раздел:",
            parse_mode="HTML",
            reply_markup=keyboards.main_menu()
        )

    @bot.message_handler(commands=['status'])
    @admin_check
    def cmd_status(message):
        # Быстрый вывод краткого статуса как в Phase 1
        msg = bot.send_message(message.chat.id, "🔄 Сбор информации, подождите...")
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
        bot.edit_message_text(text, chat_id=message.chat.id, message_id=msg.message_id, parse_mode="HTML")

    # ==========================================
    # НАВИГАЦИЯ МЕЖДУ МЕНЮ (NAVIGATION CALLBACKS)
    # ==========================================

    @bot.callback_query_handler(func=lambda call: call.data == "back_to_main")
    @admin_check
    def cb_back_to_main(call):
        bot.answer_callback_query(call.id)
        bot.edit_message_text(
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
        bot.answer_callback_query(call.id)
        bot.edit_message_text(
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
        bot.answer_callback_query(call.id)
        bot.edit_message_text(
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
        bot.answer_callback_query(call.id)
        bot.edit_message_text(
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
        bot.answer_callback_query(call.id)
        bot.edit_message_text(
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

    # --- Подменю: Core ---

    @bot.callback_query_handler(func=lambda call: call.data == "core_status")
    @admin_check
    def cb_core_status(call):
        bot.answer_callback_query(call.id)
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
        bot.edit_message_text(
            text,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode="HTML",
            reply_markup=keyboards.back_to_submenu("core")
        )

    @bot.callback_query_handler(func=lambda call: call.data == "core_start")
    @admin_check
    def cb_core_start(call):
        bot.answer_callback_query(call.id)
        bot.edit_message_text("🔄 Запуск ядра, пожалуйста, подождите...", chat_id=call.message.chat.id, message_id=call.message.message_id)
        ok = core_service.start()
        res_text = "🟢 Ядро успешно запущено!" if ok else "🔴 Не удалось запустить ядро. Проверьте системные логи."
        bot.edit_message_text(res_text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=keyboards.back_to_submenu("core"))

    @bot.callback_query_handler(func=lambda call: call.data in ["core_stop", "core_restart"])
    @admin_check
    def cb_core_dangerous(call):
        bot.answer_callback_query(call.id)
        action = call.data
        action_name = "остановить" if action == "core_stop" else "перезапустить"
        bot.edit_message_text(
            f"⚠️ <b>Подтверждение действия</b>\n\n"
            f"Вы действительно хотите <b>{action_name}</b> службу ядра?",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode="HTML",
            reply_markup=keyboards.confirm_menu(action)
        )

    # --- Подменю: Балансы ---

    @bot.callback_query_handler(func=lambda call: call.data == "balance_funpay")
    @admin_check
    def cb_balance_funpay(call):
        bot.answer_callback_query(call.id)
        fp = monitor_service.get_funpay_balance()
        if "error" in fp:
            text = f"💰 <b>Баланс FunPay</b>\n\n🔴 Ошибка получения: <code>{escape_html(fp['error'])}</code>"
        else:
            text = (
                f"💰 <b>Баланс FunPay</b>\n\n"
                f"💵 Доступно: <code>{fp['balance']} {fp['currency']}</code>\n"
                f"ℹ️ Источник: {fp['source']}"
            )
        bot.edit_message_text(
            text,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode="HTML",
            reply_markup=keyboards.back_to_submenu("balances")
        )

    @bot.callback_query_handler(func=lambda call: call.data in ["balance_twitboost", "balance_looksmm"])
    @admin_check
    def cb_balance_smm(call):
        bot.answer_callback_query(call.id)
        smm = monitor_service.get_smm_balances()
        if call.data == "balance_twitboost":
            text = f"📶 <b>Баланс TwitBoost</b>\n\n💳 Баланс: <code>{escape_html(smm['twitboost'])}</code>"
        else:
            text = f"📶 <b>Баланс LookSMM</b>\n\n💳 Баланс: <code>{escape_html(smm['looksmm'])}</code>"
        
        bot.edit_message_text(
            text,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode="HTML",
            reply_markup=keyboards.back_to_submenu("balances")
        )

    # --- Подменю: Мониторинг ---

    @bot.callback_query_handler(func=lambda call: call.data == "monitor_resources")
    @admin_check
    def cb_monitor_resources(call):
        bot.answer_callback_query(call.id)
        res = monitor_service.get_system_resources()
        text = (
            f"💻 <b>РЕСУРСЫ СЕРВЕРА</b>\n"
            f"────────────────────\n"
            f"⚡ CPU: <code>{res['cpu']}</code>\n"
            f"💾 RAM (использовано/всего): <code>{res['ram']}</code>\n"
            f"💽 Диск (использовано/всего): <code>{res['disk']}</code>\n"
            f"⏱️ Аптайм VPS: <code>{res['uptime']}</code>"
        )
        bot.edit_message_text(
            text,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode="HTML",
            reply_markup=keyboards.back_to_submenu("monitor")
        )

    @bot.callback_query_handler(func=lambda call: call.data in ["monitor_logs", "logs_refresh"])
    @admin_check
    def cb_monitor_logs(call):
        bot.answer_callback_query(call.id)
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
        
        bot.edit_message_text(
            text,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode="HTML",
            reply_markup=markup
        )

    # --- Подменю: Лоты ---

    @bot.callback_query_handler(func=lambda call: call.data == "lots_check")
    @admin_check
    def cb_lots_check(call):
        bot.answer_callback_query(call.id)
        lots = monitor_service.get_lots_stats()
        text = (
            f"📋 <b>СТАТУС ЛОТОВ НА FUNPAY</b>\n"
            f"────────────────────\n"
            f"💎 Всего лотов в базе: <code>{lots['total']}</code>\n"
            f"🟢 Активных на продаже: <code>{lots['active']}</code>"
        )
        bot.edit_message_text(
            text,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode="HTML",
            reply_markup=keyboards.back_to_submenu("lots")
        )

    @bot.callback_query_handler(func=lambda call: call.data in ["lots_recreate", "lots_remove"])
    @admin_check
    def cb_lots_dangerous(call):
        bot.answer_callback_query(call.id)
        action = call.data
        action_name = "пересоздать (деактивировать и создать заново) все" if action == "lots_recreate" else "снять (деактивировать) все"
        bot.edit_message_text(
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
        bot.answer_callback_query(call.id)
        action = call.data.replace("confirm_yes_", "")
        bot.edit_message_text("🔄 Выполнение операции, пожалуйста, подождите...", chat_id=call.message.chat.id, message_id=call.message.message_id)
        
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
        bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_no_"))
    @admin_check
    def cb_confirm_no(call):
        bot.answer_callback_query(call.id)
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
            
        bot.edit_message_text(
            text,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode="HTML",
            reply_markup=markup
        )
