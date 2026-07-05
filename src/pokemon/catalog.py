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
    # Fire deck (000)
    46: "Gouging Fire ex",
    76: "Slugma",
    30: "Magcargo ex",
    2: "Fire Energy",
    1145: "Mega Signal",
    1163: "Powerglass",
    1219: "Rocket Petrel",
    1227: "Lillie Determination",
    1245: "Festival Grounds",
    # Shared trainers (used by both decks)
    1092: "Secret Box",
    1121: "Ultra Ball",
    # Psychic deck (001)
    5: "Psychic Energy",
    9: "Boomerang Energy",
    19: "Telepath Psychic Energy",
    140: "Fezandipiti ex",
    144: "Kyurem",
    162: "Slowpoke",
    163: "Slowking",
    184: "Latias ex",
    272: "Lillie's Clefairy ex",
    276: "Metagross",
    756: "Mega Kangaskhan ex",
    956: "Zeraora",
    1071: "Meowth ex",
    1097: "Night Stretcher",
    1123: "Switch",
    1146: "Wondrous Patch",
    1152: "Poke Pad",
    1156: "Lucky Helmet",
    1175: "Brave Bangle",
    1188: "Ciphermaniac's Codebreaking",
    1248: "Academy at Night",
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
    """Human-readable label for an option dict (OptionType enum from engine docs).

    KNOWN ISSUE (see PKM-017): types 3 and 7 always index into ``hand``
    regardless of the option's own ``area`` field. For hand-area options
    that's correct, but a real playtest showed bench/active/deck-area
    options (e.g. a "switch to bench Pokemon" choice) get mislabeled with
    whatever happens to be at that index in hand — purely a display bug,
    doesn't affect which option index actually gets chosen. Fix by
    threading board state (``me``'s bench/active) into this function and
    branching on ``opt.get("area")`` before assuming HAND.
    """
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
