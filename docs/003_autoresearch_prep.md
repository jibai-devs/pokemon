# 003 — Autoresearch prep (hyperparameter sweep handoff)

**Point the next session here to run the autoresearch loop.** This doc defines the
goal, the metric, the search space, the budget, and the exact prompt to launch the
`autoresearch` skill. Speed (A1+A2) and the option-feature fix are already done, so
the loop is now practical (a trial is minutes, not 15–20 min).

- **Branch:** `feat/dqn-agent` (pushed to `origin`)
- **Read first:** `docs/002_dqn_next_steps.md` (§A2.5 = the audit/fix), `docs/001_dqn_progress.md` (results), `docs/dqn_usage.md` (CLI).
- **Skill:** `autoresearch` (autonomous experiment loop: define goal → metric → scope → iterate, keep/discard by metric).

---

## 0. DO THIS FIRST — re-baseline (one run, before any sweep)

The option-collision fix (`OPTION_DIM` 90→127, collisions 44%→0.04%) likely changed
everything. Old checkpoints are incompatible. Get the **post-fix baseline number**
so the sweep has something to beat and so we know whether features (not
hyperparameters) are still the limiter.

```bash
uv run pokemon-train train -n 250 --games-per-iter 16 --updates-per-iter 100 \
  --eval-every 10 --eval-games 100 --eps-decay-steps 30000 --workers 16 \
  --ckpt-dir data/checkpoints | tee data/checkpoints/run.log
uv run pokemon-train eval --ckpt data/checkpoints -g 200 --seed 9000
```

**Record the result here before sweeping:** `vs random (post-fix, 200g) = ____%`
(baselines: random-policy ≈ 30%, heuristic ≈ 74%; old pre-fix DQN ceiling ≈ 54%).

- If it now clearly clears ~54% and trends toward 70%+ vs random → representation
  fix worked; autoresearch is worth it.
- If still stuck ~50–55% → the limiter is **state features** (no Pokémon identity in
  `encode_state`), not hyperparameters. Fix that *before* sweeping (cheaper win than
  any HP search). See §5.

---

## 1. Goal & metric (what autoresearch optimizes)

**Metric (single scalar, maximize):** greedy win-rate of the trained DQN vs the
opponent, measured over **≥200 eval games averaged across 2–3 seeds** (use eval
seeds disjoint from training, e.g. 9000/9001/9002).

Why this exactly: win-rate is the only thing we care about; **noise is the enemy of
a hill-climber.** 30-game eval is ±18%, 100 is ±9%, 200 is ±6%; averaging 2–3 seeds
on top gets the metric trustworthy enough that the loop optimizes signal, not lucky
seeds. Cheap now that rollouts are parallel.

**Opponent schedule:**
1. **`random` first** — sanity that the agent can exceed ~60–70% on the weak deck.
2. **`heuristic` (`fire_agent`)** — the real M3 target: greedy win-rate **>50%
   (≥55%)** over ≥200 games. `--opponent heuristic` is already wired.

Run the sweep against `random` first; once a config reliably beats ~70% vs random,
switch the metric's opponent to `heuristic` and sweep again (the fire mirror).

---

## 2. Search space

Tier-1 (already CLI-exposed — sweep immediately): `--lr`, `--eps-decay-steps`,
`--updates-per-iter`, `--games-per-iter`.

Tier-2 (in `DQNConfig` but **not** yet CLI/sweepable — add flags or drive
`train_mod.train(cfg=...)` directly): `tau` (Polyak), `gamma`, `hidden` (net size),
`batch_size`, `replay_capacity`.

Suggested ranges / values:

| Knob | Range / set | Notes |
|---|---|---|
| `lr` | {3e-4, 1e-4, 5e-4, 1e-3} | 1e-3 diverged before; 3e-4/1e-4 safer |
| `tau` | {0.005, 0.01, 0.02} | Polyak target rate |
| `gamma` | {0.97, 0.99, 0.995} | horizon |
| `updates_per_iter` | {50, 100, 200} | learning per game |
| `eps_decay_steps` | {20k, 30k, 50k} | exploration anneal |
| `hidden` | {(128,128), (256,256), (256,256,256)} | **ablation also answers "is the net too big/small"** — include a tiny net |
| `batch_size` | {128, 256} | |
| EMA (see §4) | {off, decay 0.99, 0.999} | likely a big stability win |

