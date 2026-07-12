# plugins/execution/subprocess_executor.py
import multiprocessing
import threading
import time
from plugins.execution.base import PluginExecutor
from plugins.execution.process_manager import ProcessManager, ProcessMonitor

class SubprocessExecutor(PluginExecutor):
    def __init__(self, plugin_manager=None):
        self._processes = {}
        self._plugin_manager = plugin_manager
        self._process_manager = None
        self._monitor = None

    def set_process_manager(self, process_manager: ProcessManager):
        self._process_manager = process_manager
        self._monitor = ProcessMonitor(process_manager, self)
        self._monitor.start()

    def start(self, plugin):
        self.start_plugin(plugin)

    def stop(self, plugin):
        self.stop_plugin(plugin)

    def start_plugin(self, plugin):
        plugin_name = plugin.module_name
        if plugin_name in self._processes:
            self.stop_plugin(plugin)
        from plugins.execution.worker import worker_main
        event_queue = multiprocessing.Queue()
        result_queue = multiprocessing.Queue()
        process = multiprocessing.Process(
            target=worker_main,
            args=(plugin_name, event_queue, result_queue, plugin.__class__)
        )
        process.start()
        self._processes[plugin_name] = {
            "process": process,
            "event_queue": event_queue,
            "result_queue": result_queue
        }
        if self._process_manager:
            self._process_manager.register(plugin_name, process.pid)

    def stop_plugin(self, plugin):
        plugin_name = plugin.module_name
        if plugin_name not in self._processes:
            return
        worker = self._processes[plugin_name]
        try:
            worker["event_queue"].put(("stop", None))
            worker["process"].join(timeout=5)
        except Exception:
            pass
        if worker["process"].is_alive():
            worker["process"].terminate()
        del self._processes[plugin_name]
        if self._process_manager:
            self._process_manager.unregister(plugin_name)

    def execute_event(self, plugin, event_name, event, **kwargs):
        plugin_name = plugin.module_name
        if plugin_name not in self._processes:
            self.start_plugin(plugin)
        worker = self._processes[plugin_name]
        try:
            worker["event_queue"].put(("event", event_name, event))
            result = worker["result_queue"].get(timeout=30)
            if isinstance(result, Exception):
                raise result
            return result
        except Exception as e:
            if self._process_manager:
                self._process_manager.mark_crashed(plugin_name, restart_allowed=True)
            self.stop_plugin(plugin)
            raise e

    def _restart_plugin_process(self, plugin_name: str):
        if plugin_name not in self._processes:
            return
        self.stop_plugin_by_name(plugin_name)
        # перезапуск произойдёт при следующем execute_event

    def stop_plugin_by_name(self, plugin_name: str):
        if plugin_name not in self._processes:
            return
        worker = self._processes[plugin_name]
        try:
            worker["event_queue"].put(("stop", None))
            worker["process"].join(timeout=5)
        except Exception:
            pass
        if worker["process"].is_alive():
            worker["process"].terminate()
        del self._processes[plugin_name]
        if self._process_manager:
            self._process_manager.unregister(plugin_name)
