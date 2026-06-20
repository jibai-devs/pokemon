# DQN usage — how to run, train, and evaluate the agent

Practical cheat-sheet for the `pokemon-train` CLI (the deep Q-learning agent in
`src/pokemon/rl/`). For *what's been built and why*, see `docs/001_dqn_progress.md`.

Everything runs through `uv run` (the project's venv). All commands are CPU-only
here, so the engine games are the slow part — but `--workers N` now runs rollouts
across cores (~8.5× with 16 workers; combined with the jitted scorer, collection
is ~23× faster than the original single-thread path).

> **Heads-up:** every command first prints ~30 `open_spiel ... INFO` lines and an
> `NVIDIA GPU ... falling back to cpu` notice. That's `kaggle_environments`
> chatter — harmless, ignore it. The real output comes after.

---

## The three commands

```
pokemon-train smoke   # sanity check: play games, collect data, print throughput (no learning)
pokemon-train train   # train the DQN vs random_agent; saves the best checkpoint
pokemon-train eval    # measure a saved checkpoint's win-rate vs random_agent
```

See flags for any command with `--help`, e.g. `uv run pokemon-train train --help`.

---

## 1. `smoke` — quick wire-check (seconds)

Plays a few games with a *random* policy and confirms the pipeline runs. Use it
to verify the code works after changes — it does **not** train.

```bash
uv run pokemon-train smoke -g 5
```

| Flag | Default | Meaning |
|------|---------|---------|
| `-g`, `--games` | 5 | how many games to play |
| `--seed` | 0 | RNG seed |

Output: `STATE_DIM`/`OPTION_DIM`, a WIN/LOSS line per game, and `games/sec`.

---

## 2. `train` — train the agent (minutes → tens of minutes)

Trains the DQN against `random_agent`: it repeatedly **collects** games
(ε-greedy), stores them in a replay buffer, runs **gradient updates**, and every
`--eval-every` iterations **evaluates greedily** and saves the checkpoint **only
when the win-rate improves** (best-by-eval).

```bash
# quick look (a couple minutes)
uv run pokemon-train train -n 20 --eval-every 5 --eval-games 20

# a real run (what we use; much faster now with parallel rollouts)
uv run pokemon-train train -n 250 --games-per-iter 16 --updates-per-iter 100 \
  --eval-every 10 --eval-games 100 --eps-decay-steps 30000 --workers 16 \
  --ckpt-dir data/checkpoints
```

| Flag | Default | Meaning |
|------|---------|---------|
| `-n`, `--iterations` | 200 | training iterations (one iter = collect games + do updates) |
| `--games-per-iter` | 8 | games collected per iteration (more data, slower) |
| `--updates-per-iter` | 64 | gradient steps per iteration (more learning per game) |
| `--eval-every` | 10 | evaluate + maybe-save every N iterations |
| `--eval-games` | 50 | games per evaluation (more = less noisy win-rate; ≥50 recommended) |
| `--ckpt-dir` | `data/checkpoints` | parent dir; each run writes its own `run-<timestamp>/` with `best.msgpack` (best-by-eval) + `last.msgpack` (latest, also on Ctrl-C) |
| `--seed` | 0 | RNG seed |
| `--lr` | 0.001 | Adam learning rate |
| `--eps-decay-steps` | 40000 | transitions over which exploration ε anneals 1.0 → 0.05 (lower = greedier sooner) |
| `--workers` | 1 | parallel rollout worker processes (1 = serial). Set to ~your core count; collection scales ~8.5× at 16 workers |
| `--opponent` | random | `random` (vs `random_agent`) or `heuristic` (vs `fire_agent` — the real M3 target) |

### Reading the output

Each eval prints a line like:
```
iter  110 | step  11000 | eps 0.182 | loss 0.0201 | winrate 80.00% | best 80.00% (saved best)
```
- **iter / step** — training progress (step = total gradient updates).
- **eps** — current exploration rate (1.0 = all random, 0.05 = mostly greedy). It
  should fall to 0.05 by roughly `eps_decay_steps / (games_per_iter × ~30)` iters.
- **loss** — DQN training loss (should be small/stable, not exploding).
- **winrate** — greedy win-rate of *this* iteration vs random (noisy — that's why
  we save best, not last).
- **best / (saved best)** — best win-rate so far; the checkpoint is overwritten
  only when this improves. `run-<timestamp>/best.msgpack` is always the best-so-far
  model for that run; **a new run never clobbers a previous run's best** (each run
  is its own subdir). Ctrl-C is safe — `last.msgpack` is written on interrupt. The
  end of training prints the exact `eval` command with the path.

---

## 3. `eval` — measure a saved checkpoint (minute or two)

Loads a checkpoint and reports its greedy win-rate vs `random_agent`. Use a large
`-g` to get a trustworthy number (30 games is ±18%; 200 games is ±~6%).

```bash
# --ckpt accepts a file, a run dir, or data/checkpoints (uses the newest run's best):
uv run pokemon-train eval --ckpt data/checkpoints -g 200
```

| Flag | Default | Meaning |
|------|---------|---------|
| `--ckpt` | `data/checkpoints` | file, run dir, or parent dir (auto-resolves to newest `run-*/best.msgpack`) |
| `-g`, `--games` | 100 | games to evaluate over |
| `--seed` | 0 | RNG seed (use a *different* seed than training to avoid lucky overlap) |

---

## Typical workflow

```bash
# 1. sanity check the pipeline
uv run pokemon-train smoke -g 5

# 2. train (writes best to data/checkpoints/run-<timestamp>/best.msgpack; prints the eval cmd)
uv run pokemon-train train -n 250 --eval-games 50 --eps-decay-steps 30000

# 3. measure the trained agent honestly over many games
uv run pokemon-train eval --ckpt data/checkpoints -g 200 --seed 9000   # newest run's best

# compare against the hand-coded baseline any time:
uv run pokemon-play -g 50          # heuristic fire_agent vs random (~74%)
```

---

## Tips

- **Long runs:** training is CPU-bound, so use `--workers N` (≈ your core count)
  to parallelize rollouts. For a long run, append ` | tee data/checkpoints/run.log`
  to keep the win-rate curve, and run it in the background (`tmux`, etc.).
  `data/checkpoints/` is gitignored.
- **Profiling speed:** `uv run python scripts/profile_dqn.py -n 16 -u 50 -w 16`
  reports engine vs collection vs update timings and parallel speedup.
- **Run a command yourself in this chat:** prefix with `!`, e.g.
  `! uv run pokemon-train eval -g 50` — the output lands in the conversation.
- **Reproducibility:** same `--seed` + same flags → same run. Change `--seed` for
  the eval so you measure on different games than you trained/selected on.
- **Checkpoints are deck-specific & dim-specific.** A checkpoint trained with one
  `OPTION_DIM` (feature set) can't load after the features change — re-train. The
  current feature set is `STATE_DIM=126`, `OPTION_DIM=127`.
- **What "good" looks like:** random-policy baseline ≈ 30% vs `random_agent`; the
  heuristic ≈ 74%. A trained DQN should beat 30% clearly; the goal is to approach
  and pass the heuristic (that's the M3 target, vs the heuristic directly).
