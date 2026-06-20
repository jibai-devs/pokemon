# 002 — DQN next steps (handoff / roadmap)

**Read this first if you're a new session continuing the DQN work.** It captures
where we are, what we decided, and exactly what to do next. **Current focus:
Section A (SPEED) is DONE — next is Section B1 (stabilize) then B2 (M3, beat the
heuristic).**

- **Branch:** `feat/dqn-agent`
- **Status doc (results/diagnosis):** `docs/001_dqn_progress.md`
- **Design spec:** `docs/superpowers/specs/2026-06-20-dqn-agent-design.md`
- **Plans:** `docs/superpowers/plans/2026-06-20-dqn-m0.md`, `…-m1.md`, `…-m2.md`
- **Usage cheat-sheet:** `docs/dqn_usage.md`
- **Code:** `src/pokemon/rl/`

---

## Where we are (snapshot)

Working DQN pipeline, all committed, `just check` green (47 tests):
- **M0** — data path: encoders, `QNet`, replay, prize reward, rollout (`smoke` CLI).
- **M1** — learning loop: ε-greedy, Double-DQN, Polyak target, checkpoints, eval,
  `train`/`eval` CLI.
- **M2** — fixed ε schedule + enriched option features with catalog card/attack
  stats (`OPTION_DIM` 49→90).
- **M2.1** — best-by-eval checkpoint + per-run dirs + save-on-interrupt.

**What we learned (important):**
- **M1 did not beat random** (34% vs 30% baseline) — blockers were slow ε + thin features.
- **M2 *did* learn** (back-half evals avg ~54% vs 30%), but the policy is **unstable
  iter-to-iter** (20%↔80%) and early code saved latest-not-best. Stability + capture
  are the open issues.
- **Win-rate jumps** come from (a) eval noise (30–50 games = ±~18%) and (b) genuine
  DQN policy churn (argmax flips). The training loop **never reloads best** — it keeps
  optimizing the online net, so it can drift away from a good point.
- **GPU is not worth it** (see profiling). The bottleneck is CPU rollouts + our own
  Python/JAX-dispatch overhead, which a GPU can't help.
- **Opponent is weak:** `random_agent` plays a fixed Water/Mega-Abomasnow-ex deck
  (33/60 cards are energy) with uniformly random moves. So "beat random" is a low bar;
  the real target is the **heuristic `fire_agent`** (~74% vs random).

**Profiling (one training iteration = 8 games + 100 updates), measured on CPU:**

| Component | Share | GPU-able? |
|---|---|---|
| Engine (`libcg`) rollouts | ~30% | ❌ |
| Our overhead (encode + un-jitted net forward) | ~55% | ⚠️ mostly no |
| Gradient updates (JAX) | ~14% | ✅ |

Per-unit: pure engine **257 ms/game** (3.9/s), our collection **725 ms/game** (1.4/s),
one update **9.5 ms**. The shock: **our per-decision overhead (468 ms/game) is bigger
than the engine itself** — because the policy forward (`net.q_values` → `model.apply`)
is **not JIT-compiled** and is called ~30×/game (plus we re-encode states).

---

## A. Speed — ✅ DONE (2026-06-20)

A1 + A2 landed (`c06171b`, `4082ec3`); A3 skipped (see below). Profiler lives at
`scripts/profile_dqn.py` (`-w N` times parallel collection too).

**Result (measured on this CPU):**
- **A1 — JIT padded/masked scorer:** our per-decision overhead **172 → ~0 ms/game**;
  collection **283 → ~95 ms/game** (now at the engine-rollout floor). The policy
  forward (`net.q_values_masked`) is jitted with `apply_fn` as a static arg so JAX
  caches the compile and reuses it across every decision; options are padded to
  `k_max` + masked (`features.encode_decision_padded`) so shapes stay fixed.
- **A2 — parallel rollouts:** `rl/parallel.py` `RolloutPool` (persistent `spawn`
  workers) → **~8.5× at 16 workers** (~12 ms/game, ~82 games/s). Wired into
  `train.py` behind `--workers` (1 = serial, default); `--opponent random|heuristic`
  added at the same time (readies B2). **Combined A1+A2: collection ~23× faster.**
