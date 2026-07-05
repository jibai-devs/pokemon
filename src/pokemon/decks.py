"""Deck definitions and helpers.

This is the canonical source for deck lists. The numbered artifacts under
``deck/`` (decklist md, gameplay md) document a deck; the importable definition
lives here.
"""

import hashlib
from collections import Counter

from pokemon.catalog import card_name

# 000 Fire Deck — Gouging Fire ex + Magcargo ex (60 cards).
FIRE_DECK = (
    [46] * 2  # Gouging Fire ex
    + [76] * 4  # Slugma
    + [30] * 4  # Magcargo ex
    + [1092]  # Secret Box
    + [1121] * 2  # Ultra Ball
    + [1145] * 2  # Mega Signal
    + [1163] * 2  # Powerglass
    + [1219] * 4  # Team Rocket's Petrel
    + [1227] * 4  # Lillie's Determination
    + [1245] * 2  # Festival Grounds
    + [2] * 33  # Basic Fire Energy
)

assert len(FIRE_DECK) == 60, f"FIRE_DECK has {len(FIRE_DECK)} cards, expected 60"

# 001 Psychic Toolbox — Slowking + Mega Kangaskhan ex (60 cards).
# Psychic-type control/toolbox: Slowking sets up, Mega Kangaskhan ex is the main
# attacker, backed by Latias ex / Kyurem / Metagross tech and a heavy draw engine.
PSYCHIC_DECK = (
    # Pokemon (20)
    [162] * 4  # Slowpoke (Psychic, evolves into Slowking)
    + [163] * 3  # Slowking
    + [756] * 3  # Mega Kangaskhan ex
    + [184] * 2  # Latias ex
    + [144] * 2  # Kyurem
    + [276] * 2  # Metagross
    + [1071]  # Meowth ex
    + [956]  # Zeraora
    + [272]  # Lillie's Clefairy ex
    + [140]  # Fezandipiti ex
    # Trainers (29)
    + [1227] * 4  # Lillie's Determination
    + [1188] * 4  # Ciphermaniac's Codebreaking
    + [1152] * 4  # Poké Pad
    + [1121] * 4  # Ultra Ball
    + [1146] * 3  # Wondrous Patch
    + [1097] * 2  # Night Stretcher
    + [1092]  # Secret Box (ACE SPEC)
    + [1123]  # Switch
    + [1175]  # Brave Bangle
    + [1156]  # Lucky Helmet
    + [1248] * 4  # Academy at Night
    # Energy (11)
    + [19] * 4  # Telepath Psychic Energy
    + [5] * 4  # Basic Psychic Energy
    + [9] * 3  # Boomerang Energy
)

assert len(PSYCHIC_DECK) == 60, f"PSYCHIC_DECK has {len(PSYCHIC_DECK)} cards, expected 60"

DEFAULT_DECK = PSYCHIC_DECK


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
