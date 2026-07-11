"""Общие фикстуры для тестов FunPayHub."""
import os
import pytest
from dotenv import load_dotenv

# Загружаем переменные окружения из .env (если есть)
load_dotenv()

# Убеждаемся что корень проекта в PYTHONPATH
_project_root = str(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _project_root not in os.sys.path:
    os.sys.path.insert(0, _project_root)
