from typing import Dict, List, Set, Optional
from dataclasses import dataclass

@dataclass
class PluginDependency:
    name: str
    version: Optional[str] = None
    optional: bool = False

class DependencyResolver:
    def __init__(self):
        self.plugin_deps: Dict[str, List[PluginDependency]] = {}
        self.plugin_versions: Dict[str, str] = {}
    
    def register_plugin(self, name: str, version: str, dependencies: List[Dict]):
        '''Зарегистрировать плагин с зависимостями'''
        self.plugin_versions[name] = version
        self.plugin_deps[name] = [
            PluginDependency(
                name=dep.get('name'),
                version=dep.get('version'),
                optional=dep.get('optional', False)
            )
            for dep in dependencies
        ]
    
    def get_dependencies(self, plugin_name: str) -> List[str]:
        '''Получить все зависимости плагина'''
        if plugin_name not in self.plugin_deps:
            return []
        
        return [dep.name for dep in self.plugin_deps[plugin_name]]
    
    def get_dependents(self, plugin_name: str) -> List[str]:
        '''Получить все плагины, зависящие от данного'''
        dependents = []
        for name, deps in self.plugin_deps.items():
            if any(dep.name == plugin_name for dep in deps):
                dependents.append(name)
        return dependents
    
    def can_disable(self, plugin_name: str, enabled_plugins: Set[str]) -> tuple:
        '''Проверить, можно ли отключить плагин'''
        dependents = self.get_dependents(plugin_name)
        active_dependents = [d for d in dependents if d in enabled_plugins]
        
        if active_dependents:
            return False, f"Cannot disable: required by {', '.join(active_dependents)}"
        
        return True, "OK"
    
    def can_enable(self, plugin_name: str, enabled_plugins: Set[str]) -> tuple:
        '''Проверить, можно ли включить плагин'''
        if plugin_name not in self.plugin_deps:
            return True, "OK"
        
        missing_deps = []
        for dep in self.plugin_deps[plugin_name]:
            if not dep.optional and dep.name not in enabled_plugins:
                missing_deps.append(dep.name)
        
        if missing_deps:
            return False, f"Missing dependencies: {', '.join(missing_deps)}"
        
        return True, "OK"
    
    def get_dependency_graph(self) -> Dict[str, List[str]]:
        '''Получить граф зависимостей'''
        return {
            name: [dep.name for dep in deps]
            for name, deps in self.plugin_deps.items()
        }
    
    def get_load_order(self) -> List[str]:
        '''Получить порядок загрузки плагинов'''
        visited = set()
        order = []
        
        def visit(name: str):
            if name in visited:
                return
            visited.add(name)
            
            if name in self.plugin_deps:
                for dep in self.plugin_deps[name]:
                    if not dep.optional:
                        visit(dep.name)
            
            order.append(name)
        
        for plugin in self.plugin_deps.keys():
            visit(plugin)
        
        return order
