"""DQN training loop: collect (epsilon-greedy) -> replay -> Double-DQN updates."""

from __future__ import annotations

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
    history: list[dict] = []

    for it in range(iterations):
        act = policy.eps_act(model, state.params, eps, rng)
        for _ in range(games_per_iter):
            transitions, _ = rollout.play_game(
                act=act, opponent=opponent, gamma=cfg.gamma, seed=int(rng.integers(1_000_000_000))
            )
            for t in transitions:
                buf.add(
                    t["state"], t["option"], t["reward"], t["next_state"], t["next_options"], t["done"]
                )
            eps = max(cfg.eps_end, eps - eps_decay * len(transitions))

        if buf.size >= cfg.batch_size:
            for _ in range(updates_per_iter):
                batch = buf.sample(cfg.batch_size, rng)
                jbatch = {k: jnp.asarray(v) for k, v in batch.items()}
                state, loss = update_step(state, target_params, jbatch)
                step += 1
                last_loss = float(loss)
                if step % cfg.target_update_interval == 0:
                    target_params = state.params

        if (it + 1) % eval_every == 0:
            winrate = ev.evaluate(
                policy.greedy_act(model, state.params), opponent=opponent, n_games=eval_games, seed=seed
            )
            checkpoint.save_params(f"{ckpt_dir}/params.msgpack", state.params)
            history.append(
                {"iter": it + 1, "step": step, "eps": round(eps, 3), "loss": last_loss, "winrate": winrate}
            )
            print(
                f"iter {it + 1:4d} | step {step:6d} | eps {eps:.3f} | "
                f"loss {last_loss:.4f} | winrate {winrate:.2%}"
            )

    return state, history
