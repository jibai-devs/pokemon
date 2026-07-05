"""001 Psychic Deck — Mega Kangaskhan ex / Latias ex control-ish shell.

The canonical, importable definition lives in ``pokemon.decks.PSYCHIC_DECK``;
this file re-exports it so the numbered ``deck/`` artifacts stay
self-describing.
"""

from pokemon.decks import PSYCHIC_DECK as deck

assert len(deck) == 60, f"Deck has {len(deck)} cards, expected 60"
