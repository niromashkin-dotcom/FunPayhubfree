# plugins/execution/process_manager.py
import threading
import time
from enum import Enum
from dataclasses import dataclass
from typing import Dict, Optional, List
from datetime import datetime

class ProcessStatus(Enum):
    STARTING = "starting"
    RUNNING = "running"
    STOPPED = "stopped"
    CRASHED = "crashed"
    RESTARTING = "restarting"

@dataclass
class ProcessInfo:
    plugin_name: str
    pid: int
    started_at: float
    restart_count: int = 0
    last_heartbeat: float = 0
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    thread_count: int = 0
    last_resource_update: float = 0.0
    status: ProcessStatus = ProcessStatus.STARTING

class ProcessManager:
    def __init__(self, plugin_manager, quarantine_callback):
        self._processes: Dict[str, ProcessInfo] = {}
        self._lock = threading.Lock()
        self._plugin_manager = plugin_manager
        self._quarantine_callback = quarantine_callback  # quarantine_plugin(name, reason)

    def register(self, plugin_name: str, pid: int):
        with self._lock:
            self._processes[plugin_name] = ProcessInfo(
                plugin_name=plugin_name,
                pid=pid,
                started_at=time.time(),
                restart_count=0,
                last_heartbeat=time.time(),
                status=ProcessStatus.STARTING
            )

    def update_heartbeat(self, plugin_name: str):
        with self._lock:
            if plugin_name in self._processes:
                self._processes[plugin_name].last_heartbeat = time.time()
                if self._processes[plugin_name].status == ProcessStatus.STARTING:
                    self._processes[plugin_name].status = ProcessStatus.RUNNING

    def mark_crashed(self, plugin_name: str, restart_allowed: bool = True):
        with self._lock:
            if plugin_name not in self._processes:
                return
            info = self._processes[plugin_name]
            info.status = ProcessStatus.CRASHED
            info.restart_count += 1
            if not restart_allowed:
                return
            # Автоматический рестарт до 3 раз
            if info.restart_count <= 3:
                info.status = ProcessStatus.RESTARTING
                # Сигнал для внешнего перезапуска (будет обработан SubprocessExecutor)
            else:
                # После 3 рестартов – карантин
                if self._quarantine_callback:
                    self._quarantine_callback(plugin_name, f"Process crashed {info.restart_count} times")
                info.status = ProcessStatus.STOPPED

    def unregister(self, plugin_name: str):
        with self._lock:
            if plugin_name in self._processes:
                del self._processes[plugin_name]

    def get_process(self, plugin_name: str) -> Optional[ProcessInfo]:
        with self._lock:
            return self._processes.get(plugin_name)

    def get_all_processes(self) -> List[ProcessInfo]:
        with self._lock:
            return list(self._processes.values())

    def restart_process(self, plugin_name: str):
        # Перезапуск инициируется SubprocessExecutor, здесь только сбрасываем счётчик при успешном старте
        with self._lock:
            if plugin_name in self._processes:
                self._processes[plugin_name].restart_count = 0
                self._processes[plugin_name].status = ProcessStatus.STARTING

    def stop_process(self, plugin_name: str):
        with self._lock:
            if plugin_name in self._processes:
                self._processes[plugin_name].status = ProcessStatus.STOPPED

class ProcessMonitor:
    def __init__(self, process_manager, executor, check_interval: int = 5, heartbeat_timeout: int = 15):
        self.process_manager = process_manager
        self.executor = executor  # SubprocessExecutor
        self.check_interval = check_interval
        self.heartbeat_timeout = heartbeat_timeout
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
            now = time.time()
            for info in self.process_manager.get_all_processes():
                # Проверка heartbeat
                if now - info.last_heartbeat > self.heartbeat_timeout:
                    # Процесс не отвечает
                    self.process_manager.mark_crashed(info.plugin_name, restart_allowed=True)
                    # Запускаем перезапуск через executor
                    self.executor._restart_plugin_process(info.plugin_name)
                else:
                    # Если процесс был в состоянии RESTARTING и heartbeat пришёл – сбрасываем статус
                    if info.status == ProcessStatus.RESTARTING:
                        self.process_manager.restart_process(info.plugin_name)
