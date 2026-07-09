# runtime/migrations/migration_base.py
from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseMigration(ABC):
    @abstractmethod
    def apply(self, data: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @property
    @abstractmethod
    def from_version(self) -> int:
        pass

    @property
    @abstractmethod
    def to_version(self) -> int:
        pass
