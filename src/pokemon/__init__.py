"""Pokémon TCG (CABT) agent package.

Currently centered on a hand-written heuristic agent for the 000 fire deck,
used to play and understand games before training. See AGENTS.md.
"""

from pokemon.agent import fire_agent, score_option
from pokemon.catalog import atk_name, card_name, format_option
from pokemon.decks import FIRE_DECK, deck_summary

__all__ = [
    "FIRE_DECK",
    "atk_name",
    "card_name",
    "deck_summary",
    "fire_agent",
    "format_option",
    "score_option",
]
