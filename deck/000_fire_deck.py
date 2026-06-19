"""000 Fire Deck — Gouging Fire ex + Magcargo ex.

The canonical, importable definition lives in ``pokemon.decks.FIRE_DECK``; this
file re-exports it so the numbered ``deck/`` artifacts stay self-describing.
"""

from pokemon.decks import FIRE_DECK as deck

assert len(deck) == 60, f"Deck has {len(deck)} cards, expected 60"
