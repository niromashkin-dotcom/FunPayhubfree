import psutil
import threading
import time
from typing import Dict, Optional

class ResourceMonitor:
    def __init__(self, process_manager, check_interval: int = 5):
        self.process_manager = process_manager
        self.check_interval = check_interval
        self._running = False
        self._thread = None
        self._stop_event = threading.Event()

    def start(self):
        if self._running:
            return
        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)

    def _monitor_loop(self):
        while not self._stop_event.wait(self.check_interval):
            if not self._running:
                break
            self._collect_resources()

    def _collect_resources(self):
        for info in self.process_manager.get_all_processes():
            pid = info.pid
            try:
                proc = psutil.Process(pid)
                with proc.oneshot():
                    cpu = proc.cpu_percent(interval=0.1)
                    mem = proc.memory_info().rss / (1024 * 1024)  # MB
                    threads = proc.num_threads()
                    info.cpu_percent = cpu
                    info.memory_mb = mem
                    info.thread_count = threads
                    info.last_resource_update = time.time()
            except psutil.NoSuchProcess:
                pass
            except Exception:
                pass