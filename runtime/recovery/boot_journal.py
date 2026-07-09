# runtime/recovery/boot_journal.py
import json
import os
import time
from typing import Optional, Dict, Any

class BootJournal:
    def __init__(self, file_path: str = "data/state/boot_journal.json"):
        self.file_path = file_path
        self._ensure_dir()

    def _ensure_dir(self):
        directory = os.path.dirname(self.file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)

    def load(self) -> Dict[str, Any]:
        if not os.path.exists(self.file_path):
            return {
                "last_start": 0,
                "last_shutdown": None,
                "status": "unknown",
                "version": "0.0.0"
            }
        try:
            with open(self.file_path, 'r') as f:
                return json.load(f)
        except:
            return {
                "last_start": 0,
                "last_shutdown": None,
                "status": "corrupted",
                "version": "0.0.0"
            }

    def save(self, data: Dict[str, Any]) -> bool:
        try:
            # Атомарное сохранение
            tmp_path = self.file_path + ".tmp"
            with open(tmp_path, 'w') as f:
                json.dump(data, f, indent=2)
            os.replace(tmp_path, self.file_path)
            return True
        except Exception as e:
            print(f"[BootJournal] Save error: {e}")
            return False

    def mark_start(self, version: str) -> None:
        journal = self.load()
        journal["last_start"] = time.time()
        journal["status"] = "running"
        journal["version"] = version
        self.save(journal)

    def mark_shutdown(self, clean: bool = True) -> None:
        journal = self.load()
        journal["last_shutdown"] = time.time()
        journal["status"] = "clean_shutdown" if clean else "unknown"
        self.save(journal)

    def was_crash(self) -> bool:
        journal = self.load()
        return journal.get("status") == "running" and journal.get("last_shutdown") is None

    def get_last_start(self) -> float:
        return self.load().get("last_start", 0)

    def get_last_shutdown(self) -> Optional[float]:
        return self.load().get("last_shutdown")