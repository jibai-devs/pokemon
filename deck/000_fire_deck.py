"""000 Fire Deck — Gouging Fire ex + Magcargo ex"""

# Card IDs for use with kaggle_environments cabt agent
deck = (
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

assert len(deck) == 60, f"Deck has {len(deck)} cards, expected 60"
