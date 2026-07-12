"""Контрактные проверки панели Telegram без доступа к Telegram/FunPay."""
import ast
from pathlib import Path

from runtime.simulator import PluginSimulator
from bot.formatters import format_balance, format_market_status


ROOT = Path(__file__).resolve().parents[1]


def _callback_values(tree):
    values = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "InlineKeyboardButton":
            for keyword in node.keywords:
                if keyword.arg == "callback_data" and isinstance(keyword.value, ast.Constant):
                    values.add(keyword.value.value)
    return values


def _handled_callbacks(tree):
    values = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and isinstance(node.left, ast.Name):
            left = node.left.id
            if left == "cmd":
                for item in node.comparators:
                    if isinstance(item, ast.Constant) and isinstance(item.value, str):
                        values.add(item.value)
            elif left == "query":
                for item in node.comparators:
                    if isinstance(item, ast.Constant) and isinstance(item.value, str):
                        values.add(item.value)
        # aiogram 3: F.data == "..."
        if isinstance(node, ast.Compare) and isinstance(node.left, ast.Attribute):
            try:
                if node.left.attr == "data" and getattr(node.left.value, "id", None) == "F":
                    for item in node.comparators:
                        if isinstance(item, ast.Constant) and isinstance(item.value, str):
                            values.add(item.value)
            except Exception:
                pass
        # aiogram 3: F.data.in_({...})
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr == "data" and isinstance(func.value, ast.Name) and func.value.id == "F":
                for arg in node.args:
                    if isinstance(arg, ast.Set):
                        for elt in arg.elts:
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                values.add(elt.value)
    return values


def test_each_main_menu_callback_has_a_handler():
    handler_files = [
        ROOT / "bot" / "handlers" / "callbacks.py",
        ROOT / "bot" / "handlers" / "ai_agent.py",
    ]
    main_callbacks = {
        "start_hub", "stop_hub", "report", "logs_view", "balance",
        "simulation", "system_status", "lots", "ai_agent", "wallet",
    }
    handled = set()
    for path in handler_files:
        if path.exists():
            tree = ast.parse(path.read_text(encoding="utf-8"))
            handled |= _handled_callbacks(tree)
    assert main_callbacks <= handled


def test_formatters_do_not_return_raw_json_or_unescaped_html():
    balance = format_balance({
        "available": True,
        "balance": {"available_rub": 12.5, "lot_id_used": "<lot>"},
        "wallets": [],
    })
    market = format_market_status({"niches": [{"name": "<unsafe>"}]})
    assert "{\"" not in balance
    assert "&lt;lot&gt;" in balance
    assert "&lt;unsafe&gt;" in market


def test_simulation_is_diagnostic_and_does_not_require_network():
    class Plugin:
        config = {"enabled": True, "dry_run": True}

    class Manager:
        plugins = {"autosmm_plugin": Plugin(), "autodonate_plugin": Plugin()}

    report, ok = PluginSimulator(Manager()).run_all()
    assert ok is True
    assert report["mode"] == "diagnostic"
    assert all(item["dry_run"] is True for item in report["plugins"])
