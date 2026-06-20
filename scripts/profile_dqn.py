"""Profile where DQN training time goes: engine (libcg) vs our own code
(encode + Q-forward + transition assembly) vs gradient updates.

Run: ``uv run python scripts/profile_dqn.py [-n GAMES] [-u UPDATES] [-w WORKERS]``

The rollout breakdown is measured *inside real games* via `rollout.play_game`'s
`timers` hook (not by subtracting separately-timed phases), so the engine-vs-ours
split is accurate. See docs/002_dqn_next_steps.md Section A.
"""

from __future__ import annotations

import argparse
import time

import jax
import jax.numpy as jnp
import numpy as np
from kaggle_environments.envs.cabt.cabt import random_agent

from pokemon.rl import learner, net, policy, rollout
from pokemon.rl.config import DQNConfig
from pokemon.rl.features import OPTION_DIM, STATE_DIM
from pokemon.rl.replay import ReplayBuffer


def _collect_with_timers(model, params, n: int, seed: int) -> dict:
    """Play n games with the greedy policy, accumulating a per-phase wall-time
    breakdown via play_game's `timers` hook."""
    act = policy.greedy_act(model, params)
    timers: dict = {}
    # Warm the jitted scorer so its one-time compile isn't charged to game 1.
    rollout.play_game(act=act, opponent=random_agent, seed=seed, timers={})
    for g in range(n):
        rollout.play_game(act=act, opponent=random_agent, seed=seed + g, timers=timers)
    return timers


def _time_collection_parallel(model, params, n: int, seed: int, workers: int) -> float:
    """Parallel collection via the persistent worker pool (A2). Excludes the
    one-time pool spin-up; first .collect() pays per-worker JIT compile."""
    from pokemon.rl.parallel import RolloutPool

    cfg = DQNConfig()
    with RolloutPool(model.hidden, cfg.k_max, workers) as pool:
        seeds = [seed + g for g in range(n)]
        pool.collect(params, 0.0, n, "random", seeds, cfg.gamma)  # warmup compile
        start = time.perf_counter()
        pool.collect(params, 0.0, n, "random", seeds, cfg.gamma)
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
    ap.add_argument("-n", "--games", type=int, default=8, help="games for the rollout breakdown")
    ap.add_argument("-u", "--updates", type=int, default=100, help="gradient updates")
    ap.add_argument("-w", "--workers", type=int, default=0, help="also time parallel collection")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    cfg = DQNConfig()
    model = net.QNet(hidden=cfg.hidden)
    params = net.init_params(model, jax.random.PRNGKey(cfg.seed), STATE_DIM, OPTION_DIM)

    print(f"STATE_DIM={STATE_DIM}  OPTION_DIM={OPTION_DIM}")
    print(f"profiling: {args.games} games (rollout breakdown), {args.updates} updates\n")

    t = _collect_with_timers(model, params, args.games, args.seed)
    g = args.games
    # env.run contains both agent callbacks; engine/libcg = run minus ours minus opp.
    setup = t.get("setup", 0.0)
    run = t.get("run", 0.0)
    agent = t.get("agent", 0.0)
    opp = t.get("opponent", 0.0)
    post = t.get("post", 0.0)
    engine = run - agent - opp  # pure libcg + kaggle env loop (run minus our callbacks)
    ours = agent + post  # our code: encode + Q-forward + record + transitions
    total = setup + run + post  # = setup + engine + agent + opp + post

    def line(name: str, secs: float) -> str:
        return f"  {name:<26s}: {secs / g * 1e3:7.2f} ms/game | {secs / total:6.1%}"

    print(f"=== rollout breakdown ({g} games, opponent=random) ===")
    print(line("engine/libcg (env.run)", engine))
    print(line("engine setup (make+reset)", setup))
    print(line("opponent callback", opp))
    print(line("our agent (encode+Q+record)", agent))
    print(line("our post (transition asm)", post))
    print(f"  {'-' * 44}")
    print(line("TOTAL per game", total))
    print(
        f"\n  → engine (libcg+setup): {(engine + setup) / total:.1%}  |  "
        f"ours (agent+post): {ours / total:.1%}  |  opponent: {opp / total:.1%}"
    )

    upd = _time_updates(cfg, model, params, args.updates)
    upd_per = upd / args.updates
    col_per = total / g
    print(f"\nupdates ({args.updates}): {upd:.2f}s | {upd_per * 1e3:.2f} ms/update")

    if args.workers > 1:
        t_par = _time_collection_parallel(model, params, args.games, args.seed, args.workers)
        par_per = t_par / args.games
        print(
            f"parallel x{args.workers:<2d}: {t_par:.2f}s | {par_per * 1e3:.1f} ms/game | "
            f"{args.games / t_par:.1f} games/s | speedup {col_per / par_per:.1f}x vs serial"
        )

    # Modelled iteration: gi collection games + ui updates.
    gi, ui = 8, 100
    iter_collect = col_per * gi
    iter_updates = upd_per * ui
    it_total = iter_collect + iter_updates
    print(f"\nmodelled iteration ({gi} games + {ui} updates) = {it_total:.2f}s")
    print(f"  collection (rollouts) : {iter_collect / it_total:5.1%}")
    print(f"  updates               : {iter_updates / it_total:5.1%}")


if __name__ == "__main__":
    main()
