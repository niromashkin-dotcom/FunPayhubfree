# runtime/migrations/registry.py
from typing import Dict, List, Optional
from runtime.migrations.base import BaseMigration

class MigrationRegistry:
    def __init__(self):
        self._export_migrations: Dict[int, BaseMigration] = {}
        self._snapshot_migrations: Dict[int, BaseMigration] = {}
        self._backup_migrations: Dict[int, BaseMigration] = {}

    def register_export(self, migration: BaseMigration):
        self._export_migrations[migration.from_version] = migration

    def register_snapshot(self, migration: BaseMigration):
        self._snapshot_migrations[migration.from_version] = migration

    def register_backup(self, migration: BaseMigration):
        self._backup_migrations[migration.from_version] = migration

    def get_export_migration(self, from_version: int) -> Optional[BaseMigration]:
        return self._export_migrations.get(from_version)

    def get_snapshot_migration(self, from_version: int) -> Optional[BaseMigration]:
        return self._snapshot_migrations.get(from_version)

    def get_backup_migration(self, from_version: int) -> Optional[BaseMigration]:
        return self._backup_migrations.get(from_version)

    def get_export_versions(self) -> List[int]:
        return sorted(self._export_migrations.keys())

    def get_snapshot_versions(self) -> List[int]:
        return sorted(self._snapshot_migrations.keys())

    def get_backup_versions(self) -> List[int]:
        return sorted(self._backup_migrations.keys())

_registry = MigrationRegistry()

def get_registry() -> MigrationRegistry:
    return _registry
