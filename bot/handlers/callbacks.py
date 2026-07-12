from __future__ import annotations

import json
import logging
import os
import subprocess
import time
from typing import Any

import psutil
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup
from aiogram.exceptions import TelegramBadRequest

from bot.api_client import APIClient, APIClientError
from bot.config import get_bot_config
from bot.formatters import (
    format_balance,
    format_report,
    format_system_status,
    format_stats,
    format_system,
    format_lots,
    format_simulation,
    format_logs,
    format_wallet,
    format_hub_start,
    format_hub_stop,
    format_plugins_summary,
    format_plugin_detail,
    format_remove_all_lots,
    format_auto_create_toggle,
    format_market_status,
    format_error,
)
from bot.keyboards.main import (
    get_main_menu,
    get_back_button,
    get_logs_keyboard,
    get_plugins_keyboard,
    get_plugin_detail_keyboard,
    get_confirm_keyboard,
)

logger = logging.getLogger("bot.handlers.callbacks")

router = Router()
api = APIClient()


def _is_local() -> bool:
    from urllib.parse import urlparse

    cfg = get_bot_config()
    hostname = (urlparse(cfg.hub_url).hostname or "").lower()
    return hostname in {"127.0.0.1", "localhost", "::1"}


async def _healthcheck() -> bool:
    try:
        await api.get("/health")
        return True
    except Exception:
        return False


def _get_hub_pid() -> tuple[bool, int | None]:
    for proc in psutil.process_iter(["name", "cmdline"]):
        try:
            cmdline = proc.info.get("cmdline") or []
            if any("funpayhub_main.py" in str(c) for c in cmdline):
                return True, proc.pid
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return False, None


async def _safe_edit(query: CallbackQuery, text: str, reply_markup: InlineKeyboardMarkup | None = None) -> None:
    chat_id = query.message.chat.id if query.message else None
    message_id = query.message.message_id if query.message else None
    if chat_id is None or message_id is None:
        return
    try:
        if len(text) > 4000:
            text = text[:3990] + "\n\n... (обрезано)"
        await query.message.edit_text(text=text, reply_markup=reply_markup)
    except TelegramBadRequest as exc:
        err = str(exc)
        if "message is not modified" in err:
            return
        if "message can't be edited" in err:
            logger.warning("Cannot edit message %s: %s", message_id, err)
            return
        logger.error("edit_text failed: %s", err)


@router.callback_query(F.data == "back_to_menu")
async def cb_back(query: CallbackQuery) -> None:
    await _safe_edit(query, "🎮 FunPay Hub Control Panel", get_main_menu())


# =====================================================================
# Hub control
# =====================================================================


@router.callback_query(F.data == "start_hub")
async def cb_start_hub(query: CallbackQuery) -> None:
    try:
        if _is_local():
            text = "🚀 <b>Запустить систему?</b>\n\nHub будет запущен локально."
            await _safe_edit(query, text, get_confirm_keyboard("start_hub", "local"))
        else:
            text = "❌ Hub развёрнут отдельным сервисом. Используйте панель Render или Deploy API."
            await _safe_edit(query, text, get_main_menu())
    except Exception as exc:
        logger.error("start_hub error: %s", exc)
        await _safe_edit(query, format_error("start_hub", exc), get_main_menu())


@router.callback_query(F.data == "stop_hub")
async def cb_stop_hub(query: CallbackQuery) -> None:
    try:
        if _is_local():
            text = "🛑 <b>Остановить систему?</b>\n\nВсе процессы будут остановлены."
            await _safe_edit(query, text, get_confirm_keyboard("stop_hub", "local"))
        else:
            text = "❌ Hub развёрнут отдельным сервисом. Остановить его из worker-контейнера нельзя."
            await _safe_edit(query, text, get_main_menu())
    except Exception as exc:
        logger.error("stop_hub error: %s", exc)
        await _safe_edit(query, format_error("stop_hub", exc), get_main_menu())


