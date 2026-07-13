from __future__ import annotations

import datetime
from html import escape
from typing import Any


def _text(value: Any, default: str = "—") -> str:
    if value is None or value == "":
        return default
    return escape(str(value), quote=False)


def _ts(ts_val: float | None = None) -> str:
    if ts_val:
        dt = datetime.datetime.fromtimestamp(ts_val)
    else:
        dt = datetime.datetime.now()
    return dt.strftime("%d.%m.%Y %H:%M")


def _safe_float(val: Any, default: float = 0.0) -> float:
    try:
        return float(val) if val is not None else default
    except (TypeError, ValueError):
        return default


def format_welcome(username: str | None = None) -> str:
    lines = [
        "🎮 <b>FunPay Hub — Control Panel</b>",
        "─" * 25,
        "Выберите раздел:",
        "",
    ]
    return "\n".join(lines)


# =====================================================================
# Баланс
# =====================================================================


def format_balance(data: dict) -> str:
    if not isinstance(data, dict):
        return "❌ Нет данных о балансе"

    if not data.get("available", False):
        return f"❌ Не удалось получить баланс: {_text(data.get('error'), 'нет авторизации')}"

    bal = data.get("balance") or {}
    rub = _safe_float(bal.get("available_rub") or bal.get("total_rub"))
    usd = _safe_float(bal.get("available_usd") or bal.get("total_usd"))
    eur = _safe_float(bal.get("available_eur") or bal.get("total_eur"))
    lot_id = _text(bal.get("lot_id_used"))
    updated = bal.get("updated_at") or data.get("updated_at")
    wallets = data.get("wallets", [])
    history = data.get("history", [])

    lines = [
        "💰 <b>Баланс FunPay</b>",
        "─" * 25,
        "🟢 Авторизация: OK",
        "",
        f"💵 RUB: {rub:.2f}",
        f"💶 EUR: {eur:.2f}",
        f"💲 USD: {usd:.2f}",
        "",
        f"📦 Лот: {lot_id}",
        f"👛 Кошельков: {len(wallets)}",
        "",
        f"🕒 Обновлено: {_ts(updated)}",
    ]

    if history:
        lines.append("")
        lines.append(f"📊 История: {len(history)} записей")
        for h in history[-3:]:
            h_date = _text(h.get("date"))
            h_rub = _safe_float(h.get("available_rub"))
            lines.append(f"  • {h_date}: {h_rub:.2f} ₽")

    return "\n".join(lines)


# =====================================================================
# Отчёт
# =====================================================================


def format_report(data: dict) -> str:
    if not isinstance(data, dict):
        return "❌ Нет данных отчёта"

    connected = data.get("connected", False)
    username = _text(data.get("username"))
    user_id = _text(data.get("id"))
    active_sales = data.get("active_sales", 0)
    active_purchases = data.get("active_purchases", 0)
    profile_url = data.get("profile_url", "")
    updated = data.get("updated_at")

    status_emoji = "🟢" if connected else "🔴"
    status_text = "подключён" if connected else "не подключён"

    lines = [
        "📊 <b>Отчёт системы</b>",
        "─" * 25,
        f"{status_emoji} FunPay: {status_text}",
        "",
        f"👤 Пользователь: {username}",
        f"🛒 Активные покупки: {active_purchases}",
        f"💰 Активные продажи: {active_sales}",
    ]

    if profile_url:
        lines.append("")
        lines.append(f"🔗 <a href='{escape(str(profile_url), quote=True)}'>Профиль FunPay</a>")

    lines.append("")
    lines.append(f"🕒 Последнее обновление: {_ts(updated)}")

    return "\n".join(lines)


# =====================================================================
# Состояние
# =====================================================================