- **A3 — encode caching: SKIPPED on purpose.** A1 already drove per-decision encode+
  forward to ~0 and A2 parallelizes the engine, so caching per-card/attack vectors
  would trim a now-negligible slice. Revisit only if a profiler shows encode is hot.

Original plan kept below for reference.

---

### (reference) A. Speed plan as written

Goal: make a training run / eval / sweep several× faster so all later work
(stability, M3, hyperparameter search) is practical. Three levers, in order:

### A1. JIT the inference forward  (biggest easy win — attacks the 55%)
**Problem:** `net.q_values(model, params, state, options)` calls `model.apply`
un-jitted, once per decision in `policy.select_action` (collection) and eval.
**Approach:**
- Add a jitted scorer reused across calls. Variable option count `K` causes
  shape-driven recompiles, so **pad options to a fixed width and pass a mask**:
  - In `features.py`, add `encode_decision_padded(obs, k_max) -> (state[S], options[k_max,O], mask[k_max], k)` (zeros + False past `k`).
  - In `net.py`, add a jitted `q_values_masked(apply_fn, params, state, options, mask) -> [k_max]` returning `-inf` at masked slots (jit once on fixed shapes).
  - In `policy.py`, build the jitted fn once (closure) and argmax over valid entries.
- Keep the un-padded `q_values` for tests/back-compat, or update callers.
**Verify:** re-run the profiler (save it as `scripts/profile_dqn.py` from the snippet
below); collection ms/game should drop substantially. `just check` stays green.

### A2. Parallel rollouts  (biggest throughput win — attacks the ~85%)
**Problem:** games run one at a time; engine is CPU-bound and serial.
**Approach:**
- Games are independent → run `games_per_iter` across CPU cores. Use a persistent
  `multiprocessing`/`concurrent.futures.ProcessPoolExecutor` pool (workers import
  `kaggle_environments` once — startup is heavy, so reuse them).
- Each worker gets the current params (serialize via `flax.serialization.to_bytes`,
  ~0.5 MB) + a seed, plays one game with `rollout.play_game`, returns transitions.
- Main process aggregates into the replay buffer, does the gradient updates, then
  broadcasts updated params next iteration.
- Add `rollout.play_games_parallel(params, n, opponent, seeds, n_workers)` and wire
  it into `train.py` behind a `--workers` flag (default 1 = current behavior).
**Watch out:** JAX in subprocesses (each worker has its own; set
`os.environ["XLA_FLAGS"]`/threads modestly to avoid oversubscription); deterministic
per-worker seeds; clean pool shutdown.
**Verify:** games/sec scales ~linearly with `--workers` up to core count.

### A3. (Optional) Encode caching
Precompute per-card and per-attack feature vectors once into dicts
(`cardId -> np.ndarray`, `attackId -> np.ndarray`) and assemble option vectors by
lookup+concat instead of rebuilding lists each call. Trims the Python part of the 55%.

**Speed acceptance:** profiler shows a clear drop in ms/game and total iteration
time; a 200-iter run that took ~15–20 min drops materially; `just check` green.

### Profiler snippet (save as `scripts/profile_dqn.py`)
Times pure engine vs our collection vs gradient updates and prints the % breakdown.
(See git history / this session for the exact script; it: plays N games with two
built-in `random_agent`s for pure-engine timing; plays N games with
`policy.greedy_act` for collection timing; times 100 jitted `update_step`s after
warmup; prints engine/our-overhead/updates shares.)

---

## A2.5 — Option-feature audit & fix (DONE, 2026-06-20)

Before tuning, audited correctness. **Code is correct** (Double-DQN target,
masking, potential-based reward all check out) and **the QNet is small (~122k
params) — not too complex.** The real bug was the *input*: **44% of offered
options encoded to a vector identical to another option in the same decision**
(`encode_option` ignored `index`/`inPlayIndex`/`energyIndex` — which source card,
which in-play target, which attached energy), so the net was blind to ~half its
choices and `argmax` picked arbitrarily. Fixed by encoding source/target identity
+ the referenced target Pokémon's features. **Collision rate 44% → 0.04%**,
`OPTION_DIM` 90 → 127 (re-train). Guard test added (`tests/rl/test_features_option.py`).
**Re-baseline before autoresearch** — this likely changes everything below.