@router.callback_query(F.data == "confirm_start_hub_local")
async def cb_confirm_start_hub(query: CallbackQuery) -> None:
    await query.answer()
    try:
        script = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "funpayhub_main.py")
        if not os.path.exists(script):
            text = "❌ funpayhub_main.py не найден"
            await _safe_edit(query, text, get_main_menu())
            return
        for proc in psutil.process_iter(["name", "cmdline"]):
            try:
                cmdline = proc.info.get("cmdline") or []
                if any("funpayhub_main.py" in str(c) for c in cmdline):
                    text = "❌ Hub уже запущен"
                    await _safe_edit(query, text, get_main_menu())
                    return
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        try:
            kwargs: dict[str, Any] = {"cwd": os.path.dirname(os.path.abspath(__file__))}
            if __import__("sys").platform == "win32":
                kwargs["creationflags"] = subprocess.CREATE_NEW_CONSOLE
            else:
                kwargs["stdout"] = subprocess.DEVNULL
                kwargs["stderr"] = subprocess.DEVNULL
            subprocess.Popen([__import__("sys").executable, script], **kwargs)
            for _ in range(10):
                if await _healthcheck():
                    _, pid = _get_hub_pid()
                    text = format_hub_start(True, "FunPay Hub запущен", pid)
                    await _safe_edit(query, text, get_main_menu())
                    return
                time.sleep(1)
            text = format_hub_start(False, "Процесс запущен, но /health не ответил за 10с")
            await _safe_edit(query, text, get_main_menu())
        except Exception as exc:
            text = format_hub_start(False, f"Ошибка запуска: {exc}")
            await _safe_edit(query, text, get_main_menu())
    except Exception as exc:
        logger.error("confirm_start_hub error: %s", exc)
        await _safe_edit(query, format_error("start_hub", exc), get_main_menu())


@router.callback_query(F.data == "confirm_stop_hub_local")
async def cb_confirm_stop_hub(query: CallbackQuery) -> None:
    await query.answer()
    try:
        import psutil
        running, pid = _get_hub_pid()
        if not running:
            text = format_hub_stop(False, "Hub не запущен")
            await _safe_edit(query, text, get_main_menu())
            return
        try:
            p = psutil.Process(pid)
            p.terminate()
            p.wait(timeout=10)
            text = format_hub_stop(True, "Hub остановлен", pid)
            await _safe_edit(query, text, get_main_menu())
        except Exception as exc:
            text = format_hub_stop(False, f"Ошибка остановки: {exc}")
            await _safe_edit(query, text, get_main_menu())
    except Exception as exc:
        logger.error("confirm_stop_hub error: %s", exc)
        await _safe_edit(query, format_error("stop_hub", exc), get_main_menu())


def _is_local() -> bool:
    from urllib.parse import urlparse
    cfg = get_bot_config()
    hostname = (urlparse(cfg.hub_url).hostname or "").lower()
    return hostname in {"127.0.0.1", "localhost", "::1"}


async def _healthcheck() -> bool:
    try:
        data = await api.get("/health")
        return True
    except Exception:
        return False


def _get_hub_pid() -> tuple[bool, int | None]:
    import psutil
    for proc in psutil.process_iter(["name", "cmdline"]):
        try:
            cmdline = proc.info.get("cmdline") or []
            if any("funpayhub_main.py" in str(c) for c in cmdline):
                return True, proc.pid
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return False, None


# =====================================================================
# Overview / Balance / Report / Status
# =====================================================================


@router.callback_query(F.data == "report")
async def cb_report(query: CallbackQuery) -> None:
    try:
        data = await api.get("/api/seller/overview")
        text = format_report(data) if isinstance(data, dict) else format_error("/api/seller/overview", data)
        await _safe_edit(query, text, get_main_menu())
    except APIClientError as exc:
        await _safe_edit(query, format_error("/api/seller/overview", exc), get_main_menu())
    except Exception as exc:
        logger.error("report error: %s", exc)
        await _safe_edit(query, format_error("report", exc), get_main_menu())