def format_system_status(health_data: dict, overview_data: dict) -> str:
    lines = ["⚙️ <b>Состояние системы</b>", "─" * 25]

    if isinstance(overview_data, dict):
        connected = overview_data.get("connected", False)
        username = _text(overview_data.get("username"), "")
        fp_emoji = "🟢" if connected else "🔴"
        fp_text = f"Подключён — @{username}" if connected and username else "Не подключён"
        lines.append(f"{fp_emoji} <b>FunPay</b>: {fp_text}")
        if not connected:
            err = _text(overview_data.get("error"), "Нет авторизации")
            lines.append(f"   ⚠️ {err}")
    else:
        lines.append("🔴 <b>FunPay</b>: Нет данных")

    if isinstance(health_data, dict):
        status = health_data.get("status", "unknown")
        status_emoji = "🟢" if status == "ok" else ("🟡" if status == "warning" else "🔴")
        lines.append(f"{status_emoji} <b>Hub</b>: {'Работает' if status == 'ok' else status}")

        issues = health_data.get("issues", [])
        if issues:
            lines.append("")
            lines.append("🟡 <b>Предупреждения:</b>")
            for issue in issues[:5]:
                lvl = issue.get("level", "")
                msg = _text(issue.get("message"), "Неизвестное предупреждение")
                emo = "❌" if lvl == "error" else "⚠️"
                lines.append(f"  {emo} {msg}")
        else:
            lines.append("")
            lines.append("✅ Предупреждений нет")

        backups = health_data.get("backups_count", 0)
        lines.append(f"💾 <b>Бэкапов:</b> {backups}")
    else:
        lines.append("❓ <b>Hub</b>: не отвечает")

    lines.append("")
    lines.append(f"🕐 Последняя проверка: {_ts()}")

    return "\n".join(lines)


# =====================================================================
# Лоты
# =====================================================================


def format_lots(data: dict) -> str:
    if not isinstance(data, dict):
        return "❌ Нет данных о лотах"

    if data.get("available") is False:
        return f"❌ Не удалось загрузить лоты: {_text(data.get('error'), 'нет авторизации')}"

    lots = data.get("lots", [])
    total = data.get("total", len(lots))

    if not lots and total == 0:
        return "📦 Лоты не найдены"

    lines = [
        "📦 <b>Лоты</b>",
        "─" * 25,
        f"Найдено: {total}",
        "",
    ]

    for i, lot in enumerate(lots[:20], 1):
        title = _text(lot.get("title") or lot.get("description") or "(без названия)")
        price = _safe_float(lot.get("price_rub", lot.get("price", 0)))
        category = _text(lot.get("category_name") or lot.get("subcategory_name") or lot.get("platform") or "—")
        lot_id = _text(str(lot.get("id") or lot.get("lot_id") or lot.get("service_id") or "—"))
        lines.append(f"{i}.")
        lines.append(f"Название: {title}")
        lines.append(f"Цена: {price:.2f} ₽")
        lines.append(f"Категория: {category}")
        lines.append(f"ID: {lot_id}")
        lines.append("")

    if total > 20:
        lines.append(f"... и ещё {total - 20}")

    return "\n".join(lines)


def format_lots_stats(data: dict) -> str:
    if not isinstance(data, dict):
        return "❌ Нет данных о лотах"
    lots = data.get("lots", [])
    if not lots:
        return "📈 <b>Статистика лотов</b>\nЛоты не найдены"
    total = len(lots)
    active = sum(1 for l in lots if l.get("active", True))
    inactive = total - active

    # Группировка по маркеру поставщика в названии
    _MARKERS = {
        "[AS#": "AutoSMM (Twiboost)", "[GB#": "GorgonaBoosts",
        "[HB#": "HoldBoost", "[KS#": "Kosell", "[ST#": "Telegram Stars",
        "[SC#": "ShopClaude", "[LS#": "LookSMM", "[FK#": "FreeKassa",
    }
    by_supplier: dict = {}
    for l in lots:
        title = l.get("title", "")
        sup = "Прочее"
        for mk, name in _MARKERS.items():
            if mk in title:
                sup = name
                break
        by_supplier.setdefault(sup, {"total": 0, "active": 0})
        by_supplier[sup]["total"] += 1
        if l.get("active", True):
            by_supplier[sup]["active"] += 1

    lines = [
        "📈 <b>Статистика лотов</b>",
        "─" * 25,
        f"📦 Всего: {total}",
        f"🟢 Активных: {active}",
        f"🔴 Снятых: {inactive}",
        "",
        "📌 <b>По поставщикам:</b>",
    ]
    for sup, info in sorted(by_supplier.items()):
        lines.append(f"  • {sup}: {info['active']}/{info['total']} активно")
    return "\n".join(lines)


# =====================================================================
# Симуляция
# =====================================================================