State features are still thin (no Pokémon identity in `encode_state`) → next
representation lever after re-baseline (see B2 last bullet).

---

## B. Backlog (after speed) — in priority order

### B1. Stabilize the policy (so win-rate stops swinging)
- **EMA of weights:** keep an exponential moving average of the online params and
  **evaluate/checkpoint the EMA**, not the raw net. Smooths argmax churn — usually a
  big win for the deployed policy.
- Bump default `--eval-games` to ≥100 (kills most eval noise).
- Tune `lr` (the `1e-3` run diverged; `3e-4`/`1e-4` more stable), `tau`, add optax
  gradient clipping.

### B2. M3 — beat the heuristic (the real goal)
- Train against `fire_agent` instead of `random_agent` (pass `opponent=` through the
  CLI; add `--opponent random|heuristic`). This is a fire mirror match.
- Consider **self-play** (opponent pool of frozen past checkpoints) for a stronger,
  non-stationary opponent and a higher skill ceiling.
- Target: greedy win-rate **>50%** (≥55%) vs the heuristic over ≥200 games.
- Also enrich **state** features (active/bench Pokémon stats) — currently only
  *option* features are rich; state Pokémon are thin (hp ratio + energy count).

### B3. Hyperparameter search (autoresearch)
- Use the `autoresearch` skill: metric = greedy win-rate vs opponent; sweep
  `lr`, `tau`, `gamma`, `updates_per_iter`, net size, `eps_decay_steps`.
- Only practical **after A (speed)** — otherwise each trial is 15–20 min.

### B4. Reward / credit assignment (if learning still weak)
- Prize-potential shaping only fires on KOs; most decisions get ~0 reward over a
  long horizon. Consider denser shaping (damage dealt, energy efficiency) carefully,
  or n-step returns, if B1/B2 don't get there.

---

## Reference facts (don't re-derive)

- **Dims:** `STATE_DIM=126`, `OPTION_DIM=127` (referenced by symbol everywhere — a
  feature change auto-propagates; old checkpoints become incompatible → re-train).
- **Baselines vs `random_agent`:** random-policy ≈ 30%, heuristic `fire_agent` ≈ 74%.
- **Eval noise:** 30 games ≈ ±18% (95% CI), 100 ≈ ±9%, 200 ≈ ±6%. Use ≥100 to compare.
- **Compute:** CPU-only (GPU driver mismatch + no CUDA jaxlib; don't chase it).
- **Checkpoints:** `data/checkpoints/run-<ts>/best.msgpack` (+`last.msgpack`),
  gitignored; `eval --ckpt data/checkpoints` auto-resolves the newest run's best.
- **Key files:** `features.py` (encoders), `net.py` (`QNet`/`q_values`/`q_values_batched`),
  `policy.py` (action selection), `rollout.py` (`play_game`), `learner.py`
  (`make_update_step`/`soft_update`), `train.py` (loop), `eval.py`, `cli.py`, `config.py`.

---

## Workflow & conventions (for the next session)

- **The user runs long training jobs themselves** (tmux `pokemon`). Do **not** launch
  `pokemon-train train` as a background job — hand them the copy-pasteable command and
  the matching `eval`. Run only short things yourself (smoke, eval, `just check`,
  profiler). See memory `run-training-yourself`.
- **Process:** brainstorm (if new design) → `writing-plans` → `subagent-driven-development`
  (fresh subagent per coherent unit, TDD, review). The Speed section above is ready to
  turn into a plan with `writing-plans`.
- **Style:** ruff (line length 100, double quotes, py314), pyright clean, `just check`
  green. Commit messages end with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- **Editable install:** code edits don't affect an already-running training process;
  they apply to the next run.

## Suggested first action for the next session
1. Read `docs/001_dqn_progress.md` (results) + this doc. Speed (Section A) is done.
2. Start **B1 (stabilize):** add an EMA of the online params and eval/checkpoint the
   EMA; bump default `--eval-games` to ≥100; sanity-check `lr`/`tau`. Now that runs
   are ~20× faster, kick off real training with `--workers 16` to confirm the
   speedup end-to-end and re-establish the win-rate curve.
3. Then **B2 (M3):** `--opponent heuristic` is already wired — train the fire mirror
   and push greedy win-rate >50% vs `fire_agent`.
