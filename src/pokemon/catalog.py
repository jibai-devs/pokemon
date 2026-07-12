"""Card/attack name resolution and option formatting for the CABT engine.

Names resolve from the full reverse-engineered catalogs in
``reverse-engineering/data/`` (1267 cards, 1556 attacks), with a small
hand-picked override map for nicer display names.
"""

import json
from pathlib import Path
from typing import Required, TypedDict, cast

from pokemon.types import AttackId, CardId, CardState, Option


class CardCatalogEntry(TypedDict, total=False):
    cardId: Required[CardId]
    name: Required[str]
    cardType: int
    pokemonType: int
    evolutionType: int
    retreatCost: int
    hp: int
    weakness: int | None
    resistance: int | None
    energyType: int
    basic: bool
    stage1: bool
    stage2: bool
    ex: bool
    megaEx: bool
    tera: bool
    aceSpec: bool
    evolvesFrom: CardId | None
    skills: list[int]
    attacks: list[AttackId]


class AttackCatalogEntry(TypedDict):
    attackId: AttackId
    name: str
    text: str
    damage: int
    energies: list[int]

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


def _load_catalog() -> tuple[
    dict[CardId, str],
    dict[AttackId, AttackCatalogEntry],
    dict[CardId, list[AttackId]],
    dict[CardId, CardCatalogEntry],
]:
    cards: dict[int, str] = {}
    attacks: dict[AttackId, AttackCatalogEntry] = {}
    card_attacks: dict[int, list[int]] = {}
    card_raw: dict[CardId, CardCatalogEntry] = {}
    try:
        raw_cards = cast(
            list[CardCatalogEntry],
            json.loads((_DATA_DIR / "all_cards.json").read_text()),
        )
        for c in raw_cards:
            cards[c["cardId"]] = c["name"]
            card_attacks[c["cardId"]] = c.get("attacks") or []
            card_raw[c["cardId"]] = c
    except OSError:
        pass
    try:
        raw_attacks = cast(
            list[AttackCatalogEntry],
            json.loads((_DATA_DIR / "all_attacks.json").read_text()),
        )
        for a in raw_attacks:
            attacks[a["attackId"]] = a
    except OSError:
        pass
    return cards, attacks, card_attacks, card_raw


_CARD_CATALOG, _ATK_CATALOG, _CARD_ATTACKS, _CARD_RAW = _load_catalog()


def card_info(card_id: CardId | None) -> CardCatalogEntry | None:
    """Raw catalog entry for a card (hp, basic/ex/stage flags, evolvesFrom,
    attacks, weakness/resistance), or ``None`` if not in the catalog."""
    if card_id is None:
        return None
    return _CARD_RAW.get(card_id)


def attack_info(attack_id: AttackId | None) -> AttackCatalogEntry | None:
    """Raw catalog entry for an attack (damage, energies cost list), or
    ``None`` if not in the catalog."""
    if attack_id is None:
        return None
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


def min_attack_energy_cost(card_id: int) -> int | None:
    """Fewest energy cards needed for any of ``card_id``'s attacks, or
    ``None`` if the card/its attacks aren't in the catalog.

    Data-driven (reads real attack costs from the reverse-engineered
    catalog) rather than a hardcoded per-card guess, so it works for any
    Pokemon in any deck, not just ones we've special-cased.
    """
    attack_ids = _CARD_ATTACKS.get(card_id)
    if not attack_ids:
        return None
    costs = [len(_ATK_CATALOG[aid]["energies"]) for aid in attack_ids if aid in _ATK_CATALOG]
    return min(costs) if costs else None


def format_option(opt: Option, hand: list[CardState]) -> str:
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
