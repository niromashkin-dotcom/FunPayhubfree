# runtime/backup/backup_manager.py
import os
import json
import zipfile
import hashlib
import shutil
from datetime import datetime
from typing import Dict, Any, Optional
from runtime.backup.models import BackupMetadata, BackupInfo


class BackupManager:
    def __init__(self, runtime_controller, storage_dir: str = "data/backups"):
        self.runtime_controller = runtime_controller
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)

    def _get_state_manager(self):
        # Получаем state_manager из orchestrator (упрощённо, через runtime_controller)
        # В реальном коде нужно передать ссылку. Для простоты оставим заглушку.
        # Здесь предполагается, что runtime_controller имеет доступ к оркестратору.
        # Реализуем через атрибут.
        if hasattr(self.runtime_controller, '_orchestrator'):
            return self.runtime_controller._orchestrator.state_manager
        return None

    def _get_plugin_manager(self):
        return self.runtime_controller._plugin_manager

    def _get_observability_hub(self):
        if hasattr(self.runtime_controller, '_observability'):
            return self.runtime_controller._observability
        return None

    def _get_recovery_manager(self):
        if hasattr(self.runtime_controller, '_orchestrator'):
            return self.runtime_controller._orchestrator.recovery_manager
        return None

    def _get_boot_journal(self):
        if hasattr(self.runtime_controller, '_orchestrator'):
            return getattr(self.runtime_controller._orchestrator, 'boot_journal', None)
        return None

    def create_backup(self) -> Optional[BackupInfo]:
        """Создаёт полный бэкап системы."""
        backup_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_dir = os.path.join(self.storage_dir, backup_id)
        os.makedirs(backup_dir, exist_ok=True)

        # 1. Сохраняем снапшот (через StateManager)
        state_manager = self._get_state_manager()
        if state_manager:
            state_manager.save_snapshot()  # принудительно сохраняем текущий снапшот
            snapshot_path = os.path.join(backup_dir, "snapshot.json")
            shutil.copy("data/state/runtime_state.json", snapshot_path)
        else:
            # если StateManager недоступен, создаём свой снапшот
            snapshot = self._create_snapshot()
            with open(os.path.join(backup_dir, "snapshot.json"), "w") as f:
                json.dump(snapshot, f, indent=2)

        # 2. Сохраняем health scores
        pm = self._get_plugin_manager()
        health_scores = pm.get_all_health_scores()
        with open(os.path.join(backup_dir, "health_scores.json"), "w") as f:
            json.dump(health_scores, f, indent=2)

        # 3. Сохраняем quarantine data
        quarantine_data = pm.get_quarantine_data()
        with open(os.path.join(backup_dir, "quarantine.json"), "w") as f:
            json.dump(quarantine_data, f, indent=2)

        # 4. Сохраняем watchdog state (low_score_counter)
        watchdog_state = {
            "low_score_counter": getattr(pm, '_low_score_counter', {}),
            "quarantine_attempts": getattr(pm, '_quarantine_attempts', {})
        }
        with open(os.path.join(backup_dir, "watchdog_state.json"), "w") as f:
            json.dump(watchdog_state, f, indent=2)

        # 5. Сохраняем recovery report (если есть)
        recovery = self._get_recovery_manager()
        if recovery and recovery.report:
            with open(os.path.join(backup_dir, "recovery_report.json"), "w") as f:
                json.dump(recovery.report.to_dict(), f, indent=2)

        # 6. Сохраняем boot journal
        boot_journal = self._get_boot_journal()
        if boot_journal:
            boot_data = boot_journal.load()
            with open(os.path.join(backup_dir, "boot_journal.json"), "w") as f:
                json.dump(boot_data, f, indent=2)

        # 7. Сохраняем метаданные бэкапа
        total_size = self._get_dir_size(backup_dir)
        checksum = self._compute_checksum(backup_dir)
        metadata = BackupMetadata(
            backup_id=backup_id,
            created_at=datetime.utcnow().isoformat(),
            runtime_version=self.runtime_controller.runtime_version,
            checksum=checksum,
            size_bytes=total_size
        )
        with open(os.path.join(backup_dir, "metadata.json"), "w") as f:
            json.dump(metadata.__dict__, f, indent=2)

        # 8. Архивация в zip (опционально, но для экономии места)
        zip_path = os.path.join(self.storage_dir, f"{backup_id}.zip")
        self._zip_directory(backup_dir, zip_path)
        shutil.rmtree(backup_dir)  # удаляем папку, оставляем zip

        return BackupInfo(
            backup_id=backup_id,
            created_at=metadata.created_at,
            size_bytes=total_size,
            path=zip_path
        )

    def _create_snapshot(self) -> Dict[str, Any]:
        """Создаёт снапшот без StateManager (fallback)."""
        pm = self._get_plugin_manager()
        obs = self._get_observability_hub()
        plugin_states = {name: pm.get_plugin_state(name) for name in pm.get_plugin_names()}
        metrics = obs.get_plugin_metrics() if obs else {}
        health = obs.get_detailed_health() if obs else {}
        notifications = []
        return {
            "version": 1,
            "created_at": datetime.utcnow().timestamp(),
            "data": {
                "plugin_states": plugin_states,
                "metrics": metrics,
                "health": health,
                "notifications": notifications
            }
        }

    def _get_dir_size(self, path: str) -> int:
        total = 0
        for dirpath, _, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                total += os.path.getsize(fp)
        return total

    def _compute_checksum(self, path: str) -> str:
        """Вычисляет sha256 для папки (все файлы)."""
        sha256 = hashlib.sha256()
        for dirpath, _, filenames in sorted(os.walk(path)):
            for fname in sorted(filenames):
                filepath = os.path.join(dirpath, fname)
                with open(filepath, "rb") as f:
                    while chunk := f.read(8192):
                        sha256.update(chunk)
        return sha256.hexdigest()

    def _zip_directory(self, source_dir: str, output_zip: str):
        with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(source_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, source_dir)
                    zipf.write(file_path, arcname)

    def list_backups(self) -> list:
        backups = []
        for filename in os.listdir(self.storage_dir):
            if filename.endswith(".zip"):
                backup_id = filename[:-4]
                zip_path = os.path.join(self.storage_dir, filename)
                try:
                    with zipfile.ZipFile(zip_path, 'r') as zf:
                        with zf.open("metadata.json") as mf:
                            metadata = json.load(mf)
                    backups.append(BackupInfo(
                        backup_id=backup_id,
                        created_at=metadata.get("created_at", ""),
                        size_bytes=metadata.get("size_bytes", 0),
                        path=zip_path
                    ))
                except:
                    # старый или повреждённый бэкап
                    pass
        return sorted(backups, key=lambda x: x.created_at, reverse=True)

    def delete_backup(self, backup_id: str) -> bool:
        zip_path = os.path.join(self.storage_dir, f"{backup_id}.zip")
        if os.path.exists(zip_path):
            os.remove(zip_path)
            return True
        return False