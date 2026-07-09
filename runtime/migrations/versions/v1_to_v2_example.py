# runtime/migrations/versions/v1_to_v2_example.py
from typing import Any, Dict
from runtime.migrations.base import BaseMigration
from runtime.migrations.registry import get_registry

class ExportV1ToV2(BaseMigration):
    from_version = 1
    to_version = 2

    def apply(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if "format_version" not in data:
            data["format_version"] = 1
        data["format_version"] = 2
        return data

# registry = get_registry()
# registry.register_export(ExportV1ToV2())
