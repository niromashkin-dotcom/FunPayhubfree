"""
Менеджер AI-моделей с fallback-логикой

API-ключи читаются из переменных окружения:
  GROQ_API_KEY, GOOGLE_API_KEY, OPENROUTER_API_KEY
С запасным чтением из конфиг-файла (configs/ai_team_config.json).
"""
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from runtime.http_client import HTTPClient, HTTPClientError
from security.secrets_manager import SecretsManager

logger = logging.getLogger("ai_team.model_manager")

# Имена env-переменных для каждого провайдера
_ENV_KEYS = {
    "primary": "GROQ_API_KEY",
    "backup": "GOOGLE_API_KEY",
    "fallback": "OPENROUTER_API_KEY",
}


class AIModelManager:
    def __init__(self, config_path: str = "configs/ai_team_config.json"):
        self.config = self._load_config(config_path)
        self.models = self.config.get("models", {})
        self.http_client = HTTPClient()
        self.secrets = SecretsManager()

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Загружает конфигурацию из файла"""
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Ошибка загрузки конфига AI: {e}")
            return {"enabled": False, "models": {}}

    def _resolve_api_key(self, model_key: str) -> str:
        """
        Получить API-ключ для модели.
        Приоритет:
        1. Переменная окружения (например GROQ_API_KEY)
        2. Значение из config-файла
        3. Пустая строка
        """
        env_var = _ENV_KEYS.get(model_key)
        if env_var:
            secret_val = self.secrets.get_secret(env_var, "")
            if secret_val:
                return secret_val
        model_cfg = self.models.get(model_key, {})
        return model_cfg.get("api_key", "")

    def query(self, prompt: str, system_prompt: str = "", max_retries: int = 3) -> Optional[str]:
        """
        Отправляет запрос к AI с автоматическим fallback
        """
        if not self.config.get("enabled", False):
            logger.warning("AI-команда отключена в конфигурации")
            return None

        if "primary" in self.models:
            for attempt in range(max_retries):
                try:
                    response = self._query_groq(prompt, system_prompt)
                    if response:
                        return response
                except Exception as e:
                    logger.warning(f"Groq failed (attempt {attempt + 1}): {e}")
                    if attempt < max_retries - 1:
                        import time
                        time.sleep(2 ** attempt)

        if "backup" in self.models:
            try:
                response = self._query_google(prompt, system_prompt)
                if response:
                    return response
            except Exception as e:
                logger.warning(f"Google AI failed: {e}")

        if "fallback" in self.models:
            try:
                response = self._query_openrouter(prompt, system_prompt)
                if response:
                    return response
            except Exception as e:
                logger.warning(f"OpenRouter failed: {e}")

        logger.error("Все AI-модели недоступны")
        return None

    def _query_groq(self, prompt: str, system_prompt: str) -> Optional[str]:
        """Запрос к Groq API"""
        model_config = self.models["primary"]
        api_key = self._resolve_api_key("primary")
        if not api_key:
            logger.warning("Groq API ключ не настроен. Задайте GROQ_API_KEY в .env")
            return None
        url = "https://api.groq.com/openai/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        data = {
            "model": model_config["model"],
            "messages": messages,
            "max_tokens": model_config["max_tokens"],
            "temperature": model_config["temperature"]
        }

        result = self.http_client.post(url, headers=headers, json=data, timeout=model_config.get("timeout", 60))
        return result["choices"][0]["message"]["content"]

    def _query_google(self, prompt: str, system_prompt: str) -> Optional[str]:
        """Запрос к Google AI API"""
        model_config = self.models["backup"]
        api_key = self._resolve_api_key("backup")
        if not api_key:
            logger.warning("Google AI API ключ не настроен. Задайте GOOGLE_API_KEY в .env")
            return None
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_config['model']}:generateContent"

        params = {"key": api_key}
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt

        data = {
            "contents": [{"parts": [{"text": full_prompt}]}],
            "generationConfig": {
                "maxOutputTokens": model_config["max_tokens"],
                "temperature": model_config["temperature"]
            }
        }

        result = self.http_client.post(url, params=params, json=data, timeout=model_config.get("timeout", 60))
        return result["candidates"][0]["content"]["parts"][0]["text"]

    def _query_openrouter(self, prompt: str, system_prompt: str) -> Optional[str]:
        """Запрос к OpenRouter API"""
        model_config = self.models["fallback"]
        api_key = self._resolve_api_key("fallback")
        if not api_key:
            logger.warning("OpenRouter API ключ не настроен. Задайте OPENROUTER_API_KEY в .env")
            return None
        url = "https://openrouter.ai/api/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        data = {
            "model": model_config["model"],
            "messages": messages,
            "max_tokens": model_config["max_tokens"],
            "temperature": model_config["temperature"]
        }

        result = self.http_client.post(url, headers=headers, json=data, timeout=model_config.get("timeout", 60))
        return result["choices"][0]["message"]["content"]
