# runtime/migrations/export_migrations.py
from typing import Any, Dict
from runtime.migrations.migration_base import BaseMigration
from runtime.migrations.migration_registry import get_registry

# class ExportV1ToV2(BaseMigration):
#     from_version = 1
#     to_version = 2
#     def apply(self, data: Dict[str, Any]) -> Dict[str, Any]:
#         data["format_version"] = 2
#         return data

# registry = get_registry()
# registry.register_export(ExportV1ToV2())
