import pytest


def _pokemon(card_id: int, hp: int, max_hp: int, n_energy: int) -> dict:
    return {
        "id": card_id,
        "serial": 1,
        "playerIndex": 0,
        "hp": hp,
        "maxHp": max_hp,
        "appearThisTurn": False,
        "energies": [2] * n_energy,
        "energyCards": [],
        "tools": [],
        "preEvolution": [],
    }


def _player(active, bench, prize: int, hand_ids: list[int]) -> dict:
    return {
        "active": [active] if active else [],
        "bench": bench,
        "benchMax": 5,
        "deckCount": 50,
        "discard": [],
        "prize": [None] * prize,
        "handCount": len(hand_ids),
        "hand": [{"id": c, "serial": 1, "playerIndex": 0} for c in hand_ids],
        "poisoned": False,
        "burned": False,
        "asleep": False,
        "paralyzed": False,
        "confused": False,
    }


@pytest.fixture
def main_obs() -> dict:
    """A MAIN-phase decision: ATTACH hand card 0 to active, or END."""
    me = _player(_pokemon(722, 90, 90, 1), [_pokemon(76, 70, 70, 0)], prize=6, hand_ids=[2, 46])
    opp = _player(_pokemon(30, 80, 120, 2), [], prize=5, hand_ids=[])
    return {
        "step": 5,
        "select": {
            "type": 0,
            "context": 0,
            "minCount": 1,
            "maxCount": 1,
            "remainDamageCounter": 0,
            "remainEnergyCost": 0,
            "option": [
                {"type": 8, "area": 2, "index": 0, "inPlayArea": 4, "inPlayIndex": 0},
                {"type": 14},
            ],
        },
        "current": {
            "turn": 3,
            "turnActionCount": 1,
            "yourIndex": 0,
            "firstPlayer": 0,
            "supporterPlayed": False,
            "stadiumPlayed": False,
            "energyAttached": False,
            "retreated": False,
            "result": -1,
            "stadium": None,
            "looking": [],
            "players": [me, opp],
        },
    }
