import shutil
import tempfile
from pathlib import Path
from datetime import datetime
from typing import List, Tuple
from .task_package import TaskPackage
from .patch_validator import PatchValidator

class PatchExecutor:
    def __init__(self, project_root: Path, backups_dir: Path):
        self.project_root = project_root
        self.backups_dir = backups_dir
        self.validator = PatchValidator(project_root)

    def apply(self, pkg: TaskPackage, dry_run: bool = False) -> Tuple[bool, List[str], List[str]]:
        errors = self.validator.validate_files(pkg)
        if errors:
            return False, [], [f"Validation error: {path} - {msg}" for path, msg in errors]

        ok, msg = self.validator.syntax_check(pkg)
        if not ok:
            return False, [], [f"Syntax error: {msg}"]

        if dry_run:
            return True, [fc.path for fc in pkg.files], []

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir) / "project"
            for fc in pkg.files:
                dest = tmp_root / fc.path
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(fc.content, encoding='utf-8')
            ok, msg = self.validator.syntax_check(pkg)
            if not ok:
                return False, [], [f"Transaction syntax error: {msg}"]

            self.backups_dir.mkdir(exist_ok=True)
            updated = []
            for fc in pkg.files:
                real_path = self.project_root / fc.path
                if real_path.exists():
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    backup_name = f"{fc.path.replace('/', '_')}_{timestamp}.bak"
                    backup_path = self.backups_dir / backup_name
                    shutil.copy2(real_path, backup_path)
                real_path.parent.mkdir(parents=True, exist_ok=True)
                real_path.write_text(fc.content, encoding='utf-8')
                updated.append(fc.path)
        return True, updated, []
