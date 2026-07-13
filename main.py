import os
import sys

try:
    _base_dir = os.path.dirname(os.path.abspath(__file__))
except NameError:
    _base_dir = "/kaggle_simulations/agent"

_deck_path = os.path.join(_base_dir, "deck.csv")
_src_path = os.path.join(_base_dir, "src")
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)

with open(_deck_path) as f:
    DECK = [int(line.strip()) for line in f if line.strip()]

assert len(DECK) == 60, f"deck.csv has {len(DECK)} cards, expected 60"

from pokemon.admin import build_agent  # noqa: E402
from pokemon.decks import ACTIVE_DECK_NAME  # noqa: E402

agent = build_agent(DECK, ACTIVE_DECK_NAME)
