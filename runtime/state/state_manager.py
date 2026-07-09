import threading
import time
from typing import Optional
from runtime.state.storage import JsonStorage
from runtime.state.snapshot_engine import SnapshotEngine
from runtime.state.migrations import migrate_snapshot

class StateManager:
    def __init__(self, storage: JsonStorage, snapshot_engine: SnapshotEngine, autosave_interval: int = 60):
        self.storage = storage
        self.snapshot_engine = snapshot_engine
        self.autosave_interval = autosave_interval
        self._lock = threading.Lock()
        self._running = False
        self._thread = None
        self._stop_event = threading.Event()

    def save_snapshot(self):
        with self._lock:
            snapshot = self.snapshot_engine.create_snapshot()
            self.storage.save(snapshot)
            print("[StateManager] Snapshot saved")

    def load_snapshot(self) -> bool:
        data = self.storage.load()
        if not data:
            return False
        migrated = migrate_snapshot(data, self.snapshot_engine.CURRENT_VERSION)
        return self.snapshot_engine.apply_snapshot(migrated)

    def _autosave_loop(self):
        while not self._stop_event.wait(self.autosave_interval):
            if self._running:
                self.save_snapshot()

    def start_autosave(self):
        if self._running:
            return
        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._autosave_loop, daemon=True)
        self._thread.start()
        print(f"[StateManager] Autosave started (interval={self.autosave_interval}s)")

    def stop_autosave(self):
        self._running = False
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)
        self.save_snapshot()
        print("[StateManager] Autosave stopped, final snapshot saved")