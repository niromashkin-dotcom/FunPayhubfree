"""Тесты для проверки GOLDEN_KEY."""
import os


def test_golden_key_exists():
    """Проверка что GOLDEN_KEY установлен в окружении."""
    golden_key = os.getenv("GOLDEN_KEY")
    assert golden_key is not None, "GOLDEN_KEY не установлен в .env"
    assert len(golden_key) > 0, "GOLDEN_KEY пуст"
    assert golden_key != "your_golden_key_here", "GOLDEN_KEY содержит значение по умолчанию"
