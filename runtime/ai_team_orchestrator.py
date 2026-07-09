import json
import os
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class LogMonitor:
    def __init__(self, log_paths: Optional[List[Path | str]] = None, patterns: Optional[List[str]] = None):
        self.log_paths = [Path(p) for p in (log_paths or [Path("logs"), Path("autopilot/logs")])]
        self.patterns = patterns or [r"ERROR.*", r"CRITICAL.*", r"Traceback.*", r"Exception.*", r"FAIL.*"]

    def collect_errors(self) -> List[Dict[str, Any]]:
        issues: List[Dict[str, Any]] = []
        for root in self.log_paths:
            if root.is_dir():
                for path in root.rglob("*.log"):
                    issues.extend(self._scan_file(path))
            elif root.exists():
                issues.extend(self._scan_file(root))
        return issues

    def _scan_file(self, path: Path) -> List[Dict[str, Any]]:
        issues: List[Dict[str, Any]] = []
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as handle:
                for line_no, line in enumerate(handle, 1):
                    lowered = line.upper()
                    if any(re.search(pattern, lowered) for pattern in self.patterns):
                        issues.append({
                            "path": str(path),
                            "line": line_no,
                            "message": line.strip(),
                            "severity": "critical" if "CRITICAL" in lowered or "TRACEBACK" in lowered else "high",
                        })
        except Exception:
            pass
        return issues


class TaskManager:
    def __init__(self, bot: Any, tasks_file: Optional[Path | str] = None):
        self.bot = bot
        self.tasks_file = Path(tasks_file or Path("tasks") / "ai_tasks.json")
        self.tasks_file.parent.mkdir(parents=True, exist_ok=True)

    def _load_tasks(self) -> List[Dict[str, Any]]:
        if not self.tasks_file.exists():
            return []
        try:
            with open(self.tasks_file, "r", encoding="utf-8") as handle:
                data = json.load(handle)
                if isinstance(data, list):
                    return data
        except Exception:
            pass
        return []

    def _save_tasks(self, tasks: List[Dict[str, Any]]) -> None:
        with open(self.tasks_file, "w", encoding="utf-8") as handle:
            json.dump(tasks, handle, indent=2, ensure_ascii=False)

    def create_task(self, error_data: Dict[str, Any], priority: str = "high") -> Dict[str, Any]:
        task = {
            "id": f"task_{int(datetime.now().timestamp())}",
            "created_at": datetime.now().isoformat(),
            "priority": priority,
            "status": "open",
            "assigned_to": "ai-developer",
            "error": error_data,
            "context": self._get_context(),
            "solution": None,
            "tested": False,
        }
        tasks = self._load_tasks()
        tasks.append(task)
        self._save_tasks(tasks)
        if hasattr(self.bot, "_send_telegram_message"):
            self.bot._send_telegram_message(f"🛠️ New AI task queued: {task['id']} -> {error_data.get('message', 'unknown')}")
        return task

    def _get_context(self) -> str:
        return "Automatic AI team inspection"


class AITeamOrchestrator:
    def __init__(self, bot: Optional[Any] = None, log_monitor: Optional[LogMonitor] = None, task_manager: Optional[TaskManager] = None):
        self.bot = bot
        self.log_monitor = log_monitor or LogMonitor()
        self.task_manager = task_manager or TaskManager(self.bot or object())

    def run_once(self) -> Dict[str, Any]:
        issues = self.log_monitor.collect_errors()
        tasks_created = 0
        for issue in issues:
            task = self.task_manager.create_task(issue)
            if self._apply_safe_fix(task):
                task["status"] = "completed"
                task["tested"] = True
            else:
                task["status"] = "failed"
            tasks_created += 1
        return {"status": "completed", "tasks_created": tasks_created, "issues_found": len(issues)}

    def _apply_safe_fix(self, task: Dict[str, Any]) -> bool:
        message = task.get("error", {}).get("message", "")
        lowered = message.lower()
        if "modulenotfounderror" in lowered and "discord" in lowered:
            requirements_path = Path("requirements.txt")
            try:
                existing = requirements_path.read_text(encoding="utf-8") if requirements_path.exists() else ""
                if "discord.py" not in existing:
                    with open(requirements_path, "a", encoding="utf-8") as handle:
                        handle.write("\ndiscord.py>=2.4.0\n")
                return True
            except Exception:
                return False
        return False
