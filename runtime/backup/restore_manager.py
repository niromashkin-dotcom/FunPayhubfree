# runtime/backup/restore_manager.py
import os
import json
import zipfile
import shutil
import tempfile
from typing import Dict, Any
from runtime.backup.models import BackupInfo


class RestoreManager:
    def __init__(self, runtime_controller):
        self.runtime_controller = runtime_controller
        self.pm = runtime_controller._plugin_manager
        self.state_manager = None
        if hasattr(runtime_controller, '_orchestrator'):
            self.state_manager = runtime_controller._orchestrator.state_manager
        self.recovery_manager = None
        if hasattr(runtime_controller, '_orchestrator'):
            self.recovery_manager = runtime_controller._orchestrator.recovery_manager
        self.boot_journal = None
        if hasattr(runtime_controller, '_orchestrator'):
            self.boot_journal = getattr(runtime_controller._orchestrator, 'boot_journal', None)

    def restore_from_backup(self, backup_info: BackupInfo) -> bool:
        """Восстанавливает систему из бэкапа (полное замещение состояния)."""
        if not os.path.exists(backup_info.path):
            return False

        # Распаковываем zip во временную папку
        with tempfile.TemporaryDirectory() as tmpdir:
            with zipfile.ZipFile(backup_info.path, 'r') as zf:
                zf.extractall(tmpdir)

            # 1. Восстанавливаем snapshot
            snapshot_path = os.path.join(tmpdir, "snapshot.json")
            if os.path.exists(snapshot_path) and self.state_manager:
                # Загружаем snapshot напрямую в StateManager (без событий)
                with open(snapshot_path, 'r') as f:
                    snapshot = json.load(f)
                self.state_manager.snapshot_engine.apply_snapshot(snapshot)

            # 2. Восстанавливаем health scores
            health_path = os.path.join(tmpdir, "health_scores.json")
            if os.path.exists(health_path):
                # Health scores не восстанавливаем напрямую, а сбрасываем
                # Плагины пересчитают их заново
                pass

            # 3. Восстанавливаем quarantine data
            quarantine_path = os.path.join(tmpdir, "quarantine.json")
            if os.path.exists(quarantine_path):
                with open(quarantine_path, 'r') as f:
                    quarantine_data = json.load(f)
                self.pm.restore_quarantine(quarantine_data)

            # 4. Восстанавливаем watchdog state
            watchdog_path = os.path.join(tmpdir, "watchdog_state.json")
            if os.path.exists(watchdog_path):
                with open(watchdog_path, 'r') as f:
                    wd_state = json.load(f)
                self.pm._low_score_counter = wd_state.get("low_score_counter", {})
                self.pm._quarantine_attempts = wd_state.get("quarantine_attempts", {})

            # 5. Восстанавливаем recovery report (не обязательно)
            # 6. Восстанавливаем boot journal
            boot_path = os.path.join(tmpdir, "boot_journal.json")
            if os.path.exists(boot_path) and self.boot_journal:
                with open(boot_path, 'r') as f:
                    boot_data = json.load(f)
                self.boot_journal.save(boot_data)

        # После восстановления рекомендуется перезагрузить систему
        return True