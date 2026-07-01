"""Card/attack name resolution and option formatting for the CABT engine.

Names resolve from the full reverse-engineered catalogs in
``reverse-engineering/data/`` (1267 cards, 1556 attacks), with a small
hand-picked override map for nicer display names.
"""

import json
from pathlib import Path

# Catalogs live at the repo root, outside the installed package:
# src/pokemon/catalog.py -> parents[2] == repo root.
_DATA_DIR = Path(__file__).resolve().parents[2] / "reverse-engineering" / "data"

# Hand-picked labels that override the full catalog where a nicer name is wanted
# (e.g. "Fire Energy" instead of the catalog's "Basic {R} Energy").
CARD_NAMES = {
    46: "Gouging Fire ex",
    76: "Slugma",
    30: "Magcargo ex",
    2: "Fire Energy",
    1092: "Secret Box",
    1121: "Ultra Ball",
    1145: "Mega Signal",
    1163: "Powerglass",
    1219: "Rocket Petrel",
    1227: "Lillie Determination",
    1245: "Festival Grounds",
}

ATK_NAMES = {
    44: "Heat Blast (60)",
    45: "Blaze Blitz (260)",
    17: "Hot Magma (70)",
    18: "Ground Burn (140+)",
}


def _load_catalog() -> tuple[dict[int, str], dict[int, dict]]:
    cards: dict[int, str] = {}
    attacks: dict[int, dict] = {}
    try:
        for c in json.loads((_DATA_DIR / "all_cards.json").read_text()):
            cards[c["cardId"]] = c["name"]
    except OSError:
        pass
    try:
        for a in json.loads((_DATA_DIR / "all_attacks.json").read_text()):
            attacks[a["attackId"]] = a
    except OSError:
        pass
    return cards, attacks


_CARD_CATALOG, _ATK_CATALOG = _load_catalog()


def card_name(card_id: int) -> str:
    if card_id in CARD_NAMES:
        return CARD_NAMES[card_id]
    if card_id in _CARD_CATALOG:
        return _CARD_CATALOG[card_id]
    return f"Card#{card_id}"


def atk_name(atk_id: int) -> str:
    if atk_id in ATK_NAMES:
        return ATK_NAMES[atk_id]
    a = _ATK_CATALOG.get(atk_id)
    if a:
        dmg = a.get("damage", 0)
        return f"{a['name']} ({dmg})" if dmg else a["name"]
    return f"#{atk_id}"


def format_option(opt: dict, hand: list) -> str:
    """Human-readable label for an option dict (OptionType enum from engine docs)."""
    t = opt.get("type", -1)
    if t == 1:
        return "GO FIRST"
    if t == 2:
        return "GO SECOND"
    if t == 3:
        idx = opt.get("index", -1)
        if 0 <= idx < len(hand):
            return f"PLAY {card_name(hand[idx].get('id', -1))}"
        return f"PLAY hand[{idx}]"
    if t == 7:  # PLAY — play card from hand
        idx = opt.get("index", -1)
        if 0 <= idx < len(hand):
            return f"PLAY {card_name(hand[idx].get('id', -1))}"
        return f"PLAY hand[{idx}]"
    if t == 8:  # ATTACH — attach energy/tool
        idx = opt.get("index", -1)
        if 0 <= idx < len(hand):
            return f"ATTACH {card_name(hand[idx].get('id', -1))}"
        return f"ATTACH hand[{idx}]"
    if t == 9:
        return "EVOLVE"
    if t == 10:
        return "ABILITY"
    if t == 11:
        return "DISCARD"
    if t == 12:
        return "RETREAT"
    if t == 13:
        return f"ATTACK: {atk_name(opt.get('attackId', 0))}"
    if t == 14:
        return "END TURN"
    if t == 0:
        n = opt.get("number")
        return "OK" if n is None else f"OK#{n}"
    return f"?type={t}"