Keep `--workers 16` (or core count) for every trial — it's a speed knob, not a HP.

---

## 3. Budget & keep/discard

- **Per trial:** 250 iters (or 150 for a faster first pass) → eval 200g × 2–3 seeds.
  ≈ 5–7 min/trial at 16 workers.
- **Total:** target ~30–40 trials (~3–4 h). Start with a coarse pass over tier-1 +
  EMA + net size, then refine around the best.
- **Keep/discard:** keep a config only if its averaged metric beats the current best
  by more than the metric's noise band (≈ ±5–6% at 200g×3 seeds). Log every trial's
  config + metric to a results file (e.g. `data/autoresearch/results.jsonl`).
- **Always-green:** `just check` must stay green; never commit a sweep artifact dir
  (`data/` is gitignored).

---

## 4. Recommended prep (small code, do before/at sweep start)

1. **EMA of weights** (~15 lines in `learner.py`/`train.py`): keep an exponential
   moving average of the online params, **evaluate/checkpoint the EMA** not the raw
   net. Fold `ema_decay ∈ {off, 0.99, 0.999}` into the search. This is the most
   likely single stability win (kills the 20%↔80% argmax churn).
2. **Averaged-seed eval helper**: a function that evals a checkpoint/params over
   `seeds=[9000,9001,9002]` and returns the mean — the metric autoresearch reads.
3. **Expose tier-2 knobs**: add `--tau --gamma --hidden --batch-size` to
   `pokemon-train train`, OR have the autoresearch driver call
   `train_mod.train(dataclasses.replace(DQNConfig(), ...))` directly (cleaner for a
   programmatic loop). Prefer the direct-call driver.

A clean driver shape for the loop:
```python
# pseudo: one trial
cfg = dataclasses.replace(DQNConfig(), lr=lr, tau=tau, gamma=gamma, hidden=hidden, batch_size=bs)
state, _ = train_mod.train(cfg, iterations=250, games_per_iter=16,
                           updates_per_iter=upd, eval_every=999,  # skip mid-eval
                           workers=16, opponent=opp, ckpt_dir=tmp)
metric = mean(evaluate(greedy_act(model, ema_or_state.params), opponent=opp,
                       n_games=200, seed=s) for s in (9000, 9001, 9002))
```

---

## 5. If the metric stalls — it's features, not hyperparameters

The `encode_state` Pokémon features are still thin: per Pokémon only hp-ratio +
energy-count + presence, **no card identity / attack info** for the active/bench
mons. The option encoder is now rich (post-fix) but the *state* is not, so the value
function can't tell a strong board from a weak one. If autoresearch plateaus, enrich
`encode_state` (active + bench card identity / hp / attack potential via the catalog,
mirroring `card_features`) and re-baseline. This is a bigger lever than any HP.

---

## 6. The launch prompt (paste into the next session)

> Use the `autoresearch` skill. Goal: maximize the DQN's greedy win-rate vs
> **random** (then **heuristic**) — see `docs/003_autoresearch_prep.md`. Metric =
> mean greedy win-rate over 200 eval games × seeds {9000,9001,9002}. First
> re-baseline (§0) and record the number. Then implement the §4 prep (EMA +
> averaged-seed eval + a direct-call trial driver), then sweep the §2 space within
> the §3 budget, logging configs+metrics to `data/autoresearch/results.jsonl`,
> keeping a config only when it beats the best beyond the noise band. Keep
> `just check` green; don't commit `data/`. Report the best config + its metric vs
> both opponents.

**Note on who runs it:** training is normally run by the user in tmux (memory
`run-training-yourself`). Decide at the start whether the model drives the loop
in-session (trials are short now) or just generates configs for the user to run.
