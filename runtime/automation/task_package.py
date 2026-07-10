import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime

@dataclass
class FileChange:
    path: str
    content: str
    action: str = "update"

@dataclass
class TaskPackage:
    task_id: str
    title: str
    description: str
    approved: bool = False
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    files: List[FileChange] = field(default_factory=list)
    tests_required: bool = True
    rollback_enabled: bool = True
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "title": self.title,
            "description": self.description,
            "approved": self.approved,
            "created_at": self.created_at,
            "files": [{"path": f.path, "content": f.content, "action": f.action} for f in self.files],
            "tests_required": self.tests_required,
            "rollback_enabled": self.rollback_enabled,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TaskPackage":
        files = [FileChange(**f) for f in data.get("files", [])]
        return cls(
            task_id=data["task_id"],
            title=data["title"],
            description=data["description"],
            approved=data.get("approved", False),
            created_at=data.get("created_at"),
            files=files,
            tests_required=data.get("tests_required", True),
            rollback_enabled=data.get("rollback_enabled", True),
            metadata=data.get("metadata", {})
        )

    def save(self, path: str):
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: str) -> "TaskPackage":
        with open(path, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)
