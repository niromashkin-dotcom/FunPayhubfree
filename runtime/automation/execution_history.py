import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict

class ExecutionHistory:
    def __init__(self, history_file: Path):
        self.history_file = history_file
        self.history_file.parent.mkdir(parents=True, exist_ok=True)

    def log(self, task_id: str, success: bool, updated_files: List[str], errors: List[str]):
        entry = {
            "task_id": task_id,
            "timestamp": datetime.utcnow().isoformat(),
            "success": success,
            "updated_files": updated_files,
            "errors": errors
        }
        if self.history_file.exists():
            history = json.loads(self.history_file.read_text())
        else:
            history = []
        history.append(entry)
        self.history_file.write_text(json.dumps(history, indent=2))

    def get_last(self, n: int = 10) -> List[Dict]:
        if not self.history_file.exists():
            return []
        history = json.loads(self.history_file.read_text())
        return history[-n:]
