# plugins/dependency_manager.py
from typing import Dict, List, Set, Optional, Tuple
from collections import deque

class DependencyError(Exception):
    pass

class CircularDependencyError(DependencyError):
    pass

class MissingDependencyError(DependencyError):
    pass

class DependencyGraph:
    def __init__(self):
        self.graph: Dict[str, Set[str]] = {}          # plugin -> {hard dependencies}
        self.optional: Dict[str, Set[str]] = {}       # plugin -> {optional dependencies}
        self.hard_reverse: Dict[str, Set[str]] = {}   # plugin -> {plugins that hard-depend on it}
        self.soft_reverse: Dict[str, Set[str]] = {}   # plugin -> {plugins that soft-depend on it}

    def add_plugin(self, name: str, depends: List[str], optional_depends: List[str] = None):
        self.graph[name] = set(depends)
        self.optional[name] = set(optional_depends) if optional_depends else set()
        # hard reverse
        for dep in depends:
            if dep not in self.hard_reverse:
                self.hard_reverse[dep] = set()
            self.hard_reverse[dep].add(name)
        # soft reverse
        if optional_depends:
            for opt in optional_depends:
                if opt not in self.soft_reverse:
                    self.soft_reverse[opt] = set()
                self.soft_reverse[opt].add(name)

    def remove_plugin(self, name: str):
        if name in self.graph:
            for dep in self.graph[name]:
                if dep in self.hard_reverse:
                    self.hard_reverse[dep].discard(name)
            del self.graph[name]
        if name in self.optional:
            del self.optional[name]
        if name in self.hard_reverse:
            del self.hard_reverse[name]
        if name in self.soft_reverse:
            del self.soft_reverse[name]
        # удалить из reverse-словарей запись о том, что этот плагин зависит от других
        for deps in self.hard_reverse.values():
            deps.discard(name)
        for deps in self.soft_reverse.values():
            deps.discard(name)

    def validate_dependencies(self, available_plugins: Set[str]) -> None:
        """Проверяет, что все обязательные зависимости присутствуют."""
        missing = set()
        for plugin, deps in self.graph.items():
            missing.update(deps - available_plugins)
        if missing:
            raise MissingDependencyError(f"Missing dependencies: {missing}")

    def detect_circular(self) -> List[List[str]]:
        visited = set()
        stack = set()
        cycles = []

        def dfs(node, path):
            if node in stack:
                cycle_start = path.index(node)
                cycles.append(path[cycle_start:] + [node])
                return
            if node in visited:
                return
            visited.add(node)
            stack.add(node)
            for neighbor in self.graph.get(node, []):
                dfs(neighbor, path + [node])
            stack.remove(node)

        for node in self.graph:
            if node not in visited:
                dfs(node, [])
        return cycles

    def topological_sort(self) -> List[str]:
        cycles = self.detect_circular()
        if cycles:
            raise CircularDependencyError(f"Circular dependencies detected: {cycles}")
        in_degree = {node: len(self.graph[node]) for node in self.graph}
        queue = deque([node for node, deg in in_degree.items() if deg == 0])
        result = []
        while queue:
            node = queue.popleft()
            result.append(node)
            for dependent in self.hard_reverse.get(node, []):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)
        if len(result) != len(self.graph):
            raise CircularDependencyError("Circular dependency detected (incomplete sort)")
        return result

    def get_hard_dependents(self, plugin: str) -> Set[str]:
        return self.hard_reverse.get(plugin, set())

    def get_soft_dependents(self, plugin: str) -> Set[str]:
        return self.soft_reverse.get(plugin, set())

    def get_dependents(self, plugin: str) -> Tuple[Set[str], Set[str]]:
        return (self.get_hard_dependents(plugin), self.get_soft_dependents(plugin))

    def can_disable(self, plugin: str, active_plugins: Set[str]) -> Tuple[bool, List[str]]:
        blockers = []
        for depender in self.get_hard_dependents(plugin):
            if depender in active_plugins:
                blockers.append(depender)
        return len(blockers) == 0, blockers

    def get_plugin_info(self, plugin: str) -> dict:
        return {
            "hard_dependencies": list(self.graph.get(plugin, [])),
            "optional_dependencies": list(self.optional.get(plugin, [])),
            "hard_dependents": list(self.get_hard_dependents(plugin)),
            "soft_dependents": list(self.get_soft_dependents(plugin))
        }