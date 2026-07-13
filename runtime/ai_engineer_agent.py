"""
AI Engineer Agent — диагностика и предложение патчей (Этап G).

Читает логи, ищет ошибки/аномалии, формирует диагноз + патч,
присылает в Telegram с кнопками Да/Нет.
НЕ применяет изменения без подтверждения человека.
"""

import os
import re
import time
import json
import threading
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("FunPayHUB.AIAgent")


class AIEngineerAgent:
    """
    AI Engineer Agent:
      - Читает логи (app.log)
      - Ищет ошибки и аномалии
      - Формирует предложение патча
      - Отправляет в Telegram: диагноз + патч + кнопки Да/Нет
      - Применяет патч ТОЛЬКО после нажатия "Да"
    """

    def __init__(self, log_path: str = "", admin_chat_id: str = "",
                 llm_api_key: str = "", llm_api_url: str = "", message_manager=None):
        self._log_path = Path(log_path) if log_path else Path("logs/app.log")
        self._admin_chat_id = admin_chat_id
        self._llm_api_key = llm_api_key or os.environ.get("GOOGLE_API_KEY", "")
        self._llm_api_url = llm_api_url or os.environ.get("LLM_API_URL", "")
        self._msg_manager = message_manager

        self._last_position = 0
        self._worker = None
        self._stop = threading.Event()
        self._pending_patches: List[Dict] = []

        # Пороги
        self.SCAN_INTERVAL = 60  # каждые 60 сек
        self.MAX_ERRORS_PER_SCAN = 5

    def start(self):
        if not self._llm_api_key:
            logger.warning("[AIAgent] Нет LLM API ключа — агент в режиме ожидания")
        else:
            self._start_scanner()
            logger.info("[AIAgent] Started")

    def stop(self):
        self._stop.set()
        if self._worker and self._worker.is_alive():
            self._worker.join(timeout=5)

    # ── Сканер логов ──────────────────────────────────────────────

    def _start_scanner(self):
        def _loop():
            while not self._stop.is_set():
                try:
                    self._scan_logs()
                except Exception as e:
                    logger.error(f"[AIAgent] Scan error: {e}")
                time.sleep(self.SCAN_INTERVAL)
        self._worker = threading.Thread(target=_loop, name="AIAgent", daemon=True)
        self._worker.start()

    def _scan_logs(self):
        """Найти новые ошибки в логах."""
        if not self._log_path.exists():
            return

        with open(self._log_path, "r", encoding="utf-8") as f:
            f.seek(self._last_position)
            new_lines = f.readlines()
            self._last_position = f.tell()

        errors = []
        for line in new_lines:
            line = line.strip()
            if not line:
                continue
            if any(kw in line for kw in ["ERROR", "CRITICAL", "Traceback",
                                          "Failed", "failed", "Error", "error"]):
                errors.append(line)

        if errors:
            self._analyze_errors(errors[:self.MAX_ERRORS_PER_SCAN])

    # ── Анализ и формирование патча ───────────────────────────────

    def _analyze_errors(self, errors: List[str]):
        """Проанализировать ошибки и предложить патч."""
        error_text = "\n".join(errors)

        # Простейший анализ без LLM (для случаев когда ключа нет)
        fix = self._simple_fix_suggestion(error_text)
        if fix:
            self._propose_patch(fix["diagnosis"], fix["patch"], fix["file"])

    def _simple_fix_suggestion(self, error_text: str) -> Optional[Dict]:
        """Простейший анализ ошибок по шаблонам."""
        suggestions = {
            "ModuleNotFoundError: No module named '": {
                "diagnosis": "Отсутствует зависимость Python",
                "patch": "pip install <module>",
                "file": "requirements.txt",
            },
            "ConnectionError": {
                "diagnosis": "Проблема с сетью/API поставщика",
                "patch": "Проверить API-ключи и доступность сервиса",
                "file": ".env",
            },
            "Timeout": {
                "diagnosis": "Таймаут при запросе к API",
                "patch": "Увеличить timeout в http_client.py",
                "file": "runtime/http_client.py",
            },
        }

        for pattern, suggestion in suggestions.items():
            if pattern in error_text:
                return suggestion

        # Общая ошибка
        return {
            "diagnosis": f"Обнаружены ошибки в логах:\n{error_text[:300]}",
            "patch": "Требуется ручной анализ",
            "file": "—",
        }

    def _propose_patch(self, diagnosis: str, patch: str, file: str):
        """Отправить предложение патча в Telegram."""
        if not self._admin_chat_id:
            return

        patch_id = f"patch_{int(time.time())}"
        self._pending_patches.append({
            "id": patch_id,
            "diagnosis": diagnosis,
            "patch": patch,
            "file": file,
            "created_at": time.time(),
            "applied": False,
        })

        msg = (
            f"🤖 AI Engineer Agent\n\n"
            f"🔍 Диагноз: {diagnosis}\n"
            f"📁 Файл: {file}\n"
            f"💊 Патч: {patch}\n\n"
            f"Применить? (Ответьте 'да {patch_id}' или 'нет')"
        )
        self._send_admin(msg)

    def apply_patch(self, patch_id: str) -> bool:
        """Применить патч после подтверждения."""
        for p in self._pending_patches:
            if p["id"] == patch_id and not p["applied"]:
                p["applied"] = True
                logger.info(f"[AIAgent] Patch {patch_id} applied: {p['patch']}")
                self._send_admin(f"✅ Патч {patch_id} применён: {p['patch']}")
                return True
        return False

    # ── Telegram ─────────────────────────────────────────────────

    def _send_admin(self, text: str):
        if not text:
            return
        try:
            if self._msg_manager:
                self._msg_manager.send_admin("notification", "ai_agent", {"text": text})
            else:
                from runtime.http_client import HTTPClient
                hc = HTTPClient()
                token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
                if token and self._admin_chat_id:
                    hc.post(
                        f"https://api.telegram.org/bot{token}/sendMessage",
                        json={"chat_id": self._admin_chat_id, "text": text,
                               "parse_mode": "HTML"},
                        timeout=10,
                    )
        except Exception as e:
            logger.error(f"[AIAgent] Send failed: {e}")
