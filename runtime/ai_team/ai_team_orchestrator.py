import json
import logging
import re
import threading
import time
from typing import Any, Dict, Optional

from runtime.ai_team.model_manager import AIModelManager

logger = logging.getLogger("ai_team.orchestrator")


class AITeamOrchestrator:
    def __init__(self, config_path: str = "configs/ai_team_config.json"):
        self.config = {"enabled": True, "schedule": {}}
        self.model_manager = AIModelManager(config_path=config_path)
        self.tasks_completed = 0
        self.errors_fixed = 0
        self._load_config(config_path)

    def _load_config(self, config_path: str) -> None:
        try:
            with open(config_path, "r", encoding="utf-8") as handle:
                loaded = json.load(handle)
                if isinstance(loaded, dict):
                    self.config.update(loaded)
        except Exception as e:
            logger.warning(f"AI team config load warning: {e}")

    def analyze_error(self, error_log: str) -> Dict[str, Any]:
        """Анализирует ошибку с помощью AI"""
        prompt = f"""Проанализируй следующую ошибку из логов Python-приложения и предложи решение:

{error_log}

Ответь в формате JSON:
{{
  "severity": "low|medium|high|critical",
  "solution": "описание решения",
  "auto_fix": true|false
}}"""

        system_prompt = "Ты эксперт по Python-разработке. Анализируй ошибки и предлагай решения."
        ai_response = self.model_manager.query(prompt, system_prompt)

        if ai_response:
            try:
                json_match = re.search(r'\{[^}]+\}', ai_response, re.DOTALL)
                if json_match:
                    parsed = json.loads(json_match.group())
                    if isinstance(parsed, dict):
                        parsed.setdefault("source", "ai")
                        return parsed
            except Exception as e:
                logger.warning(f"Ошибка парсинга AI-ответа: {e}")

        return {"severity": "medium", "solution": "Требуется ручной анализ", "auto_fix": False, "source": "fallback"}

    def run_24_7(self) -> None:
        while True:
            time.sleep(self.config.get("schedule", {}).get("log_monitor_interval", 300))
            self.tasks_completed += 1