@router.callback_query(F.data == "balance")
async def cb_balance(query: CallbackQuery) -> None:
    try:
        data = await api.get("/api/seller/balance/full")
        text = format_balance(data) if isinstance(data, dict) else format_error("/api/seller/balance/full", data)
        await _safe_edit(query, text, get_main_menu())
    except APIClientError as exc:
        await _safe_edit(query, format_error("/api/seller/balance/full", exc), get_main_menu())
    except Exception as exc:
        logger.error("balance error: %s", exc)
        await _safe_edit(query, format_error("balance", exc), get_main_menu())


@router.callback_query(F.data == "system_status")
async def cb_system_status(query: CallbackQuery) -> None:
    try:
        health, overview = {}, {}
        try:
            health = await api.get("/api/system/health")
        except Exception:
            pass
        try:
            overview = await api.get("/api/seller/overview")
        except Exception:
            pass
        text = format_system_status(
            health if isinstance(health, dict) else None,
            overview if isinstance(overview, dict) else None,
        )
        await _safe_edit(query, text, get_main_menu())
    except Exception as exc:
        logger.error("system_status error: %s", exc)
        await _safe_edit(query, format_error("system_status", exc), get_main_menu())


# =====================================================================
# Lots
# =====================================================================


@router.callback_query(F.data == "lots")
async def cb_lots(query: CallbackQuery) -> None:
    try:
        data = await api.get("/api/seller/lots")
        text = format_lots(data) if isinstance(data, dict) else format_error("/api/seller/lots", data)
        await _safe_edit(query, text, get_main_menu())
    except APIClientError as exc:
        await _safe_edit(query, format_error("/api/seller/lots", exc), get_main_menu())
    except Exception as exc:
        logger.error("lots error: %s", exc)
        await _safe_edit(query, format_error("lots", exc), get_main_menu())


@router.callback_query(F.data == "create_lots")
async def cb_create_lots(query: CallbackQuery) -> None:
    try:
        data = await api.post("/api/lots/generate", {"plugin": "autosmm_plugin", "supplier": "", "dry_run": True})
        text = format_lots(data) if isinstance(data, dict) else format_error("/api/lots/generate", data)
        await _safe_edit(query, text, get_main_menu())
    except APIClientError as exc:
        await _safe_edit(query, format_error("/api/lots/generate", exc), get_main_menu())
    except Exception as exc:
        logger.error("create_lots error: %s", exc)
        await _safe_edit(query, format_error("create_lots", exc), get_main_menu())


# =====================================================================
# Simulation
# =====================================================================


@router.callback_query(F.data == "simulation")
async def cb_simulation(query: CallbackQuery) -> None:
    try:
        data = await api.post("/api/system/simulate", {})
        text = format_simulation(data) if isinstance(data, dict) else format_error("/api/system/simulate", data)
        await _safe_edit(query, text, get_main_menu())
    except APIClientError as exc:
        await _safe_edit(query, format_error("/api/system/simulate", exc), get_main_menu())
    except Exception as exc:
        logger.error("simulation error: %s", exc)
        await _safe_edit(query, format_error("simulation", exc), get_main_menu())


# =====================================================================
# Wallet
# =====================================================================


@router.callback_query(F.data == "wallet")
async def cb_wallet(query: CallbackQuery) -> None:
    try:
        data = await api.get("/api/seller/balance/full")
        text = format_wallet(data) if isinstance(data, dict) else format_error("/api/seller/balance/full", data)
        await _safe_edit(query, text, get_main_menu())
    except APIClientError as exc:
        await _safe_edit(query, format_error("/api/seller/balance/full", exc), get_main_menu())
    except Exception as exc:
        logger.error("wallet error: %s", exc)
        await _safe_edit(query, format_error("wallet", exc), get_main_menu())


# =====================================================================
# AI Agent
# =====================================================================
# Logs
# =====================================================================


@router.callback_query(F.data == "logs_view")
async def cb_logs_view(query: CallbackQuery) -> None:
    try:
        data = await api.get("/api/logs")
        text = format_logs(data) if isinstance(data, dict) else format_error("/api/logs", data)
        await _safe_edit(query, text, get_logs_keyboard())
    except APIClientError as exc:
        await _safe_edit(query, format_error("/api/logs", exc), get_main_menu())
    except Exception as exc:
        logger.error("logs_view error: %s", exc)
        await _safe_edit(query, format_error("logs_view", exc), get_main_menu())


