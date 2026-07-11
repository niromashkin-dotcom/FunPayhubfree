"""Тесты для AI Team интеграции."""
import json
import pytest
from unittest.mock import patch

from runtime.ai_team.model_manager import AIModelManager
from runtime.ai_team.scheduled_tasks import ScheduledTasks
from runtime.ai_team.ai_team_orchestrator import AITeamOrchestrator


@pytest.fixture(autouse=True)
def _mock_secrets_and_http(monkeypatch):
    """Автоматически мокаем SecretsManager и HTTPClient для всех тестов."""

    def mock_get_secret(self, name, default=""):
        if name == "GROQ_API_KEY":
            return "fake-groq-key"
        return default

    monkeypatch.setattr(
        "security.secrets_manager.SecretsManager.get_secret",
        mock_get_secret,
        raising=False,
    )

    def fake_post(self, url, **kwargs):
        return {"choices": [{"message": {"content": "Hello from Groq"}}]}

    monkeypatch.setattr("runtime.ai_team.model_manager.HTTPClient.post", fake_post)


def test_model_manager_initialization():
    manager = AIModelManager(config_path="configs/ai_team_config.json")
    assert manager.config is not None
    assert "models" in manager.config


def test_model_manager_query_uses_primary_model():
    manager = AIModelManager(config_path="configs/ai_team_config.json")
    response = manager.query("Say hello", max_retries=1)
    assert response == "Hello from Groq"


def test_scheduled_tasks_market_analysis():
    manager = AIModelManager(config_path="configs/ai_team_config.json")
    tasks = ScheduledTasks(manager)
    result = tasks.market_analysis()
    assert "analysis" in result
    assert "timestamp" in result


def test_scheduled_tasks_daily_report():
    manager = AIModelManager(config_path="configs/ai_team_config.json")
    tasks = ScheduledTasks(manager)
    result = tasks.generate_daily_report(tasks_completed=10, errors_fixed=5)
    assert "report" in result
    assert "timestamp" in result


def test_orchestrator_analyzes_errors_with_ai(monkeypatch):
    def fake_post_json(self, url, **kwargs):
        return {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "severity": "high",
                                "solution": "check imports",
                                "auto_fix": True,
                            }
                        )
                    }
                }
            ]
        }

    monkeypatch.setattr(
        "runtime.ai_team.model_manager.HTTPClient.post", fake_post_json
    )
    orchestrator = AITeamOrchestrator()
    result = orchestrator.analyze_error("ModuleNotFoundError: No module named 'requests'")
    assert result["severity"] == "high"
    assert result["solution"] == "check imports"
