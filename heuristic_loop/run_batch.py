"""Play a batch of games and save each one as a Kaggle-format replay JSON.

The point of this script over `pokemon play` (`src/pokemon/cli.py`) is
persistence: `cli.py play -v` prints a verbose trace to stdout and throws the
game away, which is fine for a human watching one game live but useless for
batch analysis. This script keeps `cli.py`'s win/loss loop but additionally
calls `env.toJSON()` after each game and writes it to disk in the same
`{"steps": [...], "rewards": [...], "info": {...}}` shape as a downloaded
Kaggle replay — so `scripts/analyze_heuristic_logs.py` (built against real
downloaded replays in PKM-019) can read locally-played games without any
format translation.

Usage:
    uv run python heuristic_loop/run_batch.py -g 20 -a heuristic -d dragapult
    uv run python heuristic_loop/run_batch.py -g 20 --losses-only
    uv run python heuristic_loop/run_batch.py -g 20 --out heuristic_loop/logs/my_batch
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import kaggle_environments as kaggle
from kaggle_environments.envs.cabt.cabt import random_agent

from pokemon import agent as agent_module
from pokemon import heuristics as heuristics_module
from pokemon.decks import ACTIVE_DECK_NAME, DECKS


def _resolve_deck(deck: str) -> list[int]:
    if deck not in DECKS:
        raise SystemExit(f"Unknown deck '{deck}'. Available: {', '.join(DECKS)}")
    return DECKS[deck]


def _build_agent(agent_name: str, cards: list[int], deck_name: str):
    if agent_name == "random":
        return agent_module.make_agent(cards), agent_module.set_game_num
    if agent_name == "heuristic":
        rules = heuristics_module.HEURISTIC_SETS.get(deck_name)
        return heuristics_module.make_heuristic_agent(cards, rules), heuristics_module.set_game_num
    raise SystemExit(f"Unknown agent '{agent_name}'. Available: random, heuristic")


def run_batch(
    games: int,
    agent_name: str,
    deck_name: str,
    out_dir: Path,
    losses_only: bool,
    opponent: str,
) -> dict:
    cards = _resolve_deck(deck_name)
    my_agent, set_game_num = _build_agent(agent_name, cards, deck_name)
    opponent_agent = random_agent

    out_dir.mkdir(parents=True, exist_ok=True)
    wins, losses, draws = 0, 0, 0
    saved_paths: list[str] = []

    for i in range(games):
        set_game_num(i + 1)
        env = kaggle.make("cabt", debug=True)
        env.reset()
        steps = env.run([my_agent, opponent_agent])

        final = steps[-1]
        reward = final[0].get("reward", 0)
        result = "win" if reward == 1 else "loss" if reward == -1 else "draw"
        if result == "win":
            wins += 1
        elif result == "loss":
            losses += 1
        else:
            draws += 1

        print(f"  Game {i + 1}/{games}: {result.upper()} ({len(steps)} steps)")

        if losses_only and result != "loss":
            continue

        data = env.toJSON()
        path = out_dir / f"game_{i + 1:03d}_{result}.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        saved_paths.append(str(path))

    summary = {
        "games": games,
        "agent": agent_name,
        "deck": deck_name,
        "opponent": opponent,
        "wins": wins,
        "losses": losses,
        "draws": draws,
        "win_rate": wins / games if games else 0.0,
        "saved_logs": saved_paths,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--games", "-g", type=int, default=20)
    parser.add_argument("--agent", "-a", default="heuristic", choices=["random", "heuristic"])
    parser.add_argument("--deck", "-d", default=ACTIVE_DECK_NAME, choices=list(DECKS))
    parser.add_argument("--opponent", default="random", choices=["random"])
    parser.add_argument(
        "--out",
        default=None,
        help="Output directory for saved replay JSONs (default: heuristic_loop/logs/<timestamp>)",
    )
    parser.add_argument(
        "--losses-only",
        action="store_true",
        help="Only persist replay JSON for games we lost (saves disk/time)",
    )
    args = parser.parse_args()

    out_dir = (
        Path(args.out)
        if args.out
        else Path(__file__).parent / "logs" / datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    )

    print(
        f"Playing {args.games} game(s): '{args.deck}' deck, '{args.agent}' agent vs '{args.opponent}'..."
    )
    summary = run_batch(args.games, args.agent, args.deck, out_dir, args.losses_only, args.opponent)

    print(f"\n=== RESULTS ({summary['games']} games) ===")
    print(f"Wins:   {summary['wins']} ({summary['win_rate'] * 100:.0f}%)")
    print(f"Losses: {summary['losses']}")
    print(f"Draws:  {summary['draws']}")
    print(f"Logs saved to: {out_dir}")


if __name__ == "__main__":
    main()