@router.callback_query(F.data == "logs_filter_errors")
async def cb_logs_filter_errors(query: CallbackQuery) -> None:
    try:
        data = await api.get("/api/logs?level=ERROR")
        text = format_logs(data) if isinstance(data, dict) else format_error("/api/logs", data)
        await _safe_edit(query, text, get_logs_keyboard("ERROR"))
    except APIClientError as exc:
        await _safe_edit(query, format_error("/api/logs", exc), get_main_menu())
    except Exception as exc:
        logger.error("logs_filter_errors error: %s", exc)
        await _safe_edit(query, format_error("logs_filter_errors", exc), get_main_menu())


@router.callback_query(F.data == "logs_filter_warnings")
async def cb_logs_filter_warnings(query: CallbackQuery) -> None:
    try:
        data = await api.get("/api/logs?level=WARNING")
        text = format_logs(data) if isinstance(data, dict) else format_error("/api/logs", data)
        await _safe_edit(query, text, get_logs_keyboard("WARNING"))
    except APIClientError as exc:
        await _safe_edit(query, format_error("/api/logs", exc), get_main_menu())
    except Exception as exc:
        logger.error("logs_filter_warnings error: %s", exc)
        await _safe_edit(query, format_error("logs_filter_warnings", exc), get_main_menu())


@router.callback_query(F.data == "logs_filter_all")
async def cb_logs_filter_all(query: CallbackQuery) -> None:
    try:
        data = await api.get("/api/logs")
        text = format_logs(data) if isinstance(data, dict) else format_error("/api/logs", data)
        await _safe_edit(query, text, get_logs_keyboard("all"))
    except APIClientError as exc:
        await _safe_edit(query, format_error("/api/logs", exc), get_main_menu())
    except Exception as exc:
        logger.error("logs_filter_all error: %s", exc)
        await _safe_edit(query, format_error("logs_filter_all", exc), get_main_menu())


@router.callback_query(F.data == "logs_refresh")
async def cb_logs_refresh(query: CallbackQuery) -> None:
    try:
        data = await api.get("/api/logs")
        text = format_logs(data) if isinstance(data, dict) else format_error("/api/logs", data)
        await _safe_edit(query, text, get_logs_keyboard())
    except APIClientError as exc:
        await _safe_edit(query, format_error("/api/logs", exc), get_main_menu())
    except Exception as exc:
        logger.error("logs_refresh error: %s", exc)
        await _safe_edit(query, format_error("logs_refresh", exc), get_main_menu())


# =====================================================================
# Plugins
# =====================================================================


@router.callback_query(F.data == "plugins_panel")
async def cb_plugins_panel(query: CallbackQuery) -> None:
    try:
        data = await api.get("/api/plugins")
        text = format_plugins_summary(data) if isinstance(data, dict) else format_error("/api/plugins", data)
        autosmm_enabled = False
        autodonate_enabled = False
        if isinstance(data, dict):
            for p in data.get("plugins", []):
                if p.get("name") == "autosmm_plugin":
                    autosmm_enabled = p.get("enabled", False)
                if p.get("name") == "autodonate_plugin":
                    autodonate_enabled = p.get("enabled", False)
        await _safe_edit(query, text, get_plugins_keyboard(autosmm_enabled, autodonate_enabled))
    except APIClientError as exc:
        await _safe_edit(query, format_error("/api/plugins", exc), get_main_menu())
    except Exception as exc:
        logger.error("plugins_panel error: %s", exc)
        await _safe_edit(query, format_error("plugins_panel", exc), get_main_menu())


