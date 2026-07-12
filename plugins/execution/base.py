# plugins/execution/base.py
from abc import ABC, abstractmethod

class PluginExecutor(ABC):
    @abstractmethod
    def execute_event(self, plugin, event_name, event, **kwargs):
        """Выполняет обработку события плагином."""
        pass

    @abstractmethod
    def start(self, plugin):
        """Запускает исполнителя для плагина (если нужно)."""
        pass

    @abstractmethod
    def stop(self, plugin):
        """Останавливает исполнителя для плагина."""
        pass
