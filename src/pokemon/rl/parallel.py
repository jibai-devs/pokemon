"""Parallel game collection across CPU cores (Speed A2).

Games are independent and the engine is CPU-bound and serial, so we run
`games_per_iter` across a persistent process pool. Each worker imports
`kaggle_environments` once (startup is heavy → reuse workers) and keeps a model
template; each task deserializes the current params, plays one game, and returns
its transitions. The main process aggregates into the replay buffer and does the
gradient updates, then broadcasts updated params the next iteration.

Use `spawn` (not fork) so workers start a clean interpreter — forking after JAX
is imported is unsafe. Per-worker thread caps (set in the parent env, inherited
by spawned children) avoid CPU oversubscription across `n_workers` JAX runtimes.
"""

from __future__ import annotations

import multiprocessing as mp
import os
from collections.abc import Callable

import flax.serialization as fser

# Worker-global state, populated by `_init_worker` once per process.
_W: dict = {}


def _resolve_opponent(name: str) -> Callable[[dict], list[int]]:
    from kaggle_environments.envs.cabt.cabt import random_agent

    if name == "random":
        return random_agent
    if name == "heuristic":
        from pokemon.agent import fire_agent

        return fire_agent
    raise ValueError(f"unknown opponent: {name!r}")


def _init_worker(hidden: tuple[int, ...], k_max: int) -> None:
    import jax

    from pokemon.rl import net
    from pokemon.rl.features import OPTION_DIM, STATE_DIM

    model = net.QNet(hidden=hidden)
    template = net.init_params(model, jax.random.PRNGKey(0), STATE_DIM, OPTION_DIM)
    _W["model"] = model
    _W["template"] = template
    _W["k_max"] = k_max


def _run_one(args: tuple[bytes, float, int, str, float]):
    import numpy as np

    from pokemon.rl import policy, rollout

    param_bytes, eps, seed, opponent_name, gamma = args
    params = fser.from_bytes(_W["template"], param_bytes)
    rng = np.random.default_rng(seed)
    act = policy.eps_act(_W["model"], params, eps, rng, _W["k_max"])
    opponent = _resolve_opponent(opponent_name)
    return rollout.play_game(act=act, opponent=opponent, gamma=gamma, seed=seed)


def _cap_worker_threads() -> None:
    """Limit per-worker BLAS/XLA threads so N workers don't oversubscribe cores.
    Set in the parent before spawning; children inherit at their JAX import."""
    for var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ.setdefault(var, "1")
    os.environ.setdefault("XLA_FLAGS", "--xla_cpu_multi_thread_eigen=false")


class RolloutPool:
    """Persistent process pool for parallel game collection.

    Create once and reuse across training iterations (worker startup is heavy).
    `collect` broadcasts the current params and gathers `n` games' transitions.
    """

    def __init__(self, hidden: tuple[int, ...], k_max: int, n_workers: int) -> None:
        _cap_worker_threads()
        ctx = mp.get_context("spawn")
        self.n_workers = n_workers
        self._pool = ctx.Pool(
            processes=n_workers, initializer=_init_worker, initargs=(hidden, k_max)
        )

    def collect(
        self,
        params,
        eps: float,
        n_games: int,
        opponent_name: str,
        seeds: list[int],
        gamma: float,
    ) -> list[tuple[list[dict], float]]:
        param_bytes = fser.to_bytes(params)
        tasks = [(param_bytes, eps, int(seeds[i]), opponent_name, gamma) for i in range(n_games)]
        return self._pool.map(_run_one, tasks)

    def close(self) -> None:
        self._pool.close()
        self._pool.join()

    def __enter__(self) -> RolloutPool:
        return self

    def __exit__(self, *exc) -> None:
        self.close()


def opponent_name(opponent) -> str:
    """Map an opponent callable/name to the string workers resolve by."""
    if isinstance(opponent, str):
        return opponent
    return "heuristic" if getattr(opponent, "__name__", "") == "fire_agent" else "random"
