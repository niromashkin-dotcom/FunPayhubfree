# runtime/export/import_manager.py
import json
from typing import Dict, Any, Tuple, List
from runtime.export.schema import validate_export
from runtime.export.validators import validate_plugins, validate_runtime_settings, validate_observability, validate_notifications


class ImportManager:
    def __init__(self, runtime_controller):
        self.runtime_controller = runtime_controller
        self.pm = runtime_controller._plugin_manager

    def import_from_json(self, json_str: str, dry_run: bool = False, import_mode: str = "merge") -> Dict[str, Any]:
        """Основной метод импорта."""
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            return self._report(False, [], [], f"Invalid JSON: {e}")

        # 1. Schema validation
        valid, msg, export_data = validate_export(data)
        if not valid:
            return self._report(False, [], [], msg)

        # 2. Дополнительные проверки
        existing_plugins = self.pm.get_plugin_names()
        plugin_warnings = validate_plugins(export_data, existing_plugins)
        runtime_warnings = validate_runtime_settings(export_data)
        obs_warnings = validate_observability(export_data)
        notif_warnings = validate_notifications(export_data)
        all_warnings = plugin_warnings + runtime_warnings + obs_warnings + notif_warnings

        if dry_run:
            # Возвращаем только отчёт, ничего не меняем
            changes = self._calculate_changes(export_data)
            return self._report(True, changes, all_warnings, "Dry run completed, no changes applied")

        # 3. Применяем изменения (merge)
        changes = []
        if import_mode == "merge":
            changes.extend(self._merge_plugins(export_data))
            changes.extend(self._merge_runtime_settings(export_data))
            changes.extend(self._merge_observability(export_data))
            changes.extend(self._merge_notifications(export_data))
        else:
            # replace – пока не реализуем, только заглушка
            return self._report(False, [], [], f"Import mode '{import_mode}' not implemented yet")

        return self._report(True, changes, all_warnings, f"Import completed, {len(changes)} changes applied")

    def _calculate_changes(self, export_data) -> List[Dict]:
        """Вычисляет, что изменится при импорте (без применения)."""
        changes = []
        # Аналогично _merge_*, но без записи
        return changes  # упрощённо для dry-run

    def _merge_plugins(self, export_data) -> List[Dict]:
        changes = []
        for plugin_export in export_data.plugins:
            if not self.pm.plugin_exists(plugin_export.module):
                # Плагин не установлен – пропускаем
                continue
            plugin = self.pm.get_plugin_object(plugin_export.module)
            if not plugin:
                continue
            # Обновляем конфиг (merge)
            old_config = plugin.get_config()
            new_config = {**old_config, **plugin_export.config}
            if new_config != old_config:
                plugin.config = new_config
                plugin.save_config()
                changes.append({
                    "type": "plugin_config",
                    "plugin": plugin_export.module,
                    "field": "config",
                    "old": old_config,
                    "new": new_config
                })
            # Обновляем enabled
            if plugin.is_enabled() != plugin_export.enabled:
                if plugin_export.enabled:
                    self.pm.enable(plugin_export.module)
                else:
                    self.pm.disable(plugin_export.module)
                changes.append({
                    "type": "plugin_enabled",
                    "plugin": plugin_export.module,
                    "old": plugin.is_enabled(),
                    "new": plugin_export.enabled
                })
        return changes

    def _merge_runtime_settings(self, export_data) -> List[Dict]:
        changes = []
        # Обновляем пороги
        pm = self.pm
        new_thresholds = export_data.runtime_settings.health_thresholds
        if pm.health_threshold_normal != new_thresholds.get("normal", 80):
            old = pm.health_threshold_normal
            pm.health_threshold_normal = new_thresholds["normal"]
            changes.append({"type": "runtime_setting", "field": "health_threshold_normal", "old": old, "new": pm.health_threshold_normal})
        if pm.quarantine_threshold != new_thresholds.get("quarantine", 40):
            old = pm.quarantine_threshold
            pm.quarantine_threshold = new_thresholds["quarantine"]
            changes.append({"type": "runtime_setting", "field": "quarantine_threshold", "old": old, "new": pm.quarantine_threshold})
        if pm.quarantine_checks_required != new_thresholds.get("checks_required", 3):
            old = pm.quarantine_checks_required
            pm.quarantine_checks_required = new_thresholds["checks_required"]
            changes.append({"type": "runtime_setting", "field": "quarantine_checks_required", "old": old, "new": pm.quarantine_checks_required})
        return changes

    def _merge_observability(self, export_data) -> List[Dict]:
        # Пока не реализуем, т.к. observability настройки статичны
        return []

    def _merge_notifications(self, export_data) -> List[Dict]:
        changes = []
        # Обновляем discord_webhook в конфиге runtime
        webhook = export_data.notifications.discord_webhook
        if webhook != self.runtime_controller.config.get("discord_webhook"):
            self.runtime_controller.config["discord_webhook"] = webhook
            changes.append({"type": "notifications_setting", "field": "discord_webhook", "old": "***", "new": "***"})
        return changes

    def _report(self, success: bool, changes: List[Dict], warnings: List[Tuple[str, str, str]], message: str) -> Dict[str, Any]:
        return {
            "success": success,
            "message": message,
            "changes": changes,
            "warnings": [{"code": w[0], "field": w[1], "message": w[2]} for w in warnings]
        }