"""DQN training loop: collect (epsilon-greedy) -> replay -> Double-DQN updates."""

from __future__ import annotations

import os
import time

import jax
import jax.numpy as jnp
import numpy as np
from kaggle_environments.envs.cabt.cabt import random_agent

from pokemon.rl import checkpoint, learner, net, policy, rollout
from pokemon.rl import eval as ev
from pokemon.rl.config import DQNConfig
from pokemon.rl.features import OPTION_DIM, STATE_DIM
from pokemon.rl.replay import ReplayBuffer


def train(
    cfg: DQNConfig,
    iterations: int = 200,
    games_per_iter: int = 8,
    updates_per_iter: int = 64,
    eval_every: int = 10,
    eval_games: int = 50,
    ckpt_dir: str = "data/checkpoints",
    opponent=random_agent,
    seed: int = 0,
):
    # Each run gets its own subdir so a new run never clobbers a previous run's
    # best checkpoint. `best.msgpack` = best-by-eval; `last.msgpack` = latest
    # (also written on Ctrl-C so an interrupted run is never lost).
    run_dir = os.path.join(ckpt_dir, time.strftime("run-%Y%m%d-%H%M%S"))
    best_path = os.path.join(run_dir, "best.msgpack")
    last_path = os.path.join(run_dir, "last.msgpack")

    rng = np.random.default_rng(seed)
    model = net.QNet(hidden=cfg.hidden)
    params = net.init_params(model, jax.random.PRNGKey(cfg.seed), STATE_DIM, OPTION_DIM)
    state = learner.create_train_state(model, params, cfg.lr)
    target_params = state.params
    buf = ReplayBuffer(cfg.replay_capacity, STATE_DIM, OPTION_DIM, cfg.k_max)
    update_step = learner.make_update_step(model, cfg.gamma)

    eps = cfg.eps_start
    eps_decay = (cfg.eps_start - cfg.eps_end) / max(cfg.eps_decay_steps, 1)
    step = 0
    last_loss = float("nan")
    best_winrate = -1.0
    history: list[dict] = []

    try:
        for it in range(iterations):
            act = policy.eps_act(model, state.params, eps, rng)
            for _ in range(games_per_iter):
                transitions, _ = rollout.play_game(
                    act=act,
                    opponent=opponent,
                    gamma=cfg.gamma,
                    seed=int(rng.integers(1_000_000_000)),
                )
                for t in transitions:
                    buf.add(
                        t["state"],
                        t["option"],
                        t["reward"],
                        t["next_state"],
                        t["next_options"],
                        t["done"],
                    )
                eps = max(cfg.eps_end, eps - eps_decay * len(transitions))

            if buf.size >= cfg.batch_size:
                for _ in range(updates_per_iter):
                    batch = buf.sample(cfg.batch_size, rng)
                    jbatch = {k: jnp.asarray(v) for k, v in batch.items()}
                    state, loss = update_step(state, target_params, jbatch)
                    target_params = learner.soft_update(target_params, state.params, cfg.tau)
                    step += 1
                    last_loss = float(loss)

            if (it + 1) % eval_every == 0:
                winrate = ev.evaluate(
                    policy.greedy_act(model, state.params),
                    opponent=opponent,
                    n_games=eval_games,
                    seed=seed,
                )
                checkpoint.save_params(last_path, state.params)  # always keep the latest
                saved = ""
                if winrate > best_winrate:  # and the best-by-eval separately
                    best_winrate = winrate
                    checkpoint.save_params(best_path, state.params)
                    saved = " (saved best)"
                history.append(
                    {
                        "iter": it + 1,
                        "step": step,
                        "eps": round(eps, 3),
                        "loss": last_loss,
                        "winrate": winrate,
                        "best": best_winrate,
                    }
                )
                print(
                    f"iter {it + 1:4d} | step {step:6d} | eps {eps:.3f} | "
                    f"loss {last_loss:.4f} | winrate {winrate:.2%} | best {best_winrate:.2%}{saved}"
                )
    except KeyboardInterrupt:
        checkpoint.save_params(last_path, state.params)
        print(f"\n[interrupted] latest params saved to {last_path}")

    print(f"\nrun dir: {run_dir}")
    if best_winrate >= 0:
        print(f"best win-rate {best_winrate:.2%}  ->  {best_path}")
        print(f"evaluate:  uv run pokemon-train eval --ckpt {best_path} -g 200 --seed 9000")
    return state, history
