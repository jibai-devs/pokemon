"""Typer CLI: play a deck against the built-in random agent and watch it."""

import kaggle_environments as kaggle
import typer
from kaggle_environments.envs.cabt.cabt import random_agent

from pokemon import agent

app = typer.Typer()


@app.command()
def play(
    games: int = typer.Option(1, "--games", "-g", help="Number of games to play"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed game log"),
    deck: str = typer.Option("psychic", "--deck", "-d", help="Deck to play: psychic, fire"),
):
    """Play a deck against a random agent."""
    agent.set_verbose(verbose)

    agent_fn = {
        "psychic": agent.psychic_agent,
        "fire": agent.fire_agent,
    }.get(deck, agent.psychic_agent)

    if not verbose:
        typer.echo(f"Playing {games} game(s) with {deck} deck...")
        typer.echo()

    wins, losses, draws = 0, 0, 0
    total_steps = 0

    for i in range(games):
        agent.set_game_num(i + 1)
        env = kaggle.make("cabt", debug=True)
        env.reset()
        steps = env.run([agent_fn, random_agent])

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