def format_simulation(data: dict) -> str:
    if not isinstance(data, dict):
        return "❌ Нет данных симуляции"

    report = data.get("report", {}) if isinstance(data.get("report"), (dict, list)) else {}
    dry_run = data.get("dry_run", not data.get("dry_run_off", False))
    error = data.get("error")

    if error:
        return f"❌ Симуляция недоступна\nПричина: {_text(error)}"

    lines = [
        "🔥 <b>Симуляция</b>",
        "─" * 25,
        "🟢 Статус: выполнена",
        f"🧪 Тестовый режим: {'ON' if dry_run else 'OFF'}",
    ]

    if isinstance(report, dict):
        all_ok = report.get("all_ok", report.get("success", False))
        plugins = report.get("plugins", report.get("results", []))
        lines.append(f"📋 Результат: {'✅ Все ок' if all_ok else '⚠️ Есть ошибки'}")
        if isinstance(plugins, list) and plugins:
            lines.append("")
            lines.append("📌 <b>Плагины:</b>")
            for p in plugins:
                pname = _text(p.get("name", p.get("plugin")))
                pstatus = "✅" if p.get("ok", p.get("success", False)) else "❌"
                lines.append(f"  {pstatus} {pname}")
    elif isinstance(report, list):
        lines.append(f"📋 Этапов: {len(report)}")
        for r in report:
            if isinstance(r, dict):
                name = _text(r.get("name", r.get("step")))
                status = "✅" if r.get("ok", r.get("success", False)) else "❌"
                lines.append(f"  {status} {name}")

    ts = data.get("updated_at") or data.get("timestamp") or datetime.datetime.now().timestamp()
    lines.append("")
    lines.append(f"🕐 Последний запуск: {_ts(ts)}")

    return "\n".join(lines)


# =====================================================================
# Логи
# =====================================================================


def format_logs(data: dict) -> str:
    if not isinstance(data, dict):
        return "📜 <b>Последние события</b>\nНет данных"
    entries = data.get("logs", [])
    if not entries:
        return "📜 <b>Последние события</b>\nНет записей"
    lines = ["📜 <b>Последние события</b>", "─" * 25]
    for e in entries[:50]:
        lvl = _text(e.get("level", "INFO"))
        message = _text(e.get("message", ""))
        ts = _text(e.get("time", "") or e.get("timestamp", ""))
        source = _text(e.get("source", ""))
        if lvl == "ERROR":
            lines.append(f"🔴 `{ts}` [{source}] {message}")
        elif lvl == "WARNING":
            lines.append(f"🟡 `{ts}` [{source}] {message}")
        elif lvl == "INFO":
            lines.append(f"🟢 `{ts}` [{source}] {message}")
        else:
            lines.append(f"⚪ `{ts}` [{source}] {message}")
    total = data.get("count", len(entries))
    lines.append(f"\nВсего записей: {total}")
    return "\n".join(lines)


# =====================================================================
# Плагины
# =====================================================================


def format_plugins_summary(data: dict) -> str:
    if not isinstance(data, dict):
        return "🔌 <b>Плагины</b>:\nНет данных"
    plugins = data.get("plugins", [])
    if not plugins:
        return "🔌 <b>Плагины</b>:\nНет данных"
    lines = ["🔌 <b>Плагины</b>:", ""]
    for p in plugins:
        name = _text(p.get("display_name") or p.get("name"))
        enabled = p.get("enabled", False)
        status = "🟢 АКТИВЕН" if enabled else "🔴 ОТКЛЮЧЁН"
        lines.append(f"<b>{name}</b> — {status}")
        lines.append(f"  Лотов: {p.get('lots_count', 0)}")
    return "\n".join(lines)


def format_plugin_detail(data: dict, plugin_name: str = "") -> str:
    if not isinstance(data, dict):
        return "❌ Нет данных о плагине"
    state = _text(data.get("state", "unknown"))
    config = data.get("config", {})
    is_active = config.get("enabled", False) if isinstance(config, dict) else False
    display = "📈 АвтоСММ" if plugin_name == "autosmm" else "💰 АвтоДонат" if plugin_name == "autodonate" else _text(plugin_name)
    lines = [
        f"<b>{display}</b>",
        "─" * 25,
        f"Статус: {'🟢 АКТИВЕН' if is_active else '🔴 ОТКЛЮЧЁН'}",
        f"Состояние: {state}",
    ]
    history = data.get("history", [])
    if history:
        lines.append("")
        lines.append("📜 <b>История:</b>")
        for h in history[-5:]:
            lines.append(f"  • {_text(h.get('time', ''))} {_text(h.get('action', ''))}")
    return "\n".join(lines)


