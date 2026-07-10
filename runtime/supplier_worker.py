"""
Supplier Worker Pool — конкурентность (Этап E).

Каждый поставщик получает свой поток-очередь.
Если один поставщик завис — остальные продолжают.
"""

import time
import queue
import threading
import logging
from typing import Dict, List, Callable, Optional

logger = logging.getLogger("FunPayHUB.SupplierWorker")


class SupplierWorker:
    """Очередь-поток для одного поставщика."""

    def __init__(self, supplier_name: str):
        self.name = supplier_name
        self._queue: queue.Queue = queue.Queue()
        self._thread = threading.Thread(target=self._run, name=f"SW-{supplier_name}", daemon=True)
        self._stop = threading.Event()
        self._active = True

    def start(self):
        self._thread.start()
        logger.debug(f"[SW] {self.name} started")

    def stop(self):
        self._stop.set()
        self._active = False

    def submit(self, task: Callable, callback: Optional[Callable] = None):
        """Добавить задачу в очередь поставщика."""
        self._queue.put((task, callback))

    @property
    def active(self) -> bool:
        return self._active

    def _run(self):
        while not self._stop.is_set():
            try:
                task, callback = self._queue.get(timeout=1)
                try:
                    result = task()
                    if callback:
                        callback(result)
                except Exception as e:
                    logger.error(f"[SW] {self.name} task error: {e}")
                finally:
                    self._queue.task_done()
            except queue.Empty:
                continue


class SupplierWorkerPool:
    """Пул потоков для всех поставщиков."""

    def __init__(self):
        self._workers: Dict[str, SupplierWorker] = {}

    def get_worker(self, supplier: str) -> SupplierWorker:
        """Получить (или создать) воркер для поставщика."""
        if supplier not in self._workers:
            self._workers[supplier] = SupplierWorker(supplier)
            self._workers[supplier].start()
        return self._workers[supplier]

    def submit(self, supplier: str, task: Callable, callback: Optional[Callable] = None):
        """Отправить задачу поставщику."""
        worker = self.get_worker(supplier)
        worker.submit(task, callback)

    def stop_all(self):
        for w in self._workers.values():
            w.stop()

    @property
    def active_workers(self) -> List[str]:
        return [name for name, w in self._workers.items() if w.active]
