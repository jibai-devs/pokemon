"""002 Dragapult Deck — Dragapult ex ("Pult Noir") Phantom Dive engine.

The canonical, importable definition lives in ``pokemon.decks.DRAGAPULT_DECK``;
this file re-exports it so the numbered ``deck/`` artifacts stay
self-describing.
"""

from pokemon.decks import DRAGAPULT_DECK as deck

assert len(deck) == 60, f"Deck has {len(deck)} cards, expected 60"