# =====================================================================
# Кошелёк / Hub / AI / Market / Error
# =====================================================================


def format_wallet(data: dict) -> str:
    if not isinstance(data, dict):
        return "❌ Нет данных о кошельках"

    bal = data.get("balance") or {}
    rub = _safe_float(bal.get("available_rub") or bal.get("total_rub"))
    usd = _safe_float(bal.get("available_usd") or bal.get("total_usd"))
    eur = _safe_float(bal.get("available_eur") or bal.get("total_eur"))
    wallets = data.get("wallets", [])

    lines = [
        "👛 <b>Кошельки</b>",
        "─" * 25,
        f"📊 Подключено: {len(wallets)}",
        "",
        f"💰 Общий баланс:",
        f"  💵 RUB: {rub:.2f}",
        f"  💶 EUR: {eur:.2f}",
        f"  💲 USD: {usd:.2f}",
    ]

    if wallets:
        lines.append("")
        lines.append("📌 <b>Кошельки:</b>")
        for w in wallets:
            wtype = _text(w.get("type"))
            waddr = _text(w.get("address"), "")[:20]
            lines.append(f"  • {wtype}: {waddr}")
    else:
        lines.append("")
        lines.append("🟡 Нет активных кошельков")

    lines.append("")
    lines.append(f"🕒 Обновлено: {_ts(data.get('updated_at'))}")

    return "\n".join(lines)


def format_hub_start(ok: bool, msg: str, pid: int | None = None) -> str:
    if ok:
        lines = [
            "🚀 <b>Запуск Hub</b>",
            "─" * 25,
            "🟢 Статус: Запущен",
        ]
        if pid:
            lines.append(f"📌 PID: {pid}")
        lines.append(f"🕐 Время: {_ts()}")
        return "\n".join(lines)
    return f"❌ {msg}"


def format_hub_stop(ok: bool, msg: str, pid: int | None = None) -> str:
    if ok:
        lines = [
            "🛑 <b>Остановка Hub</b>",
            "─" * 25,
            "✅ Сигнал отправлен",
            "⏳ Статус: Останавливается",
        ]
        if pid:
            lines.append(f"📌 PID: {pid}")
        lines.append(f"🕐 Время: {_ts()}")
        return "\n".join(lines)
    return f"❌ {msg}"


def format_ai_agent(data: dict) -> str:
    if not isinstance(data, dict):
        return "🤖 <b>AI Agent</b>\n─" * 15 + "\n❌ Нет данных"

    status = data.get("status", "unknown")
    ai_data = data.get("ai_agent", {})
    ai_available = bool(ai_data.get("available", False)) if isinstance(ai_data, dict) else False

    lines = [
        "🤖 <b>AI Agent</b>",
        "─" * 25,
        f"Статус: {'🟢 АКТИВЕН' if ai_available else '🔴 НЕ АКТИВЕН'}",
        f"Система: {'🟢' if status == 'ok' else '🟡'} {status}",
    ]

    if isinstance(ai_data, dict):
        for k, v in ai_data.items():
            if k != "available" and v:
                lines.append(f"  • {_text(k)}: {_text(v)}")

    recommendation = ai_data.get("last_recommendation") if isinstance(ai_data, dict) else None
    if recommendation:
        lines.append("")
        lines.append("📋 <b>Последняя рекомендация:</b>")
        lines.append(f"  {_text(recommendation)}")

    return "\n".join(lines)


def format_ai_recommendation(data: dict) -> str:
    if not isinstance(data, dict):
        return "🤖 <b>AI Рекомендация</b>\nНет данных"
    lines = ["🤖 <b>AI Рекомендация</b>", "─" * 25]
    diagnosis = _text(data.get("diagnosis"))
    if diagnosis:
        lines.append(f"🔍 {diagnosis}")
    patch = _text(data.get("patch"))
    if patch:
        lines.append(f"💊 {patch}")
    file_ = _text(data.get("file"))
    if file_ and file_ != "—":
        lines.append(f"📁 {file_}")
    confidence = data.get("confidence")
    if confidence is not None:
        lines.append(f"📊 Уверенность: {confidence}%")
    return "\n".join(lines)


