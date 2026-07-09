# plugins/execution/inprocess_executor.py
import time
from plugins.execution.base import PluginExecutor

class InProcessExecutor(PluginExecutor):
    def execute_event(self, plugin, event, **kwargs):
        start = time.time()
        try:
            plugin.on_event(event)
        except Exception as e:
            # Метрики и логирование будут на уровне PluginManager
            raise e
        finally:
            duration = time.time() - start
            # Записываем длительность (будет использовано метриками)
            if hasattr(plugin, '_last_execution_time'):
                plugin._last_execution_time = duration
        return True

    def start(self, plugin):
        pass

    def stop(self, plugin):
        pass
