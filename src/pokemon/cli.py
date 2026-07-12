"""Typer CLI: play a deck against the built-in random agent and watch it."""

import kaggle_environments as kaggle
import typer
from kaggle_environments.envs.cabt.cabt import random_agent

from pokemon import agent as agent_module
from pokemon import heuristics as heuristics_module
from pokemon.decks import ACTIVE_DECK_NAME, DECKS
from pokemon.types import Deck

app = typer.Typer()


def _resolve_deck(deck: str) -> Deck:
    if deck not in DECKS:
        typer.echo(f"Unknown deck '{deck}'. Available: {', '.join(DECKS)}")
        raise typer.Exit(1)
    return DECKS[deck]


@app.command()
def play(
    games: int = typer.Option(1, "--games", "-g", help="Number of games to play"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed game log"),
    deck: str = typer.Option(
        ACTIVE_DECK_NAME, "--deck", "-d", help=f"Deck to play ({', '.join(DECKS)})"
    ),
    agent: str = typer.Option(
        "random", "--agent", "-a", help="Agent to play with: random or heuristic"
    ),
) -> None:
    """Play a deck against the built-in random agent and watch it."""
    cards = _resolve_deck(deck)

    if agent == "random":
        my_agent = agent_module.make_agent(cards)
        agent_module.set_verbose(verbose)
        set_game_num = agent_module.set_game_num
    elif agent == "heuristic":
        rules = heuristics_module.HEURISTIC_SETS.get(deck)
        my_agent = heuristics_module.make_heuristic_agent(cards, rules)
        heuristics_module.set_verbose(verbose)
        set_game_num = heuristics_module.set_game_num
    else:
        typer.echo(f"Unknown agent '{agent}'. Available: random, heuristic")
        raise typer.Exit(1)

    if not verbose:
        typer.echo(f"Playing {games} game(s) with '{deck}' deck ('{agent}' agent)...")
        typer.echo()

    wins, losses, draws = 0, 0, 0
    total_steps = 0

    for i in range(games):
        set_game_num(i + 1)
        env = kaggle.make("cabt", debug=True)
        env.reset()
        steps = env.run([my_agent, random_agent])

        final = steps[-1]
        reward = final[0].get("reward", 0)
        result = "WIN" if reward == 1 else "LOSS" if reward == -1 else "DRAW"
        total_steps += len(steps)

        if reward == 1:
            wins += 1
        elif reward == -1:
            losses += 1
        else:
            draws += 1

        if verbose:
            typer.echo(f"\n{'=' * 60}")
            typer.echo(f"RESULT: {result} in {len(steps)} steps")
            typer.echo(f"{'=' * 60}")
        else:
            typer.echo(f"  Game {i + 1}: {result} ({len(steps)} steps)")

    typer.echo()
    typer.echo(f"=== RESULTS ({games} games) ===")
    typer.echo(f"Wins:   {wins} ({wins / games * 100:.0f}%)")
    typer.echo(f"Losses: {losses} ({losses / games * 100:.0f}%)")
    typer.echo(f"Draws:  {draws} ({draws / games * 100:.0f}%)")
    typer.echo(f"Avg game length: {total_steps / games:.0f} steps")


@app.command("export-deck")
def export_deck(
    deck: str = typer.Option(
        ACTIVE_DECK_NAME, "--deck", "-d", help=f"Deck to export ({', '.join(DECKS)})"
    ),
    out: str = typer.Option("deck.csv", "--out", "-o", help="Output CSV path"),
) -> None:
    """Write a deck's card ids to a CSV file (one id per line) for Kaggle submission."""
    cards = _resolve_deck(deck)
    with open(out, "w") as f:
        f.write("\n".join(map(str, cards)) + "\n")
    typer.echo(f"Wrote {len(cards)} cards from '{deck}' deck to {out}")
