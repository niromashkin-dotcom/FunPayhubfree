# plugins/execution/executor_registry.py
from typing import Dict, Type
from plugins.execution.base import PluginExecutor
from plugins.execution.inprocess_executor import InProcessExecutor
from plugins.execution.subprocess_executor import SubprocessExecutor

class ExecutorRegistry:
    def __init__(self):
        self._executors: Dict[str, PluginExecutor] = {}

    def register(self, name: str, executor: PluginExecutor):
        self._executors[name] = executor

    def get(self, name: str) -> PluginExecutor:
        return self._executors.get(name)

    def get_default(self) -> PluginExecutor:
        return self._executors.get("inprocess")

_registry = None

def get_executor_registry() -> ExecutorRegistry:
    global _registry
    if _registry is None:
        _registry = ExecutorRegistry()
        _registry.register("inprocess", InProcessExecutor())
        _registry.register("subprocess", SubprocessExecutor())
    return _registry
