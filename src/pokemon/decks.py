"""Deck definitions and helpers.

This is the canonical source for deck lists. The numbered artifacts under
``deck/`` (decklist md, gameplay md) document a deck; the importable definition
lives here.

Add a new deck by defining a ``list[int]`` of 60 card ids, asserting its
length, and registering it in ``DECKS`` below.
"""

import hashlib
from collections import Counter

from pokemon.catalog import card_name

# 002 Dragapult Deck — Dragapult ex ("Pult Noir") Phantom Dive engine (60 cards).
# Source: dragapult_deck_explanation.md, Section 1.
DRAGAPULT_DECK = (
    [119] * 4  # Dreepy
    + [120] * 4  # Drakloak
    + [121] * 3  # Dragapult ex
    + [112] * 2  # Munkidori
    + [235] * 2  # Budew
    + [791]  # Moltres
    + [140]  # Fezandipiti ex
    + [1071]  # Meowth ex
    + [1227] * 4  # Lillie's Determination
    + [1198] * 3  # Crispin
    + [1182] * 3  # Boss's Orders
    + [1213]  # Judge
    + [1120] * 4  # Crushing Hammer
    + [1086] * 4  # Buddy-Buddy Poffin
    + [1152] * 4  # Poke Pad
    + [1121] * 4  # Ultra Ball
    + [1097] * 2  # Night Stretcher
    + [1080]  # Unfair Stamp (ACE SPEC)
    + [1260]  # Risky Ruins
    + [1256]  # Team Rocket's Watchtower
    + [1197]  # Xerosic's Machinations
    + [2] * 4  # Fire Energy
    + [5] * 3  # Psychic Energy
    + [7] * 2  # Darkness Energy
)

assert len(DRAGAPULT_DECK) == 60, f"DRAGAPULT_DECK has {len(DRAGAPULT_DECK)} cards, expected 60"

# Central deck registry. Add a deck here once its card list is non-empty and
# sums to 60; everything else (CLI, deck.csv export, agent) reads from this.
DECKS: dict[str, list[int]] = {"dragapult": DRAGAPULT_DECK}

# The deck used by default when nothing else is specified.
ACTIVE_DECK_NAME: str = "dragapult"
ACTIVE_DECK: list[int] = DECKS[ACTIVE_DECK_NAME]


def deck_summary(deck: list[int]) -> tuple[list[str], str]:
    """Return (per-card breakdown lines, checksum) for a deck list.

    The checksum is a canonical fingerprint: ids are sorted first, so the same
    multiset of cards always hashes the same regardless of build order.
    """
    counts = Counter(deck)
    lines = [
        f"  {n:2}x {card_name(cid)} (#{cid})"
        for cid, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    ]
    digest = hashlib.sha256(",".join(map(str, sorted(deck))).encode()).hexdigest()[:8]
    return lines, digest
