"""Typer CLI for the DQN: `pokemon-train smoke` (M0). Training lands in M1."""

from __future__ import annotations

import time

import jax
import numpy as np
import typer

from pokemon.rl import features, net, rollout
from pokemon.rl.config import DQNConfig

app = typer.Typer(no_args_is_help=True)


@app.callback()
def _main() -> None:
    """DQN training CLI for the Pokémon TCG agent."""


@app.command()
def smoke(
    games: int = typer.Option(5, "--games", "-g", help="Games to play"),
    seed: int = typer.Option(0, "--seed", help="Base RNG seed"),
):
    """Wire-check: play games, collect transitions, verify prize semantics + throughput."""
    cfg = DQNConfig()
    model = net.QNet(hidden=cfg.hidden)
    params = net.init_params(
        model, jax.random.PRNGKey(cfg.seed), features.STATE_DIM, features.OPTION_DIM
    )

    typer.echo(f"STATE_DIM={features.STATE_DIM}  OPTION_DIM={features.OPTION_DIM}")
    total_transitions = 0
    start = time.perf_counter()
    for g in range(games):
        transitions, terminal_reward = rollout.play_game(gamma=cfg.gamma, seed=seed + g)
        total_transitions += len(transitions)

        # Forward pass on the first decision proves the net runs on real features.
        t0 = transitions[0]
        q = net.q_values(model, params, t0["state"], t0["option"][None, :])
        assert np.all(np.isfinite(np.asarray(q))), "non-finite Q on real features"
        assert all(np.all(np.isfinite(tr["reward"])) for tr in transitions)

        result = {1.0: "WIN", -1.0: "LOSS"}.get(terminal_reward, "DRAW")
        typer.echo(
            f"  game {g + 1}: {result:4s}  decisions={len(transitions):3d}  "
            f"terminal_reward={terminal_reward:+.0f}"
        )

    elapsed = time.perf_counter() - start
    typer.echo(
        f"\n{games} games | {total_transitions} transitions | "
        f"{games / elapsed:.2f} games/sec | {elapsed:.1f}s"
    )
