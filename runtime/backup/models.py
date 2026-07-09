# runtime/backup/models.py
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime


@dataclass
class BackupMetadata:
    version: int = 1
    backup_id: str = ""          # уникальный ID
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    runtime_version: str = "0.1.0"
    checksum: str = ""           # sha256
    size_bytes: int = 0


@dataclass
class BackupInfo:
    backup_id: str
    created_at: str
    size_bytes: int
    path: str