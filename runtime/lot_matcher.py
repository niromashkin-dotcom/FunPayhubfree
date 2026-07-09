"""
Universal Lot Auto-Matcher for FunPay Hub plugins.

Used by AutoSMM (and future plugins like Stars, TopUp, etc.) to automatically
build mapping: my_funpay_lot -> external_provider_service_id.

Algorithm:
  1. Plugin provides:
     - list of FunPay lots (with id, title, subcategory_name, category_name)
     - list of provider services (with service_id, name/description, keywords)
     - matching profile (category filters, must-have keywords)
  2. Matcher computes similarity score and returns three buckets:
     - high   (>=0.75) -> auto-attach
     - medium (>=0.50) -> suggest for manual confirmation
     - low    (<0.50)  -> skip

Scoring rules:
  - +0.40 if category_name matches plugin profile
  - +0.30 for each must-have keyword present in lot title
  - +0.20 for "quantity match" (1000 in lot vs 1000 in service)
  - +0.10 for fuzzy text similarity (lot title vs service name)
"""
from __future__ import annotations
import re
from difflib import SequenceMatcher
from typing import List, Dict, Optional


# Normalized quantity extractor: 1000, 1к, 1k, 1 тыс
_QTY_RE = re.compile(r'(\d+)\s*(к|k|тыс|000)?', re.IGNORECASE)


def _normalize(text: str) -> str:
    if not text:
        return ""
    t = text.lower()
    t = re.sub(r'[^\w\s]', ' ', t, flags=re.UNICODE)
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def _extract_quantities(text: str) -> List[int]:
    if not text:
        return []
    out = []
    for m in _QTY_RE.finditer(text):
        try:
            n = int(m.group(1))
            suf = (m.group(2) or "").lower()
            if suf in ("к", "k", "тыс"):
                n *= 1000
            out.append(n)
        except (ValueError, TypeError):
            pass
    return out


def _text_similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, _normalize(a), _normalize(b)).ratio()


