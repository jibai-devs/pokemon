"""Baseline agent for the 000 fire deck.

Submits the fire deck and picks random legal moves. Verbose mode logs the full
board state each turn so you can read game flow and understand the engine.
"""

import random

from pokemon.catalog import card_name, format_option
from pokemon.decks import FIRE_DECK, deck_summary

_verbose = False
_game_num = 0


def set_verbose(value: bool) -> None:
    global _verbose
    _verbose = value


def set_game_num(value: int) -> None:
    global _game_num
    _game_num = value


def _log(msg: str) -> None:
    if _verbose:
        print(msg)


def fire_agent(obs: dict) -> list[int]:
    """Pick action(s) for the fire deck given an engine observation."""

    if obs["select"] is None:
        lines, checksum = deck_summary(FIRE_DECK)
        _log(f"\n{'=' * 60}")
        _log(f"GAME {_game_num}: Submitting deck ({len(FIRE_DECK)} cards, sha256:{checksum})")
        _log(f"{'=' * 60}")
        if _game_num <= 1:
            for line in lines:
                _log(line)
        return FIRE_DECK

    select = obs["select"]
    options = select["option"]
    max_count = select["maxCount"]
    current = obs.get("current", {})
    my_idx = current.get("yourIndex", 0)
    players = current.get("players", [])
    me = players[my_idx] if my_idx < len(players) else {}
    hand = me.get("hand", []) or []
    active = me.get("active", [])
    bench = me.get("bench", [])
    turn = current.get("turn", 0)

    if _verbose:
        if active and active[0]:
            a = active[0]
            a_name = card_name(a.get("id", -1))
            a_hp = a.get("hp", "?")
            a_max = a.get("maxHp", "?")
            a_nrg = len(a.get("energies", []))
            bench_names = [card_name(c.get("id", -1)) for c in bench if c]
            _log(
                f"\n--- Turn {turn} | Active: {a_name} HP={a_hp}/{a_max} "
                f"Energy={a_nrg} | Bench: {bench_names} | Hand: {len(hand)} ---"
            )
        else:
            _log(f"\n--- Turn {turn} | No active Pokemon | Bench: {len(bench)} | Hand: {len(hand)} ---")

        _log(f"  Choices ({len(options)}, pick {max_count}):")
        for i, opt in enumerate(options):
            _log(f"    [{i}] {format_option(opt, hand)}")

    chosen = random.sample(range(len(options)), min(max_count, len(options)))

    if _verbose:
        picked = [format_option(options[i], hand) for i in chosen]
        _log(f"  -> Picking: {', '.join(picked)}")

    return chosen
