"""Typer CLI for the DQN: `pokemon-train smoke` (M0). Training and eval land in M1."""

from __future__ import annotations

import dataclasses
import glob
import os
import time

import jax
import numpy as np
import typer

from pokemon.rl import checkpoint, features, net, policy, rollout
from pokemon.rl import eval as ev
from pokemon.rl import train as train_mod
from pokemon.rl.config import DQNConfig
from pokemon.rl.features import OPTION_DIM, STATE_DIM

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


@app.command()
def train(
    iterations: int = typer.Option(200, "--iterations", "-n"),
    games_per_iter: int = typer.Option(8, "--games-per-iter"),
    updates_per_iter: int = typer.Option(64, "--updates-per-iter"),
    eval_every: int = typer.Option(10, "--eval-every"),
    eval_games: int = typer.Option(50, "--eval-games"),
    ckpt_dir: str = typer.Option("data/checkpoints", "--ckpt-dir"),
    seed: int = typer.Option(0, "--seed"),
    lr: float = typer.Option(1e-3, "--lr"),
    eps_decay_steps: int = typer.Option(40000, "--eps-decay-steps"),
    workers: int = typer.Option(1, "--workers", help="Parallel rollout workers (1 = serial)"),
    opponent: str = typer.Option("random", "--opponent", help="random | heuristic"),
):
    """Train the DQN; parallel rollouts via --workers, choose foe via --opponent."""
    from pokemon.rl.parallel import _resolve_opponent

    cfg = dataclasses.replace(DQNConfig(), lr=lr, eps_decay_steps=eps_decay_steps)
    _, history = train_mod.train(
        cfg,
        iterations=iterations,
        games_per_iter=games_per_iter,
        updates_per_iter=updates_per_iter,
        eval_every=eval_every,
        eval_games=eval_games,
        ckpt_dir=ckpt_dir,
        opponent=_resolve_opponent(opponent),
        workers=workers,
        seed=seed,
    )
    if history:
        best = max(history, key=lambda h: h["winrate"])
        typer.echo(f"best win-rate {best['winrate']:.2%} at iter {best['iter']}")


def _resolve_ckpt(path: str) -> str:
    """Resolve a checkpoint file from a file OR a directory.

    If given a directory, prefer its ``best.msgpack``; else the newest
    ``run-*/best.msgpack`` inside it; else a legacy ``params.msgpack``.
    """
    if os.path.isfile(path):
        return path
    direct = os.path.join(path, "best.msgpack")
    if os.path.isfile(direct):
        return direct
    runs = sorted(glob.glob(os.path.join(path, "run-*", "best.msgpack")))
    if runs:
        return runs[-1]
    legacy = os.path.join(path, "params.msgpack")
    if os.path.isfile(legacy):
        return legacy
    return path  # let load fail with a clear FileNotFoundError


@app.command()
def eval(
    ckpt: str = typer.Option("data/checkpoints", "--ckpt"),
    games: int = typer.Option(100, "--games", "-g"),
    seed: int = typer.Option(0, "--seed"),
):
    """Evaluate a saved checkpoint (greedy) vs random_agent.

    --ckpt accepts a file, a run dir, or data/checkpoints (uses the newest run's best).
    """
    resolved = _resolve_ckpt(ckpt)
    typer.echo(f"loading checkpoint: {resolved}")
    model = net.QNet(hidden=DQNConfig().hidden)
    template = net.init_params(model, jax.random.PRNGKey(0), STATE_DIM, OPTION_DIM)
    params = checkpoint.load_params(template, resolved)
    winrate = ev.evaluate(policy.greedy_act(model, params), n_games=games, seed=seed)
    typer.echo(f"win-rate vs random over {games} games: {winrate:.2%}")
