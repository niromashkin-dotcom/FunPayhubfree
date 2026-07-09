from typing import Dict, Any

def migrate_snapshot(snapshot: Dict[str, Any], target_version: int) -> Dict[str, Any]:
    version = snapshot.get("version", 0)
    if version == target_version:
        return snapshot
    if version == 0:
        snapshot["version"] = 1
        snapshot["created_at"] = snapshot.get("timestamp", 0)
    return snapshot