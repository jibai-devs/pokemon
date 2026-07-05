"""Deck-agnostic analyzer for CABT Kaggle-format replay logs (PKM-019).

Built after two sessions of reading `data/recent_log.txt` by hand ran into
the same rough edges every time — the trigger condition PKM-019 named for
turning this from "read it manually" into a script.

Fixes two systemic issues that make raw replays unreliable to read by eye or
with `scripts/parse_replay.py` as-is:

1. **Off-by-one `selected` field.** In the Kaggle replay export, the option
   actually chosen for the decision shown at frame ``i`` is not stored on
   ``vis[i]["selected"]`` — it's stored on ``vis[i + 1]["selected"]``.
   Confirmed on a real 183-step replay: shifting by one recovers an
   in-range, valid selection for 182/183 decisions, vs. 151/183 reading the
   field unshifted (and those 151 are mostly coincidental overlap for
   small `maxCount=1` menus, not a real signal — e.g. a genuine 2-card
   Ciphermaniac's Codebreaking search showed `selected=[0]` on its own
   frame, a single-index answer to a 2-required select, while the *next*
   frame's `selected=[14, 27]` was invalid for *that* frame's own 5-option
   menu but exactly matched two Metagross cards in the search frame's
   46-option list).
2. **Area-blind option labels.** `catalog.format_option` always resolves an
   option's card via ``hand[index]``, regardless of the option's own
   ``area`` field — correct for hand-area options, wrong for bench/active/
   deck/discard/prize ones (see PKM-017 "Known cosmetic issue"). This module
   resolves any area, for either player, generically by card id — nothing
   here is specific to any particular Pokemon, deck, or matchup, so it reads
   the opponent's cards exactly as well as ours.

Output is a condensed, turn-grouped decision trace for one player (skips
full board-state JSON) plus an end-of-game summary: attacks used, evolves,
retreats, and what was actually picked in each search/discard context —
meant to be short enough to read directly instead of spelunking the raw
JSON with one-off scripts.

Usage:
    uv run python scripts/analyze_heuristic_logs.py data/recent_log.txt
    uv run python scripts/analyze_heuristic_logs.py data/recent_log.txt --player 1
    uv run python scripts/analyze_heuristic_logs.py data/recent_log.txt --summary-only
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pokemon.cabt_enums import AreaType
from pokemon.catalog import atk_name, card_name

_ZONE_LABELS = {
    AreaType.DECK: "deck",
    AreaType.HAND: "hand",
    AreaType.DISCARD: "discard",
    AreaType.ACTIVE: "active",
    AreaType.BENCH: "bench",
    AreaType.PRIZE: "prize",
    AreaType.LOOKING: "looking",
}


def _zone_cards(player: dict, area: int | None) -> list:
    if area == AreaType.HAND:
        return player.get("hand") or []
    if area == AreaType.BENCH:
        return player.get("bench") or []
    if area == AreaType.ACTIVE:
        return player.get("active") or []
    if area == AreaType.DISCARD:
        return player.get("discard") or []
    if area == AreaType.PRIZE:
        return [c for c in (player.get("prize") or []) if c]
    return []


def _board_card(players: list, player_idx: int | None, area: int | None, idx: int | None) -> dict | None:
    if player_idx is None or idx is None or not (0 <= player_idx < len(players)):
        return None
    cards = _zone_cards(players[player_idx], area)
    return cards[idx] if 0 <= idx < len(cards) else None


def _resolve_card_id(opt: dict, select: dict, players: list, active_idx: int) -> int | None:
    """Best-effort card id for any CARD-shaped option, any area, either player.

    `Play`/`Evolve` options omit `area` entirely — both always refer to a
    hand card, so a missing `area` defaults to HAND rather than resolving
    to nothing.
    """
    area = opt.get("area", AreaType.HAND)
    idx = opt.get("index")
    player_idx = opt.get("playerIndex", active_idx)

    if area in (AreaType.DECK, AreaType.LOOKING):
        deck = select.get("deck")
        if isinstance(deck, list) and idx is not None and 0 <= idx < len(deck):
            entry = deck[idx]
            if isinstance(entry, dict):
                return entry.get("id")
        context_card = select.get("contextCard")
        if isinstance(context_card, dict):
            return context_card.get("id")
        return None

    card = _board_card(players, player_idx, area, idx)
    return card.get("id") if card else None


def format_option(opt: dict, select: dict, players: list, active_idx: int) -> str:
    """Human-readable label for a Kaggle-format option, resolving any area
    for either player generically (fixes the hand-only assumption in
    ``catalog.format_option``)."""
    t = opt.get("type", "?")
    ctx = select.get("context", "")

    if t == "Attack":
        return f"ATTACK {atk_name(opt.get('attackId', 0))}"
    if t == "Retreat":
        return "RETREAT"
    if t == "End":
        return "END TURN"
    if t == "Ability":
        return "ABILITY"
    if t in ("Yes", "No"):
        return f"{t.upper()} ({ctx})"
    if t in ("Evolve", "Play"):
        cid = _resolve_card_id(opt, select, players, active_idx)
        return f"{t.upper()} {card_name(cid) if cid is not None else '?'}"
    if t == "Attach":
        cid = _resolve_card_id(opt, select, players, active_idx)
        target = _board_card(players, opt.get("playerIndex", active_idx), opt.get("inPlayArea"), opt.get("inPlayIndex"))
        target_name = card_name(target.get("id")) if target else "?"
        return f"ATTACH {card_name(cid) if cid is not None else '?'} -> {target_name}"
    if t == "Card":
        cid = _resolve_card_id(opt, select, players, active_idx)
        zone = _ZONE_LABELS.get(opt.get("area"), f"area={opt.get('area')}")
        return f"CARD[{ctx}] {card_name(cid) if cid is not None else '?'} ({zone})"

    return f"?{t}"


# ---------------------------------------------------------------------------
# Decision extraction (with the off-by-one `selected` fix)
# ---------------------------------------------------------------------------


def extract_decisions(vis: list, player: int | None) -> list[dict]:
    """One entry per real decision: frame i's select/options, answered by
    frame (i + 1)'s ``selected`` field — see module docstring for why."""
    decisions = []
    for i in range(len(vis) - 1):
        frame = vis[i]
        select = frame.get("select")
        if not select:
            continue
        current = frame.get("current") or {}
        active_idx = current.get("yourIndex", 0)
        if player is not None and active_idx != player:
            continue

        options = select.get("option") or []
        chosen = vis[i + 1].get("selected")
        valid = isinstance(chosen, list) and bool(chosen) and all(0 <= c < len(options) for c in chosen)

        decisions.append({
            "step_idx": i,
            "turn": current.get("turn"),
            "player": active_idx,
            "current": current,
            "select": select,
            "chosen": chosen if valid else None,
            "valid": valid,
        })
    return decisions


