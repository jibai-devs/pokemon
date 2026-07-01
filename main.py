import os
import random

try:
    _deck_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "deck.csv")
except NameError:
    _deck_path = "/kaggle_simulations/agent/deck.csv"

with open(_deck_path) as f:
    DECK = [int(line.strip()) for line in f if line.strip()]

assert len(DECK) == 60, f"deck.csv has {len(DECK)} cards, expected 60"


def agent(obs_dict: dict) -> list[int]:
    select = obs_dict.get("select")
    if select is None:
        return DECK
    options = select["option"]
    max_count = select["maxCount"]
    return random.sample(range(len(options)), min(max_count, len(options)))
