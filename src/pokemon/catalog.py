"""Card/attack name resolution and option formatting for the CABT engine.

Names resolve from the full reverse-engineered catalogs in
``reverse-engineering/data/`` (1267 cards, 1556 attacks), with a small
hand-picked override map for nicer display names.
"""

import json
from pathlib import Path

from pokemon.cabt_enums import (
    AreaType,
    OptionType,
    SelectContext,
    SpecialConditionType,
    safe,
)

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


def _load_catalog() -> tuple[dict[int, str], dict[int, dict], dict[int, dict]]:
    names: dict[int, str] = {}
    card_data: dict[int, dict] = {}
    attacks: dict[int, dict] = {}
    try:
        for c in json.loads((_DATA_DIR / "all_cards.json").read_text()):
            names[c["cardId"]] = c["name"]
            card_data[c["cardId"]] = c
    except OSError:
        pass
    try:
        for a in json.loads((_DATA_DIR / "all_attacks.json").read_text()):
            attacks[a["attackId"]] = a
    except OSError:
        pass
    return names, card_data, attacks


_CARD_CATALOG, _CARD_DATA, _ATK_CATALOG = _load_catalog()


def card_record(card_id: int) -> dict | None:
    return _CARD_DATA.get(card_id)


def attack_record(attack_id: int) -> dict | None:
    return _ATK_CATALOG.get(attack_id)


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


def _area_name(area: int | None) -> str:
    a = safe(AreaType, area)
    return a.name if a is not None else "?"


def _ctx_name(context) -> str:
    """Name for a ``select.context`` value (accepts int or enum), or empty."""
    if isinstance(context, SelectContext):
        return context.name
    c = safe(SelectContext, context)
    return c.name if c is not None else ""


def _slot(opt: dict, hand: list) -> str:
    """Locate a card slot as ``Name`` (if in our hand) or ``AREA#index``.

    PLAY options omit ``area`` (their ``index`` is implicitly into the hand), so a
    missing area defaults to HAND.
    """
    area = opt.get("area", AreaType.HAND)
    index = opt.get("index", -1)
    player = opt.get("playerIndex", 0)
    if area == AreaType.HAND and player == 0 and 0 <= index < len(hand):
        return card_name(hand[index].get("id", -1))
    tag = f"{_area_name(area)}#{index}"
    return f"opp {tag}" if player == 1 else tag


def format_option(opt: dict, hand: list, context=None) -> str:
    """Human-readable label for an option dict.

    ``context`` is the enclosing ``select.context`` (int or :class:`SelectContext`);
    it disambiguates options whose ``type`` alone is not enough — most importantly
    ``OptionType.NUMBER``, which is just ``{"type": 0, "number": n}`` and means
    ``DRAW_COUNT=n`` in one place and ``DAMAGE_COUNTER_COUNT=n`` in another.

    Labels follow the engine's real ``OptionType`` enum (7=PLAY, 8=ATTACH), not
    the older reverse-engineered map that this function used to carry.
    """
    t = safe(OptionType, opt.get("type"))
    ctx = _ctx_name(context)

    if t == OptionType.NUMBER:
        return f"{ctx or 'NUMBER'}={opt.get('number')}"
    if t == OptionType.YES:
        return f"{ctx or 'YES_NO'}=YES"
    if t == OptionType.NO:
        return f"{ctx or 'YES_NO'}=NO"
    if t == OptionType.CARD:
        return f"{ctx or 'CARD'} {_slot(opt, hand=hand)}"
    if t == OptionType.TOOL_CARD:
        return f"{ctx or 'TOOL'} {_slot(opt, hand=hand)} (tool#{opt.get('toolIndex')})"
    if t == OptionType.ENERGY_CARD:
        return f"{ctx or 'ENERGY_CARD'} {_slot(opt, hand=hand)} (nrg#{opt.get('energyIndex')})"
    if t == OptionType.ENERGY:
        return f"{ctx or 'ENERGY'} x{opt.get('count', 1)} @{_slot(opt, hand=hand)}"
    if t == OptionType.PLAY:
        return f"PLAY {_slot(opt, hand=hand)}"
    if t == OptionType.ATTACH:
        tgt = f"{_area_name(opt.get('inPlayArea'))}#{opt.get('inPlayIndex')}"
        return f"ATTACH {_slot(opt, hand=hand)} -> {tgt}"
    if t == OptionType.EVOLVE:
        tgt = f"{_area_name(opt.get('inPlayArea'))}#{opt.get('inPlayIndex')}"
        return f"EVOLVE {_slot(opt, hand=hand)} -> {tgt}"
    if t == OptionType.ABILITY:
        return f"ABILITY {_slot(opt, hand=hand)}"
    if t == OptionType.DISCARD:
        return f"DISCARD {_slot(opt, hand=hand)}"
    if t == OptionType.RETREAT:
        return "RETREAT"
    if t == OptionType.ATTACK:
        return f"ATTACK: {atk_name(opt.get('attackId', 0))}"
    if t == OptionType.END:
        return "END TURN"
    if t == OptionType.SKILL:
        return f"SKILL {card_name(opt.get('cardId', -1))}"
    if t == OptionType.SPECIAL_CONDITION:
        sc = safe(SpecialConditionType, opt.get("specialConditionType"))
        return f"CONDITION {sc.name if sc is not None else '?'}"
    # Unknown OptionType: surface the raw value, never a bare 'OK'.
    name = t.name if t is not None else f"type={opt.get('type')}"
    return f"{name}={opt.get('number', '')}".rstrip("=")