# ---------------------------------------------------------------------------
# Printing
# ---------------------------------------------------------------------------


def print_trace(decisions: list[dict], players_meta: list) -> None:
    last_turn = None
    for d in decisions:
        if d["turn"] != last_turn:
            print(f"\n--- Turn {d['turn']} ---")
            last_turn = d["turn"]

        select = d["select"]
        players = d["current"].get("players") or []
        active_idx = d["player"]
        options = select.get("option") or []
        ctx = select.get("context")

        if not d["valid"]:
            print(f"  [step {d['step_idx']}] ctx={ctx} -- unresolved selection (raw: {d['chosen']})")
            continue

        labels = [format_option(options[i], select, players, active_idx) for i in d["chosen"]]
        print(f"  [step {d['step_idx']}] ctx={ctx}: {', '.join(labels)}")


def print_summary(decisions: list[dict]) -> None:
    type_counts: Counter = Counter()
    attack_counts: Counter = Counter()
    pick_counts: dict[str, Counter] = {}
    n_unresolved = 0

    for d in decisions:
        if not d["valid"]:
            n_unresolved += 1
            continue
        select = d["select"]
        players = d["current"].get("players") or []
        active_idx = d["player"]
        options = select.get("option") or []
        ctx = select.get("context") or "?"

        for i in d["chosen"]:
            opt = options[i]
            t = opt.get("type", "?")
            type_counts[t] += 1
            if t == "Attack":
                attack_counts[atk_name(opt.get("attackId", 0))] += 1
            if t in ("Card", "Play", "Evolve", "Attach"):
                label = format_option(opt, select, players, active_idx)
                pick_counts.setdefault(ctx, Counter())[label] += 1

    print(f"\n{'=' * 72}")
    print(f"Decisions: {len(decisions)} | Unresolved: {n_unresolved}")
    print("\nOption-type breakdown (chosen, not just offered):")
    for t, n in type_counts.most_common():
        print(f"  {n:3d}x  {t}")
    if attack_counts:
        print("\nAttacks used:")
        for name, n in attack_counts.most_common():
            print(f"  {n:3d}x  {name}")
    else:
        print("\nAttacks used: none")
    print("\nPicks by select context:")
    for ctx, counter in sorted(pick_counts.items(), key=lambda kv: -sum(kv[1].values())):
        print(f"  {ctx}:")
        for label, n in counter.most_common(10):
            print(f"    {n:3d}x  {label}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("file", help="Path to a Kaggle-format replay JSON")
    parser.add_argument("--player", type=int, default=None, help="Restrict to one player index (0 or 1)")
    parser.add_argument("--summary-only", action="store_true", help="Skip the turn-by-turn trace")
    args = parser.parse_args()

    data = json.loads(Path(args.file).read_text(encoding="utf-8"))
    steps = data.get("steps", [])
    if not steps or not steps[0][0].get("visualize"):
        print("No visualize frames found — not a Kaggle-format replay?")
        return
    vis = steps[0][0]["visualize"]

    rewards = data.get("rewards", [])
    agents = [a.get("Name", f"P{i}") for i, a in enumerate(data.get("info", {}).get("Agents", []))]
    result = "unknown"
    if len(rewards) == 2 and agents:
        if rewards[0] == 1:
            result = f"{agents[0]} wins"
        elif rewards[1] == 1:
            result = f"{agents[1]} wins"
        else:
            result = "Draw"
    print(f"Result: {result} ({len(vis)} decision frames)")

    decisions = extract_decisions(vis, args.player)
    if not args.summary_only:
        print_trace(decisions, [])
    print_summary(decisions)


if __name__ == "__main__":
    main()
