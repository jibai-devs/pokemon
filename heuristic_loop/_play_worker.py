"""Internal worker for eval_heuristic_change.py — not meant to be run directly.

Plays N games with `pokemon` imported from a given `src/` directory and
prints a one-line JSON summary to stdout. Isolated into its own process
because comparing two versions of the heuristics code in a single Python
process would collide on Python's module cache (`pokemon.admin`,
`pokemon.heuristics.dragapult`, etc.) — subprocess per version sidesteps
that entirely.
"""

from __future__ import annotations

import argparse
import json
import sys


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--src-dir", required=True)
    parser.add_argument("--games", type=int, required=True)
    parser.add_argument("--deck", required=True)
    parser.add_argument("--agent", required=True, choices=["random", "heuristic"])
    parser.add_argument("--opponent", default="random", choices=["random"])
    args = parser.parse_args()

    sys.path.insert(0, args.src_dir)

    import kaggle_environments as kaggle
    from kaggle_environments.envs.cabt.cabt import random_agent

    from pokemon import admin as admin_module
    from pokemon import agent as agent_module
    from pokemon.decks import DECKS

    cards = DECKS[args.deck]
    if args.agent == "random":
        my_agent = agent_module.make_agent(cards)
        set_game_num = agent_module.set_game_num
    else:
        my_agent = admin_module.build_agent(cards, args.deck)
        set_game_num = admin_module.set_game_num

    wins = losses = draws = 0
    for i in range(args.games):
        set_game_num(i + 1)
        env = kaggle.make("cabt", debug=True)
        env.reset()
        steps = env.run([my_agent, random_agent])
        reward = steps[-1][0].get("reward", 0)
        if reward == 1:
            wins += 1
        elif reward == -1:
            losses += 1
        else:
            draws += 1

    print(json.dumps({"games": args.games, "wins": wins, "losses": losses, "draws": draws}))


if __name__ == "__main__":
    main()
