"""
FunPay catalog parser v2 — под реальную структуру https://funpay.com/
Один HTTP-запрос → весь каталог subcategory.
Кэш: data/funpay/subcategories_cache.json (TTL по умолчанию 24h).

Структура HTML FunPay:
<div class="promo-game-item">
  <div class="game-title" data-id="224">
    <a href="https://funpay.com/lots/702/">Telegram</a>
  </div>
  <ul class="list-inline" data-id="224">
    <li><a href="https://funpay.com/lots/702/">Каналы</a></li>
    <li><a href="https://funpay.com/chips/55/">...</a></li>
  </ul>
</div>
"""
from __future__ import annotations
import os, re, json, time
from typing import List, Dict, Optional

from runtime.http_client import HTTPClient, HTTPClientError

_http_client = HTTPClient(timeout=20, max_retries=3)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
FUNPAY_HOME = "https://funpay.com/"

_HERE = os.path.dirname(os.path.abspath(__file__))
_CACHE_DIR = os.path.normpath(os.path.join(_HERE, "..", "data", "funpay"))
_CACHE_FILE = os.path.join(_CACHE_DIR, "subcategories_cache.json")


def _ensure_dir():
    os.makedirs(_CACHE_DIR, exist_ok=True)


# Блок одной игры: <div class="promo-game-item"> ... </div>
# Используем lazy + lookahead на следующий promo-game-item ИЛИ закрытие
RE_GAME_BLOCK = re.compile(
    r'<div class="promo-game-item">(.*?)</div>\s*</div>',
    re.DOTALL
)

# Внутри блока: game-title с именем (последний <a> внутри)
RE_GAME_TITLE = re.compile(
    r'<div class="game-title"[^>]*>\s*<a[^>]*>([^<]+)</a>\s*</div>',
    re.DOTALL
)

# Все ссылки subcategory: <a href="https://funpay.com/(lots|chips)/N/">текст</a>
RE_SUB_LINK = re.compile(
    r'<a[^>]*href="https?://funpay\.com/(lots|chips)/(\d+)/"[^>]*>([^<]+)</a>',
    re.DOTALL
)


def fetch_all_subcategories(force: bool = False, ttl_hours: int = 24) -> Dict:
    """
    Возвращает: {
      fetched_at, total, games_count,
      games: [ {game_name, subcategories:[{id,type,url,name,game}]} ],
      flat:  [ {id,type,url,name,game} ]
    }
    """
    _ensure_dir()

    # cache
    if not force and os.path.exists(_CACHE_FILE):
        try:
            with open(_CACHE_FILE, encoding="utf-8") as f:
                cached = json.load(f)
            age_h = (time.time() - cached.get("fetched_at", 0)) / 3600.0
            if age_h < ttl_hours and cached.get("flat"):
                cached["from_cache"] = True
                cached["age_hours"] = round(age_h, 2)
                return cached
        except Exception:
            pass

    headers = {"User-Agent": UA, "Accept-Language": "ru-RU,ru;q=0.9"}
    html = _http_client.get(FUNPAY_HOME, headers=headers)

    games: List[Dict] = []
    flat: List[Dict] = []
    seen_ids = set()  # (id, type)

    blocks = RE_GAME_BLOCK.findall(html)
    for block in blocks:
        mt = RE_GAME_TITLE.search(block)
        if not mt:
            continue
        game_name = mt.group(1).strip()
        if not game_name:
            continue

        subs: List[Dict] = []
        for ml in RE_SUB_LINK.finditer(block):
            kind = ml.group(1)            # lots | chips
            sid = int(ml.group(2))
            sub_name = ml.group(3).strip()
            stype = 0 if kind == "lots" else 1

            # пропустить дубль "заголовочной" ссылки (она же и первая подкатегория)
            key = (sid, stype)
            if key in seen_ids:
                # уже взято в предыдущей игре — пропускаем
                continue
            seen_ids.add(key)

            item = {
                "id": sid,
                "type": stype,
                "url": f"/{kind}/{sid}/",
                "name": sub_name,
                "game": game_name,
            }
            subs.append(item)
            flat.append(item)

        if subs:
            games.append({"game_name": game_name, "subcategories": subs})

    result = {
        "fetched_at": int(time.time()),
        "total": len(flat),
        "games_count": len(games),
        "games": games,
        "flat": flat,
        "from_cache": False,
    }

    try:
        with open(_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    except Exception as e:
        result["save_error"] = str(e)

    return result


def get_cached() -> Optional[Dict]:
    if not os.path.exists(_CACHE_FILE):
        return None
    try:
        with open(_CACHE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


if __name__ == "__main__":
    print("Fetching FunPay catalog v2...")
    r = fetch_all_subcategories(force=True)
    print(f"from_cache: {r.get('from_cache')}")
    print(f"total subcategories: {r.get('total')}")
    print(f"games_count: {r.get('games_count')}")
    print()

    # Покажем популярные SMM-вертикали (то что нам нужно для AutoSMM)
    smm_keywords = ["telegram", "vk", "вконтакт", "instagram", "youtube",
                    "tiktok", "twitter", "discord", "twitch", "rutube",
                    "linkedin", "facebook", "spotify", "soundcloud", "threads"]
    print("=== SMM-вертикали (релевантные для AutoSMM) ===")
    for g in r.get("games", []):
        gname = g["game_name"].lower()
        if any(kw in gname for kw in smm_keywords):
            print(f"\n  [{g['game_name']}] — {len(g['subcategories'])} sub:")
            for s in g["subcategories"][:10]:
                print(f"    id={s['id']:5d} type={s['type']} {s['url']:18s} -> {s['name']}")

    # Telegram отдельно — подтверждение
    print("\n=== Telegram (контрольная проверка) ===")
    for g in r.get("games", []):
        if g["game_name"] == "Telegram":
            for s in g["subcategories"]:
                print(f"  id={s['id']:5d} type={s['type']} {s['url']:18s} -> {s['name']}")
            break

    print(f"\n=== Сохранено в кэш: data/funpay/subcategories_cache.json ===")