@router.callback_query(F.data.in_({"autosmm", "autodonate"}))
async def cb_plugin_detail(query: CallbackQuery) -> None:
    try:
        plugin = query.data
        data = await api.get(f"/api/plugins/{plugin}")
        text = format_plugin_detail(data, plugin) if isinstance(data, dict) else format_error(f"/api/plugins/{plugin}", data)
        kb = get_plugin_detail_keyboard(
            plugin,
            data.get("config", {}).get("enabled", False) if isinstance(data, dict) and isinstance(data.get("config"), dict) else False,
        )
        await _safe_edit(query, text, kb)
    except APIClientError as exc:
        await _safe_edit(query, format_error(f"/api/plugins/{plugin}", exc), get_main_menu())
    except Exception as exc:
        logger.error("plugin detail error: %s", exc)
        await _safe_edit(query, format_error(f"{plugin}_detail", exc), get_main_menu())


@router.callback_query(F.data.in_({"autosmm_toggle", "autodonate_toggle", "autosmm_deactivate", "autodonate_deactivate", "autosmm_status", "autodonate_status"}))
async def cb_plugin_actions(query: CallbackQuery) -> None:
    try:
        raw = query.data or ""
        plugin_alias = raw.split("_")[0]
        plugin = "autosmm_plugin" if plugin_alias == "autosmm" else "autodonate_plugin" if plugin_alias == "autodonate" else plugin_alias
        if raw.endswith("_toggle"):
            try:
                status_data = await api.get(f"/api/plugins/{plugin}")
                current = False
                if isinstance(status_data, dict):
                    cfg = status_data.get("config", {})
                    if isinstance(cfg, dict):
                        current = cfg.get("enabled", False)
            except Exception:
                current = False
            action = "disable" if current else "enable"
            data = await api.post(f"/api/plugins/{plugin}/{action}")
            is_active = not current
            text = f"✅ {'📈 АвтоСММ' if plugin_alias == 'autosmm' else '💰 АвтоДонат'} {'запущен' if is_active else 'остановлен'}"
            await _safe_edit(query, text, get_plugin_detail_keyboard(plugin_alias, is_active))
        elif raw.endswith("_deactivate"):
            data = await api.post("/api/dev/lots/deactivate_all", {})
            text = format_remove_all_lots(data)
            await _safe_edit(query, text, get_plugin_detail_keyboard(plugin_alias, True))
        elif raw.endswith("_status"):
            data = await api.get(f"/api/plugins/{plugin}")
            text = format_plugin_detail(data, plugin) if isinstance(data, dict) else format_error(f"/api/plugins/{plugin}", data)
            kb = get_plugin_detail_keyboard(
                plugin_alias,
                data.get("config", {}).get("enabled", False) if isinstance(data, dict) and isinstance(data.get("config"), dict) else False,
            )
            await _safe_edit(query, text, kb)
        else:
            await _safe_edit(query, "❓ Неизвестное действие", get_main_menu())
    except APIClientError as exc:
        await _safe_edit(query, format_error("plugin_action", exc), get_main_menu())
    except Exception as exc:
        logger.error("plugin action error: %s", exc)
        await _safe_edit(query, format_error("plugin_action", exc), get_main_menu())


@router.callback_query(F.data == "remove_all_lots")
async def cb_remove_all_lots(query: CallbackQuery) -> None:
    try:
        data = await api.post("/api/dev/lots/deactivate_all", {})
        text = format_remove_all_lots(data)
        await _safe_edit(query, text, get_main_menu())
    except APIClientError as exc:
        await _safe_edit(query, format_error("/api/dev/lots/deactivate_all", exc), get_main_menu())
    except Exception as exc:
        logger.error("remove_all_lots error: %s", exc)
        await _safe_edit(query, format_error("remove_all_lots", exc), get_main_menu())


@router.callback_query(F.data == "auto_create_toggle")
async def cb_auto_create_toggle(query: CallbackQuery) -> None:
    try:
        data = await api.post("/api/system/settings/auto_lots", {"enabled": True})
        text = format_auto_create_toggle(data)
        await _safe_edit(query, text, get_main_menu())
    except APIClientError as exc:
        await _safe_edit(query, format_error("/api/system/settings/auto_lots", exc), get_main_menu())
    except Exception as exc:
        logger.error("auto_create_toggle error: %s", exc)
        await _safe_edit(query, format_error("auto_create_toggle", exc), get_main_menu())


