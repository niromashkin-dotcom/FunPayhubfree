"""
Lot Generator for FunPay Hub
Generates lot variations for AutoSMM and Donate plugins.
"""
import os
import json
import random
import itertools
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
logger = logging.getLogger(__name__)


class LotGenerator:
    def __init__(self, seller_service=None):
        self._seller_service = seller_service
        self._services_cache = None
        self._cache_path = Path("data/autosmm/twiboost_services_cache.json")
        self._return_policy = self._load_return_policy()
        self._synonyms = self._load_synonyms()
        self._emojis = self._load_emojis()

    # ── Динамическое масштабирование ───────────────────────────────
    # Новая услуга: 3 лота. После 20 продаж: +5 (8). После 100: 15.
    SCALE_THRESHOLDS = [
        (0,   3),    # 0 продаж → 3 копии
        (20,  8),    # 20+ продаж → 8 копий
        (100, 15),   # 100+ продаж → 15 копий
    ]

    def _calculate_copies(self, service_tag: Optional[str] = None) -> int:
        """Определяем сколько копий лота создавать по числу продаж."""
        try:
            sales = 0
            if service_tag:
                from runtime.database.base import get_session
                from runtime.database.models import Order
                session = get_session()
                try:
                    sales = session.query(Order).filter(
                        Order.service_tag == service_tag,
                        Order.status.in_(["completed", "in_progress"]),
                        Order.source == "real",
                    ).count()
                finally:
                    session.close()
            for threshold, copies in reversed(self.SCALE_THRESHOLDS):
                if sales >= threshold:
                    return copies
            return 3
        except Exception:
            return 3  # безопасный дефолт

    def _calculate_market_price(self, cost: float, quantity: int = 0,
                                 service_name: str = "") -> float:
        """Определяем цену с учётом рынка.
        Если данных нет — fallback на ×1.3.
        """
        try:
            if self._seller_service and service_name:
                # Пытаемся найти похожие лоты на FunPay и взять мин. цену
                lots = self._seller_service.search_lots(service_name)
                if lots and isinstance(lots, list) and len(lots) > 1:
                    prices = []
                    for l in lots[:10]:
                        p = l.get("price") if isinstance(l, dict) else getattr(l, "price", None)
                        if p and float(p) > 0:
                            prices.append(float(p))
                    if len(prices) >= 3:
                        min_price = min(prices)
                        avg_price = sum(prices) / len(prices)
                        # Ставим чуть ниже средней, но не ниже себестоимости + комиссия
                        base_cost = cost
                        commission = base_cost * 0.1  # ~10% комиссия FunPay
                        min_safe = base_cost + commission
                        suggested = round(avg_price * 0.95, 2)
                        return max(suggested, min_safe)
            return round(cost * 1.3, 2)
        except Exception:
            return round(cost * 1.3, 2)

    def _load_return_policy(self) -> str:
        policy_path = Path("configs/plugins/templates/return_policy.txt")
        if policy_path.exists():
            try:
                return policy_path.read_text(encoding="utf-8").strip()
            except Exception:
                pass
        return "Возврат в течение 24 часов при проблемах с услугой."

    def _load_synonyms(self) -> dict:
        path = Path("data/synonyms.json")
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data.get("synonyms", {}) if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _load_emojis(self) -> dict:
        path = Path("data/lot_emojis.json")
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _load_twiboost_services(self) -> List[Dict[str, Any]]:
        if self._services_cache is not None:
            return self._services_cache
        if not self._cache_path.exists():
            return []
        try:
            data = json.loads(self._cache_path.read_text(encoding="utf-8"))
            self._services_cache = data.get("services", []) if isinstance(data, dict) else []
            return self._services_cache
        except Exception:
            return []

    def _load_kosell_products(self) -> List[Dict[str, Any]]:
        """Загрузить товары Kosell для генерации лотов.

        Источник товаров Kosell не привязан к статическому кэшу (поставщик
        Kosell отсутствует в SupplierRegistry). Возвращаем пустой список —
        секция donate_kosell будет пустой, генерация остальных разделов
        (AutoSMM, Discord-boost, Stars) не нарушается.
        """
        return []

    def _categorize_service(self, service: Dict[str, Any]) -> tuple[str, str]:
        name = (service.get("name") or "").lower()
        category = (service.get("category") or "").lower()
        text = name + " " + category
        platform = "other"
        for key in ["telegram", "vk", "vkontakte", "instagram", "tiktok", "youtube", "twitch", "twitter", "x.com", "kick", "max", "rutube", "discord"]:
            if key in text:
                platform = key
                break
        stype = "other"
        for key in ["подписчик", "follower", "subscriber", "member", "просмотр", "view", "лайк", "like", "реакция", "reaction", "коммент", "comment", "репост", "share", "premium", "звёзд", "stars", "клик", "click", "буст", "boost"]:
            if key in text:
                stype = key
                break
        return platform, stype

    def _mutate_title(self, title: str, emoji_cycle: str) -> str:
        words = title.split()
        if not words:
            return title
        if words[0] in self._emojis.get("emojis_start", []):
            words[0] = emoji_cycle
        elif len(words) > 1 and random.random() < 0.3:
            words[0], words[1] = words[1], words[0]
        syn_map = self._synonyms.get("synonyms", {})
        for i, w in enumerate(words):
            low = w.lower()
            for key, vals in syn_map.items():
                if low == key and vals:
                    words[i] = random.choice(vals)
                    break
        return " ".join(words)

    def generate_lots_for_service(self, service_id: int, base_title: str, quantity: int = 1000, copies: Optional[int] = None, max_price: float = 150.0, marker: str = "[AS#") -> List[Dict[str, Any]]:
        service = None
        for s in self._load_twiboost_services():
            if str(s.get("service_id")) == str(service_id):
                service = s
                break
        if not service:
            return []

        # Динамическое число копий
        tag = f"{marker}{service_id}]"
        if copies is None:
            copies = self._calculate_copies(tag)

        platform, stype = self._categorize_service(service)
        svc_name = service.get("name", base_title)
        rate = float(service.get("rate") or 0)
        cost = rate * quantity / 1000 if rate else 40.0
        # Рыночная цена вместо фиксированной ×1.3
        final_price = self._calculate_market_price(cost, quantity, svc_name)
        if final_price > max_price:
            return []

        platform_names = {
            "telegram": ["Telegram", "TG", "ТЕЛЕГРАМ"],
            "vk": ["ВК", "VK", "ВКонтакте"],
            "instagram": ["Instagram", "INSTAGRAM", "Инста"],
            "tiktok": ["TikTok", "TIKTOK", "ТикТок"],
            "youtube": ["YouTube", "YOUTUBE", "Ютуб"],
            "twitch": ["Twitch", "TWITCH", "Твич"],
            "twitter": ["Twitter", "X", "Твиттер"],
            "discord": ["Discord", "DISCORD"],
        }
        type_names = {
            "подписчик": ["Подписчиков", "ПОДПИСЧИКОВ", "подписчики", "followers"],
            "просмотр": ["Просмотров", "ПРОСМОТРОВ", "просмотры", "views"],
            "лайк": ["Лайков", "ЛАЙКОВ", "лайки", "likes"],
            "реакция": ["Реакций", "РЕАКЦИЙ", "reactions"],
            "коммент": ["Комментариев", "КОММЕНТАРИЕВ", "comments"],
            "репост": ["Репостов", "РЕПОСТОВ", "shares"],
            "premium": ["Premium", "PREMIUM"],
            "звёзд": ["Звёзд", "ЗВЁЗД", "stars"],
            "буст": ["Бустов", "БУСТОВ", "boosts"],
        }
        plats = platform_names.get(platform, [platform.capitalize()])
        types = type_names.get(stype, [stype.capitalize()])
        emojis_start = self._emojis.get("emojis_start", ["🔥", "⭐", "🚀", "💎", "✅", "💫", "✨", "🎯", "⚡", "💥"])
        tails = self._emojis.get("emojis_tail", ["БЫСТРО", "моментально", "ГАРАНТИЯ", "живые", "без списаний", "стабильно", "топ", "PRO", "новинка"])
        templates = self._synonyms.get("title_templates", [
            "{emoji} {quantity} {type} {platform} {tail}",
            "{emoji} {platform} | {quantity} {type} | {tail}",
            "{emoji} {type} {platform} {quantity} штук {tail}",
            "{platform} {quantity} {type} {emoji} {tail}",
        ])

        def make_donor():
            e1 = random.choice(emojis_start)
            plat = random.choice(plats)
            typ = random.choice(types)
            tail = random.choice(tails) if random.random() < 0.5 else ""
            tmpl = random.choice(templates)
            title = tmpl.format(emoji=e1, quantity=quantity, type=typ, platform=plat, tail=tail, marker=marker, service_id=service_id)
            return " ".join(title.split()), e1

        lots = []
        donor_title, first_emoji = make_donor()
        lots.append({
            "title": donor_title,
            "description": self._make_descr(quantity, types[0] if types else stype, plats[0] if plats else platform),
            "price_rub": final_price,
            "amount": 1,
            "marker": f"{marker}{service_id}]",
            "service_id": service_id,
            "service_name": svc_name,
            "quantity": quantity,
            "platform": platform,
            "type": stype,
            "is_donor": True,
        })

        emoji_cycle = itertools.cycle(emojis_start)
        seen = {donor_title}
        attempts = 0
        while len(lots) < copies and attempts < copies * 20:
            attempts += 1
            next(emoji_cycle)
            e1 = next(emoji_cycle)
            plat = random.choice(plats)
            typ = random.choice(types)
            tail = random.choice(tails) if random.random() < 0.5 else ""
            tmpl = random.choice(templates)
            raw = tmpl.format(emoji=e1, quantity=quantity, type=typ, platform=plat, tail=tail, marker=marker, service_id=service_id)
            title = self._mutate_title(" ".join(raw.split()), e1)
            if title in seen:
                continue
            seen.add(title)
            lots.append({
                "title": title,
                "description": self._make_descr(quantity, typ, plat),
                "price_rub": final_price + random.choice([-1, 0, 0, 0, 1]),
                "amount": 1,
                "marker": f"{marker}{service_id}]",
                "service_id": service_id,
                "service_name": svc_name,
                "quantity": quantity,
                "platform": platform,
                "type": stype,
                "is_donor": False,
            })
        return lots

    def _make_descr(self, quantity, typ, plat):
        return (
            f"✅ Вы получаете: {quantity} {typ.lower()} для {plat}\n"
            f"⚡ Время выполнения: 1-24 часа\n"
            f"🎯 Гарантия стабильности\n\n"
            f"{self._return_policy}"
        )

    def generate_discord_boost_lots(self, supplier: str, months: int = 1, copies: Optional[int] = None, max_price: float = 150.0) -> List[Dict[str, Any]]:
        marker = "[GB#" if supplier == "gorgona" else "[HB#"
        name = "GorgonaBoosts" if supplier == "gorgona" else "HoldBoost"
        plat = "Discord"
        typ = "Бустов"
        # Динамическое число копий
        tag = f"{marker}{months}]"
        if copies is None:
            copies = self._calculate_copies(tag)
        tails = self._emojis.get("emojis_tail", ["БЫСТРО", "моментально", "ГАРАНТИЯ", "стабильно", "топ", "PRO", "новинка", "без списаний"])
        emojis_start = self._emojis.get("emojis_start", ["🔥", "⭐", "🚀", "💎", "✅", "💫", "✨", "🎯", "⚡"])
        templates = self._synonyms.get("title_templates", [
            "{emoji} Discord Boost {months}м | {plat} {tail}",
            "{emoji} {plat} Boost {months} месяц {tail}",
            "{emoji} Буст {plat} на {months}м {tail}",
        ])
        cost = float(months) * 50.0
        final_price = self._calculate_market_price(cost, 0, f"Discord Boost {months}м")
        if final_price > max_price:
            return []
        lots = []
        seen = set()
        emoji_cycle = itertools.cycle(emojis_start)
        while len(lots) < copies:
            next(emoji_cycle)
            e1 = next(emoji_cycle)
            tail = random.choice(tails) if random.random() < 0.5 else ""
            tmpl = random.choice(templates)
            raw = tmpl.format(emoji=e1, months=months, plat=plat, tail=tail, marker=marker)
            title = " ".join(raw.split())
            if title in seen:
                continue
            seen.add(title)
            descr = (
                f"✅ Discord Boost на {months} месяц(а)\n"
                f"⚡ Применение: 5-30 минут\n"
                f"🎯 Гарантия стабильности\n\n"
                f"{self._return_policy}"
            )
            lots.append({
                "title": title,
                "description": descr,
                "price_rub": final_price + random.choice([-1, 0, 0, 0, 1]),
                "amount": 1,
                "marker": f"{marker}{months}]",
                "supplier": supplier,
                "months": months,
                "type": "discord_boost",
            })
        return lots

    def generate_kosell_lots(self, products: List[Dict[str, Any]], copies: Optional[int] = None, max_price: float = 150.0) -> List[Dict[str, Any]]:
        lots = []
        templates = [
            "🎮 {name} — {hours}ч аренда",
            "🔥 Аренда {name} на {hours} часов",
            "⭐ {name} | {hours}ч | мгновенная выдача",
            "🎯 {hours}ч аренды: {name}",
            "🚀 {name} {hours} часов — доступ сразу",
        ]
        for product in products:
            pid = product.get("id") or product.get("product_id")
            name = product.get("name") or f"Товар #{pid}"
            cost = float(product.get("price") or 50.0)
            for hours in [1, 3, 6, 12, 24, 48, 72, 168]:
                tag = f"[KS#{pid}:{hours}]"
                c = copies if copies is not None else self._calculate_copies(tag)
                final_price = self._calculate_market_price(cost, 0, name)
                if final_price > max_price:
                    continue
                seen = set()
                while len([l for l in lots if l.get("product_id") == pid and l.get("hours") == hours]) < c:
                    tmpl = random.choice(templates)
                    raw = tmpl.format(name=name, hours=hours, marker=f"[KS#{pid}:{hours}]")
                    title = " ".join(raw.split())
                    if title in seen:
                        continue
                    seen.add(title)
                    descr = (
                        f"✅ Аренда: {name}\n"
                        f"⏱ Срок: {hours} часов\n"
                        f"📋 Данные для входа приходят сразу после оплаты\n\n"
                        f"{self._return_policy}"
                    )
                    lots.append({
                        "title": title,
                        "description": descr,
                        "price_rub": final_price + random.choice([-1, 0, 0, 0, 1]),
                        "amount": 1,
                        "marker": f"[KS#{pid}:{hours}]",
                        "product_id": pid,
                        "product_name": name,
                        "hours": hours,
                        "type": "game_rental",
                    })
        return lots

    # ── Stars (Telegram Stars) ──────────────────────────────────────
    # Генерация лотов для Stars-услуг. Маркер [ST#N].
    # Работает только если настроен FRAGMENT_WALLET_SEED.

    def generate_stars_lots(self, copies: Optional[int] = None,
                            max_price: float = 5000.0) -> List[Dict[str, Any]]:
        """Генерирует лоты для Telegram Stars (50, 100, 200, 500, 1000 звёзд)."""
        stars_options = [50, 100, 200, 500, 1000, 2000]
        result = []
        base_cost_per_star = 1.2  # ~1.2₽ за звезду (себестоимость)
        plat = "Telegram"
        typ = "Звёзд"
        tails = self._emojis.get("emojis_tail", ["БЫСТРО", "моментально", "ГАРАНТИЯ", "живые", "без списаний", "PRO"])
        emojis_start = self._emojis.get("emojis_start", ["⭐", "🔥", "💎", "✅", "🚀"])
        templates = [
            "{emoji} {count} Telegram Stars | {tail}",
            "{emoji} {count} Звёзд Telegram {tail}",
            "{emoji} ✨ {count} TG Stars — {tail}",
            "{emoji} {count} ⭐ Telegram Stars {tail}",
        ]

        for stars in stars_options:
            tag = f"[ST#{stars}]"
            c = copies if copies is not None else self._calculate_copies(tag)
            cost = base_cost_per_star * stars
            final_price = self._calculate_market_price(cost, stars, f"Telegram Stars {stars}")
            if final_price > max_price:
                continue

            seen = set()
            emoji_cycle = itertools.cycle(emojis_start)
            while len([l for l in result if l.get("stars") == stars]) < c:
                e1 = next(emoji_cycle)
                tail = random.choice(tails) if random.random() < 0.5 else ""
                tmpl = random.choice(templates)
                raw = tmpl.format(emoji=e1, count=stars, tail=tail)
                title = " ".join(raw.split())
                if title in seen:
                    continue
                seen.add(title)
                descr = (
                    f"✅ Telegram Stars: {stars} ⭐\n"
                    f"⚡ Зачисление: 1-5 минут\n"
                    f"🎯 Гарантия, живые звёзды\n\n"
                    f"{self._return_policy}"
                )
                result.append({
                    "title": title,
                    "description": descr,
                    "price_rub": final_price + random.choice([-1, 0, 0, 0, 1]),
                    "amount": 1,
                    "marker": tag,
                    "stars": stars,
                    "service_name": f"Telegram Stars {stars}",
                    "type": "stars",
                })
        return result

    def generate_all_lots(self, copies: Optional[int] = None,
                          max_price: float = 150.0) -> Dict[str, List[Dict[str, Any]]]:
        result = {
            "autosmm": [],
            "donate_gorgona": [],
            "donate_holdboost": [],
            "donate_kosell": [],
            "stars": [],
        }

        # AutoSMM (Twiboost)
        for svc in self._load_twiboost_services():
            sid = svc.get("service_id")
            if sid:
                lots = self.generate_lots_for_service(sid, svc.get("name", ""),
                                                      copies=copies, max_price=max_price)
                result["autosmm"].extend(lots)

        # Discord (Gorgona/HoldBoost)
        for supplier, months in [("gorgona", 1), ("gorgona", 3),
                                  ("holdboost", 1), ("holdboost", 3)]:
            lots = self.generate_discord_boost_lots(supplier, months=months,
                                                     copies=copies, max_price=max_price)
            key = f"donate_{supplier}"
            if key not in result:
                result[key] = []
            result[key].extend(lots)

        # Kosell
        kosell_products = self._load_kosell_products()
        if kosell_products:
            result["donate_kosell"] = self.generate_kosell_lots(kosell_products,
                                                                 copies=copies, max_price=max_price)

        # Stars (если настроен Fragment)
        import os as _os
        if _os.environ.get("FRAGMENT_WALLET_SEED", "").strip():
            result["stars"] = self.generate_stars_lots(copies=copies, max_price=max_price)

        return result

    def save_lots(self, lots: List[Dict[str, Any]], plugin: str, supplier: str = "") -> Dict[str, Any]:
        if not self._seller_service:
            return {"ok": False, "error": "seller_service not available"}
        print(f"[LotGenerator] save_lots called: total_lots={len(lots)}, plugin={plugin!r}, supplier={supplier!r}")
        created = 0
        failed = 0
        for lot in lots:
            try:
                title = lot.get("title", "")
                descr = lot.get("description", "")
                price = float(lot.get("price_rub") or 0)
                if not title or not price:
                    failed += 1
                    continue
                # Определяем category_id в зависимости от типа услуги
                lot_type = lot.get("type", "")
                category_id = None
                if lot_type == "discord_boost":
                    category_id = 14  # Discord-буст (пример)
                elif lot_type == "stars":
                    category_id = 26  # Telegram Stars (пример)
                elif lot_type == "game_rental":
                    category_id = 18  # Аренда игр

                print(f"[LotGenerator] Attempting to create lot: title={title!r}, price={price}, category_id={category_id}")
                result = self._seller_service.create_lot({
                    "title": title,
                    "description": descr,
                    "price": price,
                    "amount": lot.get("amount", 1),
                    "category_id": category_id,
                })
                print(f"[LotGenerator] Lot creation result: ok={result.get('ok')}, id={result.get('id')}, error={result.get('error')}")
                if result.get("ok"):
                    created += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"[LotGenerator] Error creating lot: {e}")
        return {"ok": True, "created": created, "failed": failed, "total": len(lots)}
