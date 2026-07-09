# runtime/export/validators.py
from typing import List, Tuple
from runtime.export.models import ExportData


def validate_plugins(export_data: ExportData, existing_plugins: List[str]) -> List[Tuple[str, str, str]]:
    warnings = []
    for plugin in export_data.plugins:
        if plugin.module not in existing_plugins:
            warnings.append(("plugin_missing", plugin.module, f"Plugin {plugin.module} not found in current system, will be skipped"))
    return warnings


def validate_runtime_settings(export_data: ExportData) -> List[Tuple[str, str, str]]:
    warnings = []
    if export_data.runtime_settings.health_thresholds.get("quarantine", 40) < 0 or export_data.runtime_settings.health_thresholds.get("quarantine", 40) > 100:
        warnings.append(("invalid_threshold", "quarantine", "Quarantine threshold must be between 0 and 100"))
    if export_data.runtime_settings.health_thresholds.get("normal", 80) < export_data.runtime_settings.health_thresholds.get("quarantine", 40):
        warnings.append(("invalid_threshold", "normal", "Normal threshold should be greater than quarantine threshold"))
    return warnings


def validate_observability(export_data: ExportData) -> List[Tuple[str, str, str]]:
    warnings = []
    if export_data.observability.metrics_retention < 100:
        warnings.append(("small_retention", "metrics_retention", "Metrics retention is very small (<100), may lose history"))
    return warnings


def validate_notifications(export_data: ExportData) -> List[Tuple[str, str, str]]:
    warnings = []
    if export_data.notifications.discord_webhook and not export_data.notifications.discord_webhook.startswith("https://"):
        warnings.append(("invalid_webhook", "discord_webhook", "Discord webhook URL does not look valid"))
    return warnings