# =====================================================================
# Market
# =====================================================================


@router.callback_query(F.data == "market_status")
async def cb_market_status(query: CallbackQuery) -> None:
    try:
        data = await api.post("/api/market/analyze_niches_global", {"budget": 500, "force_refresh": False})
        text = format_market_status(data) if isinstance(data, dict) else format_error("/api/market/analyze_niches_global", data)
        await _safe_edit(query, text, get_main_menu())
    except APIClientError as exc:
        await _safe_edit(query, format_error("/api/market/analyze_niches_global", exc), get_main_menu())
    except Exception as exc:
        logger.error("market_status error: %s", exc)
        await _safe_edit(query, format_error("market_status", exc), get_main_menu())


# =====================================================================
# Stats / System / Notifications
# =====================================================================


@router.callback_query(F.data == "stats")
async def cb_stats(query: CallbackQuery) -> None:
    try:
        data = await api.get("/api/seller/overview")
        text = format_stats(data) if isinstance(data, dict) else format_error("/api/seller/overview", data)
        await _safe_edit(query, text, get_main_menu())
    except APIClientError as exc:
        await _safe_edit(query, format_error("/api/seller/overview", exc), get_main_menu())
    except Exception as exc:
        logger.error("stats error: %s", exc)
        await _safe_edit(query, format_error("stats", exc), get_main_menu())


@router.callback_query(F.data == "system")
async def cb_system(query: CallbackQuery) -> None:
    try:
        data = await api.get("/api/system/health")
        text = format_system(data) if isinstance(data, dict) else format_error("/api/system/health", data)
        await _safe_edit(query, text, get_main_menu())
    except APIClientError as exc:
        await _safe_edit(query, format_error("/api/system/health", exc), get_main_menu())
    except Exception as exc:
        logger.error("system error: %s", exc)
        await _safe_edit(query, format_error("system", exc), get_main_menu())


@router.callback_query(F.data == "notifications")
async def cb_notifications(query: CallbackQuery) -> None:
    try:
        data = await api.get("/api/seller/notifications")
        if isinstance(data, dict):
            notifs = data.get("notifications", [])
            lines = ["🔔 <b>Уведомления</b>", "─" * 25]
            if not notifs:
                lines.append("Нет новых уведомлений")
            for n in notifs[:10]:
                ntype = _text(n.get("type", "info"))
                nmsg = _text(n.get("message", ""))
                lines.append(f"• {ntype}: {nmsg}")
            text = "\n".join(lines)
        else:
            text = format_error("/api/seller/notifications", data)
        await _safe_edit(query, text, get_main_menu())
    except APIClientError as exc:
        await _safe_edit(query, format_error("/api/seller/notifications", exc), get_main_menu())
    except Exception as exc:
        logger.error("notifications error: %s", exc)
        await _safe_edit(query, format_error("notifications", exc), get_main_menu())


# =====================================================================
# Auto-refresh
# =====================================================================


@router.callback_query(F.data.startswith("refresh_"))
async def cb_refresh(query: CallbackQuery) -> None:
    await query.answer()
    raw = query.data or ""
    interval = 0
    if raw.startswith("refresh_"):
        try:
            interval = int(raw.split("_")[-1])
        except ValueError:
            interval = 0
    if interval > 0:
        # TODO: actual auto-refresh via FSM or storage
        await query.message.edit_text(
            text=f"🔄 Автообновление установлено на {interval} сек\n\n(Демо-режим)",
            reply_markup=get_main_menu(),
        )
    else:
        await query.message.edit_text(
            text="🔄 Автообновление выключено",
            reply_markup=get_main_menu(),
        )


# =====================================================================
# Settings / catch-all
# =====================================================================


@router.callback_query(F.data == "settings")
async def cb_settings(query: CallbackQuery) -> None:
    await _safe_edit(query, "⚙️ <b>Настройки</b>:\nБудут доступны позже.", get_main_menu())


@router.callback_query()
async def cb_unknown(query: CallbackQuery) -> None:
    await _safe_edit(query, "❓ Неизвестная команда", get_main_menu())