def format_market_status(data: dict) -> str:
    niches = data.get("niches", data.get("results", []))
    if not isinstance(niches, list):
        niches = []
    lines = ["📊 <b>Анализ ниш</b>", "─" * 25, f"Найдено: {len(niches)}"]
    for niche in niches[:5]:
        if not isinstance(niche, dict):
            continue
        name = _text(niche.get("name", niche.get("title")))
        score = niche.get("score", niche.get("profitability"))
        suffix = f" — рейтинг: {score}" if score is not None else ""
        lines.append(f"• {name}{suffix}")
    if len(niches) > 5:
        lines.append(f"… и ещё {len(niches) - 5}")
    if not niches:
        lines.append("🟡 Подходящих ниш не найдено")
    lines.append("")
    lines.append(f"🕐 Обновлено: {_ts(data.get('updated_at'))}")
    return "\n".join(lines)


# =====================================================================
# Статистика
# =====================================================================

def format_stats(data: dict) -> str:
    if not isinstance(data, dict):
        return "📈 <b>Статистика</b>\nНет данных"
    lines = ["📈 <b>Статистика</b>", "─" * 25]
    today = data.get("today", {})
    if today:
        lines.append("<b>📅 Сегодня</b>")
        lines.append(f"💰 Выручка: {_safe_float(today.get('revenue', 0)):.2f} ₽")
        lines.append(f"🛒 Продаж: {today.get('sales', 0)}")
        avg = _safe_float(today.get('avg_check', 0))
        lines.append(f"⭐ Средний чек: {avg:.2f} ₽")
        lines.append(f"📦 Активных лотов: {today.get('active_lots', 0)}")
    else:
        lines.append("Нет данных за сегодня")
    return "\n".join(lines)


# =====================================================================
# Система
# =====================================================================

def format_system(data: dict) -> str:
    if not isinstance(data, dict):
        return "⚙️ <b>Система</b>\nНет данных"
    lines = ["⚙️ <b>Система</b>", "─" * 25]
    cpu = _text(data.get("cpu_percent", "—"))
    mem = _text(data.get("memory_percent", "—"))
    lines.append(f"🖥 CPU: {cpu}%")
    lines.append(f"🧠 RAM: {mem}%")
    services = data.get("services", {})
    if services:
        lines.append("")
        lines.append("📌 <b>Сервисы:</b>")
        for name, info in services.items():
            st = info.get("status", "unknown")
            emo = "🟢" if st == "ok" else ("🟡" if st == "warning" else "🔴")
            lines.append(f"  {emo} {_text(name)}: {_text(st)}")
    uptime = data.get("uptime")
    if uptime is not None:
        lines.append("")
        lines.append(f"⏱ Uptime: {_text(uptime)}")
    return "\n".join(lines)


def format_action_ok(title: str, detail: str = "") -> str:
    lines = [f"✅ <b>{_text(title)}</b>", "─" * 25]
    if detail:
        lines.append(_text(detail))
    return "\n".join(lines)


def format_remove_all_lots(result: dict) -> str:
    deactivated = 0
    if isinstance(result, dict):
        deactivated = result.get("deactivated", 0)
    return f"🗑️ Снято лотов: {deactivated}"


def format_auto_create_toggle(result: dict) -> str:
    enabled = False
    if isinstance(result, dict):
        enabled = result.get("auto_lots_enabled", False)
    status = "включено" if enabled else "выключено"
    return f"✅ Авто-создание {status}"


def format_error(endpoint: str, error: Any, detail: str = "") -> str:
    error_str = _text(error, "Неизвестная ошибка")[:200]

    lines = [
        "⚠️ <b>Ошибка получения данных</b>",
        "─" * 25,
        f"🔗 Endpoint: {endpoint}",
        f"❌ Причина: {error_str}",
    ]
    if detail:
        lines.append(f"📝 {detail}")
    lines.append("")
    lines.append("🔄 Попробуйте позже или проверьте статус системы")

    return "\n".join(lines)
