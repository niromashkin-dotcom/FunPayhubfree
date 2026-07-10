"""
Universal Plugin Marker System for FunPay Hub.

Лоты могут содержать маркер вида [XX#YYY] в названии или описании, где:
  XX  = короткий код плагина (AS, TU, AB...)
  YYY = ID услуги/предмета у внешнего провайдера

Примеры:
  "💥 Telegram Подписчики 1000 [AS#4947]"   → плагин AutoSMM, service 4947

Регистрируемые коды плагинов:
  AS  = AutoSMM (Twiboost)
  TU  = Direct Top-Up (будущий)
  AB  = AutoBump tag (просто метка)

Использование:
  from runtime.plugin_markers import parse_marker, has_any_marker

  parse_marker("Лот [AS#1234]")   → ("AS", "1234")
  has_any_marker("Лот [AS#1234]") → True
  has_any_marker("Простой лот")    → False
"""
import re
from typing import Optional, Tuple

# Регистрируем известные коды плагинов (для валидации)
KNOWN_PLUGIN_CODES = {
    "AS": "AutoSMM",
    "TU": "TopUp",
    "AB": "AutoBump",
    "GB": "GorgonaBoosts",
    "HB": "HoldBoost",
    "KS": "Kosell",
    "SC": "ShopClaude",
    "ST": "Stars",
}

# Регекс: [XX#YYY] где XX = 2-4 заглавные буквы, YYY = цифры или буквы
_MARKER_RE = re.compile(r'\[([A-Z]{2,4})#([A-Za-z0-9_-]+)\]')


def parse_marker(text: str) -> Optional[Tuple[str, str]]:
    """
    Найти ПЕРВЫЙ маркер в тексте.
    Возвращает (plugin_code, service_id) или None.
    """
    if not text:
        return None
    m = _MARKER_RE.search(text)
    if not m:
        return None
    return (m.group(1), m.group(2))


def parse_all_markers(text: str):
    """Найти ВСЕ маркеры в тексте."""
    if not text:
        return []
    return [(m.group(1), m.group(2)) for m in _MARKER_RE.finditer(text)]


def has_any_marker(text: str) -> bool:
    """True если есть любой маркер плагина."""
    return parse_marker(text) is not None


def has_marker_for(text: str, plugin_code: str) -> Optional[str]:
    """
    Если в тексте есть маркер указанного плагина — вернуть его ID.
    Иначе None.
    """
    if not text or not plugin_code:
        return None
    for code, srv_id in parse_all_markers(text):
        if code.upper() == plugin_code.upper():
            return srv_id
    return None


def strip_markers(text: str) -> str:
    """Удалить все маркеры из текста (для чистого отображения)."""
    if not text:
        return text
    return _MARKER_RE.sub("", text).strip()


def make_marker(plugin_code: str, service_id) -> str:
    """Сформировать маркер для встраивания в название лота."""
    return f"[{plugin_code.upper()}#{service_id}]"