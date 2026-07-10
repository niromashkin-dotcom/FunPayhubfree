import json
from pathlib import Path
from datetime import datetime

class ApprovalManager:
    def __init__(self, approval_dir: Path):
        self.approval_dir = approval_dir
        self.approval_dir.mkdir(exist_ok=True)

    def request_approval(self, task_id: str, package_path: Path) -> str:
        approval_file = self.approval_dir / f"{task_id}.json"
        data = {
            "task_id": task_id,
            "package_path": str(package_path),
            "requested_at": datetime.utcnow().isoformat(),
            "approved": False
        }
        approval_file.write_text(json.dumps(data, indent=2))
        return str(approval_file)

    def approve(self, task_id: str) -> bool:
        approval_file = self.approval_dir / f"{task_id}.json"
        if not approval_file.exists():
            return False
        data = json.loads(approval_file.read_text())
        data["approved"] = True
        data["approved_at"] = datetime.utcnow().isoformat()
        approval_file.write_text(json.dumps(data, indent=2))
        return True

    def is_approved(self, task_id: str) -> bool:
        approval_file = self.approval_dir / f"{task_id}.json"
        if not approval_file.exists():
            return False
        data = json.loads(approval_file.read_text())
        return data.get("approved", False)
