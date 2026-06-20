"""Profile where DQN training time goes: engine rollouts vs our collection
overhead (encode + policy forward) vs gradient updates.

Run: ``uv run python scripts/profile_dqn.py [-n GAMES] [-u UPDATES]``

Prints per-unit timings and the % share of an iteration (engine / our overhead /
updates) so we can see what to optimize. See docs/002_dqn_next_steps.md Section A.
"""

from __future__ import annotations

import argparse
import time

import jax
import jax.numpy as jnp
import kaggle_environments as kaggle
import numpy as np
from kaggle_environments.envs.cabt.cabt import random_agent

from pokemon.rl import learner, net, policy, rollout
from pokemon.rl.config import DQNConfig
from pokemon.rl.features import OPTION_DIM, STATE_DIM
from pokemon.rl.replay import ReplayBuffer


def _time_pure_engine(n: int, seed: int) -> float:
    """Two built-in random_agents — engine cost with no Python policy of ours."""
    start = time.perf_counter()
    for _ in range(n):
        env = kaggle.make("cabt", debug=True)
        env.reset()
        env.run([random_agent, random_agent])
    return time.perf_counter() - start


def _time_collection(model, params, n: int, seed: int) -> float:
    """Our full collection path: encode + (un-jitted) net forward + transitions."""
    act = policy.greedy_act(model, params)
    start = time.perf_counter()
    for g in range(n):
        rollout.play_game(act=act, opponent=random_agent, seed=seed + g)
    return time.perf_counter() - start


def _time_updates(cfg: DQNConfig, model, params, n_updates: int) -> float:
    """Jitted Double-DQN update steps after warmup (excludes compile time)."""
    rng = np.random.default_rng(0)
    buf = ReplayBuffer(cfg.replay_capacity, STATE_DIM, OPTION_DIM, cfg.k_max)
    # Seed the buffer with synthetic transitions so we can sample batches.
    for _ in range(cfg.batch_size * 4):
        k = int(rng.integers(1, cfg.k_max))
        nopt = rng.standard_normal((k, OPTION_DIM)).astype(np.float32)
        buf.add(
            rng.standard_normal(STATE_DIM).astype(np.float32),
            rng.standard_normal(OPTION_DIM).astype(np.float32),
            float(rng.standard_normal()),
            rng.standard_normal(STATE_DIM).astype(np.float32),
            nopt,
            bool(rng.integers(0, 2)),
        )
    state = learner.create_train_state(model, params, cfg.lr)
    target_params = state.params
    update_step = learner.make_update_step(model, cfg.gamma)

    def one() -> None:
        batch = buf.sample(cfg.batch_size, rng)
        jbatch = {k: jnp.asarray(v) for k, v in batch.items()}
        nonlocal state, target_params
        state, loss = update_step(state, target_params, jbatch)
        target_params = learner.soft_update(target_params, state.params, cfg.tau)
        jax.block_until_ready(loss)

    one()  # warmup / compile
    start = time.perf_counter()
    for _ in range(n_updates):
        one()
    return time.perf_counter() - start


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", "--games", type=int, default=8, help="games per phase")
    ap.add_argument("-u", "--updates", type=int, default=100, help="gradient updates")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    cfg = DQNConfig()
    model = net.QNet(hidden=cfg.hidden)
    params = net.init_params(model, jax.random.PRNGKey(cfg.seed), STATE_DIM, OPTION_DIM)

    print(f"STATE_DIM={STATE_DIM}  OPTION_DIM={OPTION_DIM}")
    print(f"profiling: {args.games} games (engine + collection), {args.updates} updates\n")

    t_engine = _time_pure_engine(args.games, args.seed)
    t_collect = _time_collection(model, params, args.games, args.seed)
    t_updates = _time_updates(cfg, model, params, args.updates)

    eng_per = t_engine / args.games
    col_per = t_collect / args.games
    upd_per = t_updates / args.updates
    overhead_per = col_per - eng_per  # our encode + forward, on top of engine

    print(
        f"pure engine    : {t_engine:6.2f}s  | {eng_per * 1e3:7.1f} ms/game | {args.games / t_engine:5.2f} games/s"
    )
    print(
        f"our collection : {t_collect:6.2f}s  | {col_per * 1e3:7.1f} ms/game | {args.games / t_collect:5.2f} games/s"
    )
    # After A1 (jitted scorer) our overhead is ~0, so collection ≈ engine and this
    # subtraction can go slightly negative from run-to-run engine variance.
    print(f"  └ our overhead (encode+forward, ≈0 after A1): {overhead_per * 1e3:7.1f} ms/game")
    print(f"updates ({args.updates})    : {t_updates:6.2f}s  | {upd_per * 1e3:7.1f} ms/update")

    # Iteration model: an iteration spends `g` collection games + `u` updates.
    # Base the split on measured collection (the real training cost) — not on the
    # fragile engine/overhead subtraction. Engine is reported as the rollout floor
    # that parallel workers (A2) can divide down toward.
    g, u = 8, 100
    iter_collect = col_per * g
    iter_updates = upd_per * u
    total = iter_collect + iter_updates
    print(f"\nmodelled iteration ({g} games + {u} updates) = {total:.2f}s")
    print(
        f"  collection (rollouts) : {iter_collect / total:5.1%}  (engine floor ≈ {eng_per * g / total:5.1%})"
    )
    print(f"  updates               : {iter_updates / total:5.1%}")


if __name__ == "__main__":
    main()
