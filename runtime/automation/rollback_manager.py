import shutil
from pathlib import Path
from typing import List

class RollbackManager:
    def __init__(self, backups_dir: Path):
        self.backups_dir = backups_dir

    def rollback(self, file_paths: List[str], original_state: dict = None) -> bool:
        success = True
        for path in file_paths:
            pattern = f"{path.replace('/', '_')}_*.bak"
            backups = sorted(self.backups_dir.glob(pattern), reverse=True)
            if backups:
                shutil.copy2(backups[0], Path(path))
                print(f"[Rollback] Restored {path}")
            else:
                # Нет бэкапа – значит, файл был создан операцией, удаляем его
                target = Path(path)
                if target.exists():
                    target.unlink()
                    print(f"[Rollback] Deleted created file {path}")
                else:
                    print(f"[Rollback] No backup and file not found: {path}")
                    success = False
        return success