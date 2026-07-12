"""Безопасная диагностическая симуляция состояния торговых плагинов.

Модуль намеренно не создаёт лоты, не отправляет сообщения и не изменяет
конфигурацию: endpoint Telegram должен быть безопасен в production.
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple


class PluginSimulator:
    """Проверяет, что основные торговые плагины загружены и настроены."""

    PLUGINS = ("autosmm_plugin", "autodonate_plugin")

    def __init__(self, plugin_manager: Any = None):
        self.plugin_manager = plugin_manager

    def run_all(self) -> Tuple[Dict[str, Any], bool]:
        plugins: List[Dict[str, Any]] = []
        registry = getattr(self.plugin_manager, "plugins", {}) if self.plugin_manager else {}
        for name in self.PLUGINS:
            plugin = registry.get(name) if isinstance(registry, dict) else None
            if plugin is None:
                plugins.append({"name": name, "ok": False, "message": "Плагин не загружен"})
                continue
            config = getattr(plugin, "config", {})
            config_ok = isinstance(config, dict)
            plugins.append({
                "name": name,
                "ok": config_ok,
                "enabled": bool(config.get("enabled", False)) if config_ok else False,
                "dry_run": bool(config.get("dry_run", True)) if config_ok else True,
                "message": "Конфигурация доступна" if config_ok else "Некорректная конфигурация",
            })
        all_ok = bool(plugins) and all(item["ok"] for item in plugins)
        return {"all_ok": all_ok, "plugins": plugins, "mode": "diagnostic"}, all_ok
