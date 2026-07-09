# runtime/recovery/recovery_manager.py
import time
from typing import Dict, Any
from runtime.recovery.boot_journal import BootJournal
from runtime.recovery.report import RecoveryReport
from runtime.state.storage import JsonStorage
from runtime.state.migrations import migrate_snapshot
from runtime.state.snapshot_engine import SnapshotEngine

class RecoveryManager:
    def __init__(self, runtime_controller, boot_journal: BootJournal, snapshot_engine: SnapshotEngine):
        self.runtime_controller = runtime_controller
        self.boot_journal = boot_journal
        self.snapshot_engine = snapshot_engine
        self.report = RecoveryReport()

    def is_crash_recovery(self) -> bool:
        return self.boot_journal.was_crash()

    def perform_recovery(self) -> RecoveryReport:
        self.report.set_crash(self.boot_journal.get_last_start())
        # Пытаемся загрузить последний snapshot
        storage = JsonStorage("data/state/runtime_state.json")
        data = storage.load()
        if data:
            snapshot = migrate_snapshot(data, self.snapshot_engine.CURRENT_VERSION)
            self.report.set_snapshot(snapshot.get("created_at", 0))
            # Восстанавливаем только безопасные состояния
            plugin_states = snapshot.get("data", {}).get("plugin_states", {})
            safe_states = {"active", "disabled"}
            for name, state in plugin_states.items():
                if state in safe_states:
                    # Восстановление через restore_states (без событий)
                    self.runtime_controller._plugin_manager.restore_states({name: state})
                    self.report.add_restored(name)
                else:
                    self.report.add_skipped(name)
            self.report.set_message("Recovery completed with snapshot")
        else:
            self.report.set_message("No snapshot found, starting fresh")
        return self.report

    def get_recovery_status(self) -> Dict[str, Any]:
        status = {
            "crash_detected": self.is_crash_recovery(),
            "last_start": self.boot_journal.get_last_start(),
            "last_shutdown": self.boot_journal.get_last_shutdown(),
            "recovery_report": self.report.to_dict() if self.is_crash_recovery() else None
        }
        return status