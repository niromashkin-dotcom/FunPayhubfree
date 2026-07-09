# runtime/migrations/migration_manager.py
from typing import Any, Dict, List, Tuple
from runtime.migrations.migration_registry import get_registry


class MigrationPathNotFoundError(Exception):
    pass


class MigrationManager:
    def __init__(self):
        self.registry = get_registry()
        self.current_export_version = 1
        self.current_snapshot_version = 1
        self.current_backup_version = 1

    def _migrate_chain(
        self, data: Dict[str, Any], from_version: int, to_version: int,
        get_migration_func, version_name: str
    ) -> Tuple[Dict[str, Any], List[str]]:
        if from_version == to_version:
            return data, []
        if from_version > to_version:
            raise MigrationPathNotFoundError(
                f"Downgrade not supported: {version_name} v{from_version} -> v{to_version}"
            )
        steps = []
        current = from_version
        current_data = data
        while current < to_version:
            migration = get_migration_func(current)
            if not migration:
                raise MigrationPathNotFoundError(
                    f"Missing migration for {version_name} v{current} -> v{current+1}"
                )
            current_data = migration.apply(current_data)
            steps.append(f"v{current}_to_v{current+1}")
            current += 1
        return current_data, steps

    def migrate_export(self, data: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
        from_version = data.get("format_version", 0)
        if from_version == 0:
            from_version = 1
        to_version = self.current_export_version
        return self._migrate_chain(
            data, from_version, to_version,
            self.registry.get_export_migration, "export"
        )

    def migrate_snapshot(self, data: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
        from_version = data.get("version", 0)
        to_version = self.current_snapshot_version
        return self._migrate_chain(
            data, from_version, to_version,
            self.registry.get_snapshot_migration, "snapshot"
        )

    def migrate_backup(self, data: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
        from_version = data.get("backup_version", 0)
        to_version = self.current_backup_version
        return self._migrate_chain(
            data, from_version, to_version,
            self.registry.get_backup_migration, "backup"
        )

    def get_current_versions(self) -> Dict[str, int]:
        return {
            "export_version": self.current_export_version,
            "snapshot_version": self.current_snapshot_version,
            "backup_version": self.current_backup_version
        }