def match_lot_to_service(
    lot: Dict,
    services: List[Dict],
    profile: Optional[Dict] = None,
) -> List[Dict]:
    """
    Match one FunPay lot against list of provider services.
    Returns list of candidates sorted by score (best first).

    profile = {
        "category_keywords": ["telegram", "телеграм"],   # must match category_name OR title
        "service_keywords":  ["подписчик", "subscriber"], # must be in lot title
        "exclude_keywords":  ["просмотр", "view"],        # if any present — skip lot entirely
    }
    """
    profile = profile or {}
    lot_title = lot.get("title", "") or ""
    lot_category = (lot.get("category_name", "") or "") + " " + (lot.get("subcategory_name", "") or "")
    lot_text_full = _normalize(lot_title + " " + lot_category)

    # Hard exclude
    excludes = [k.lower() for k in (profile.get("exclude_keywords") or [])]
    for kw in excludes:
        if kw and kw in lot_text_full:
            return []

    # Category gate
    cat_kws = [k.lower() for k in (profile.get("category_keywords") or [])]
    if cat_kws:
        if not any(k in lot_text_full for k in cat_kws):
            return []

    # Service-type keywords gate (must have at least one)
    srv_kws = [k.lower() for k in (profile.get("service_keywords") or [])]
    if srv_kws:
        if not any(k in lot_text_full for k in srv_kws):
            return []

    lot_quantities = _extract_quantities(lot_title)

    # Detect lot service type group (subscribers / views / likes / etc)
    # These groups are mutually exclusive — буст подписчиков ≠ накрутка просмотров.
    LOT_GROUPS = {
        "subscribers": ["подписчик", "subscriber", "member", "участник", "follower", "аудитор", "канал"],
        "views":       ["просмотр", "view", "показ", "зрител"],
        "likes":       ["лайк", "like", "сердечк", "heart"],
        "reactions":   ["реакц", "reaction", "эмоц"],
        "comments":    ["комент", "коммент", "comment", "отзыв"],
        "reposts":     ["репост", "share", "перепост"],
        "boosts":      ["буст", "boost"],
        "friends":     ["друз", "friend"],
        "votes":       ["голос", "vote", "poll", "опрос"],
        "stars":       ["звезд", "star", "stars", "звёзд"],
        "gifts":       ["подар", "gift", "подарок"],
        "premium":     ["премиум", "premium", "премиум"],
        "usernames":   ["юзернейм", "username", "ник", "имя", "нейм"],
        "stickers":    ["стикер", "sticker", "эмодзи", "emoji"],
        "games":       ["игр", "game", "игра"],
    }
    lot_groups_detected = set()
    for grp, kws in LOT_GROUPS.items():
        if any(kw in lot_text_full for kw in kws):
            lot_groups_detected.add(grp)

    results = []
    for s in services:
        sname = s.get("name") or s.get("service_name") or ""
        sid = s.get("service_id") or s.get("id") or s.get("service")
        if not sid or not sname:
            continue

        srv_text_full = _normalize(sname + " " + (s.get("category", "") or ""))
        srv_type = (s.get("type") or "").lower()

        # Detect service group from Twiboost type field (gold!) or fallback to name analysis
        SERVICE_TYPE_MAP = {
            "subscribe": "subscribers",
            "follow":    "subscribers",
            "friend":    "friends",
            "like":      "likes",
            "favorite":  "likes",
            "dislike":   "likes",
            "view":      "views",
            "comment":   "comments",
            "like_to_comment": "comments",
            "dislike_to_comment": "comments",
            "repost":    "reposts",
            "retweet":   "reposts",
            "vote":      "votes",
        }
        srv_group = SERVICE_TYPE_MAP.get(srv_type)
        if not srv_group:
            # Fallback by name keywords only
            for grp, kws in LOT_GROUPS.items():
                if any(k in srv_text_full for k in kws):
                    srv_group = grp
                    break

        # HARD FILTER: if lot wants "subscribers" but service is "views" — skip entirely
        if lot_groups_detected and srv_group:
            if srv_group not in lot_groups_detected:
                continue

        score = 0.0
        reasons = []

        # Group match (CRITICAL +0.50)
        if lot_groups_detected and srv_group and srv_group in lot_groups_detected:
            score += 0.50
            reasons.append(f"group:{srv_group}")

        # Category match (+0.30)
        if cat_kws and any(k in lot_text_full for k in cat_kws) and any(k in srv_text_full for k in cat_kws):
            score += 0.30
            reasons.append("category")

        # Quantity match (+0.15)
        srv_quantities = _extract_quantities(sname)
        if lot_quantities and srv_quantities:
            qty_match = False
            for lq in lot_quantities:
                for sq in srv_quantities:
                    if lq == sq:
                        qty_match = True
                        break
                if qty_match:
                    break
            if qty_match:
                score += 0.15
                reasons.append("qty")

        # "Russian/Ru" bonus (+0.05) — лоты часто специально РФ
        if ("российск" in lot_text_full or "русск" in lot_text_full or "ru " in lot_text_full):
            if ("россий" in srv_text_full or "русск" in srv_text_full or " ru " in srv_text_full
                or "rus" in srv_text_full or "[ru]" in sname.lower()):
                score += 0.05
                reasons.append("ru")

        # Text similarity (+0.10 max)
        sim = _text_similarity(lot_title, sname)
        score += sim * 0.10
        if sim > 0.3:
            reasons.append(f"sim:{sim:.2f}")

        if score > 0:
            results.append({
                "service_id": sid,
                "service_name": sname,
                "score": round(score, 3),
                "reasons": reasons,
                "lot_quantities": lot_quantities,
                "service_group": srv_group,
                "service_type":  srv_type,
                "rate":          s.get("rate"),
                "min":           s.get("min"),
                "max":           s.get("max"),
            })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results


def classify_match(score: float) -> str:
    if score >= 0.75:
        return "high"
    if score >= 0.50:
        return "medium"
    return "low"


def auto_build_mapping(
    lots: List[Dict],
    services: List[Dict],
    profile: Optional[Dict] = None,
    auto_threshold: float = 0.75,
) -> Dict:
    """
    Run matcher on all lots and produce:
      {
        "auto":      {lot_id: {service_id, score, quantity, service_name}},
        "suggested": {lot_id: [list of candidates]},
        "skipped":   [lot_ids without any candidate],
      }
    """
    out_auto = {}
    out_suggested = {}
    out_skipped = []

    for lot in lots:
        lot_id = lot.get("id")
        if not lot_id:
            continue
        candidates = match_lot_to_service(lot, services, profile)
        if not candidates:
            out_skipped.append(lot_id)
            continue

        top = candidates[0]
        if top["score"] >= auto_threshold:
            out_auto[str(lot_id)] = {
                "service_id":   top["service_id"],
                "service_name": top["service_name"],
                "score":        top["score"],
                "reasons":      top["reasons"],
                "quantity":     top["lot_quantities"][0] if top["lot_quantities"] else None,
                "lot_title":    lot.get("title"),
            }
        else:
            out_suggested[str(lot_id)] = {
                "lot_title": lot.get("title"),
                "candidates": candidates[:5],
            }

    return {
        "auto": out_auto,
        "suggested": out_suggested,
        "skipped": out_skipped,
        "stats": {
            "total_lots":      len(lots),
            "auto_matched":    len(out_auto),
            "needs_review":    len(out_suggested),
            "skipped":         len(out_skipped),
        },
    }