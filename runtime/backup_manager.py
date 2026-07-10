"""
Backup Manager — бэкап и восстановление (Этап K).

- Ежедневный backup SQLite
- Backup конфигов и состояния
- Restore System из Telegram
"""

import os
import time
import shutil
import threading
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

logger = logging.getLogger("FunPayHUB.Backup")


class BackupManager:
    def __init__(self, db_path: str = "", configs_dir: str = "",
                 backup_dir: str = "", admin_chat_id: str = ""):
        root = Path(__file__).resolve().parent.parent
        self._db_path = Path(db_path) if db_path else root / "data" / "funpayhub.db"
        self._configs_dir = Path(configs_dir) if configs_dir else root / "configs"
        self._backup_dir = Path(backup_dir) if backup_dir else root / "backups"
        self._admin_chat_id = admin_chat_id
        self._backup_dir.mkdir(parents=True, exist_ok=True)
        self._worker = None
        self._stop = threading.Event()
        # Храним последний бэкап для restore
        self._last_backup_path: Optional[Path] = None

    def start(self):
        self._start_daily_backup()
        logger.info(f"[Backup] Manager started → {self._backup_dir}")

    def stop(self):
        self._stop.set()
        if self._worker and self._worker.is_alive():
            self._worker.join(timeout=5)

    # ── Backup ─────────────────────────────────────────────────────

    def backup_now(self) -> Optional[Path]:
        """Создать backup прямо сейчас."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Backup DB
        if self._db_path.exists():
            db_backup = self._backup_dir / f"funpayhub_{timestamp}.db"
            try:
                shutil.copy2(self._db_path, db_backup)
                self._last_backup_path = db_backup
                logger.info(f"[Backup] DB backed up → {db_backup}")
            except Exception as e:
                logger.error(f"[Backup] DB backup failed: {e}")

        # Backup configs
        cfg_backup = self._backup_dir / f"configs_{timestamp}"
        if self._configs_dir.exists():
            try:
                shutil.copytree(self._configs_dir, cfg_backup,
                                ignore=shutil.ignore_patterns("__pycache__"))
                logger.info(f"[Backup] Configs backed up → {cfg_backup}")
            except Exception as e:
                logger.error(f"[Backup] Configs backup failed: {e}")

        return self._last_backup_path

    def restore(self, backup_path: Optional[str] = None) -> bool:
        """Восстановить из backup."""
        if not backup_path and not self._last_backup_path:
            logger.error("[Restore] No backup to restore from")
            return False

        src = Path(backup_path) if backup_path else self._last_backup_path
        if not src or not src.exists():
            logger.error(f"[Restore] Backup not found: {src}")
            return False

        try:
            # Restore DB
            if src.suffix == ".db":
                if self._db_path.exists():
                    self._db_path.unlink()
                shutil.copy2(src, self._db_path)
                logger.info(f"[Restore] DB restored from {src}")
                return True
            else:
                logger.error(f"[Restore] Unknown backup type: {src}")
                return False
        except Exception as e:
            logger.error(f"[Restore] Failed: {e}")
            return False

    def list_backups(self) -> list:
        """Список доступных backup'ов."""
        if not self._backup_dir.exists():
            return []
        return sorted(
            [str(f) for f in self._backup_dir.iterdir() if f.suffix == ".db"],
            reverse=True,
        )[:10]

    # ── Планировщик ────────────────────────────────────────────────

    def _start_daily_backup(self):
        def _loop():
            last_date = ""
            while not self._stop.is_set():
                try:
                    today = datetime.now().strftime("%Y-%m-%d")
                    if today != last_date:
                        self.backup_now()
                        last_date = today
                except Exception as e:
                    logger.error(f"[Backup] Scheduler error: {e}")
                time.sleep(3600)  # проверка раз в час
        self._worker = threading.Thread(target=_loop, name="Backup", daemon=True)
        self._worker.start()
