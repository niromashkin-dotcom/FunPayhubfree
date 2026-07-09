# runtime/recovery/report.py
import time
from typing import List, Dict, Any

class RecoveryReport:
    def __init__(self):
        self.crashed = False
        self.crash_time = None
        self.snapshot_used = None
        self.plugins_restored: List[str] = []
        self.plugins_skipped: List[str] = []
        self.message = ""

    def set_crash(self, crash_time: float):
        self.crashed = True
        self.crash_time = crash_time

    def set_snapshot(self, snapshot_time: float):
        self.snapshot_used = snapshot_time

    def add_restored(self, plugin: str):
        self.plugins_restored.append(plugin)

    def add_skipped(self, plugin: str):
        self.plugins_skipped.append(plugin)

    def set_message(self, msg: str):
        self.message = msg

    def to_dict(self) -> Dict[str, Any]:
        return {
            "crashed": self.crashed,
            "crash_time": self.crash_time,
            "snapshot_used": self.snapshot_used,
            "plugins_restored": self.plugins_restored,
            "plugins_skipped": self.plugins_skipped,
            "message": self.message
        }

    def save(self, file_path: str = "data/state/recovery_report.json"):
        import json, os
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
        with open(file_path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)