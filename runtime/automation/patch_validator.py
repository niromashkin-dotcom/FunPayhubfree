import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Tuple
from .task_package import TaskPackage

class PatchValidator:
    def __init__(self, project_root: Path):
        self.project_root = project_root

    def validate_files(self, pkg: TaskPackage) -> List[Tuple[str, str]]:
        errors = []
        for fc in pkg.files:
            full_path = self.project_root / fc.path
            try:
                full_path.resolve().relative_to(self.project_root.resolve())
            except ValueError:
                errors.append((fc.path, "Path outside project root"))
            if any(x in fc.path for x in ["__pycache__", ".git", "backups", "inbox"]):
                errors.append((fc.path, "Protected directory"))
        return errors

    def syntax_check(self, pkg: TaskPackage) -> Tuple[bool, str]:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            for fc in pkg.files:
                if fc.path.endswith('.py'):
                    dest = tmp_root / fc.path
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_text(fc.content, encoding='utf-8')
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "compileall", "-q", str(tmp_root)],
                    capture_output=True, text=True, timeout=30
                )
                if result.returncode != 0:
                    return False, result.stderr or result.stdout
                return True, "OK"
            except Exception as e:
                return False, str(e)
