# runtime/backup/scheduler.py
import threading
import time
from typing import Optional
from runtime.backup.backup_manager import BackupManager


class BackupScheduler:
    def __init__(self, backup_manager: BackupManager, interval_seconds: int = 86400, max_backups: int = 7):
        self.backup_manager = backup_manager
        self.interval_seconds = interval_seconds
        self.max_backups = max_backups
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def start(self):
        if self._running:
            return
        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        print(f"[BackupScheduler] Started with interval {self.interval_seconds}s")

    def stop(self):
        self._running = False
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        print("[BackupScheduler] Stopped")

    def _loop(self):
        while not self._stop_event.wait(self.interval_seconds):
            if not self._running:
                break
            self._create_backup_and_rotate()

    def _create_backup_and_rotate(self):
        try:
            backup = self.backup_manager.create_backup()
            if backup:
                print(f"[BackupScheduler] Created backup {backup.backup_id}")
                self._rotate_backups()
        except Exception as e:
            print(f"[BackupScheduler] Backup failed: {e}")

    def _rotate_backups(self):
        backups = self.backup_manager.list_backups()
        if len(backups) > self.max_backups:
            to_delete = backups[self.max_backups:]
            for b in to_delete:
                self.backup_manager.delete_backup(b.backup_id)
                print(f"[BackupScheduler] Deleted old backup {b.backup_id}")