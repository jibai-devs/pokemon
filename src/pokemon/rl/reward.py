"""Potential-based prize shaping.

The win clock is the length of a player's ``prize`` list (6 -> 0; 0 = that
player has taken all their prizes and won). We shape with the policy-invariant
potential ``phi(s) = opp_prizes_remaining - my_prizes_remaining`` so taking a
prize (my pile shrinks) yields a positive step reward, plus a terminal +/-1.
"""

from __future__ import annotations


def prizes_remaining(obs: dict, player_index: int) -> int:
    players = (obs.get("current") or {}).get("players") or []
    if 0 <= player_index < len(players) and players[player_index]:
        return len(players[player_index].get("prize") or [])
    return 0


def potential(obs: dict) -> float:
    cur = obs.get("current") or {}
    my = cur.get("yourIndex", 0)
    return float(prizes_remaining(obs, 1 - my) - prizes_remaining(obs, my))


def shaped_reward(
    obs: dict, next_obs: dict | None, gamma: float, terminal_reward: float = 0.0
) -> float:
    phi = potential(obs)
    phi_next = 0.0 if next_obs is None else potential(next_obs)
    return gamma * phi_next - phi + terminal_reward
