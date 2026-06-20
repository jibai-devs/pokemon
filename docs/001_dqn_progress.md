# 001 — DQN agent: build progress & status

**Living status doc** for the deep Q-learning agent that plays the CABT Pokémon
TCG environment. Update this as milestones land. Last updated: **2026-06-20** (M1 complete).

- **Branch:** `feat/dqn-agent`
- **Design spec:** `docs/superpowers/specs/2026-06-20-dqn-agent-design.md`
- **M0 plan:** `docs/superpowers/plans/2026-06-20-dqn-m0.md`
- **Code:** `src/pokemon/rl/`

---

## TL;DR (where we are right now)

- **M2 made it learn to beat random — but the saved checkpoint doesn't capture it.**
  After fixing the ε schedule and enriching option features with catalog-backed
  card/attack stats (`OPTION_DIM` 49→90), a re-train's **back-half evals average
  ~54%** (ε at floor 0.05; individual iters hit 66–80%) vs the **30% random
  baseline** — real learning, unlike M1. **But** the policy is **unstable
  iter-to-iter** (20%↔80%) and we save the *latest* checkpoint, not the *best*,
  so the final artifact measured only **33.5% (±6.5%, n=200)**. (See "M2 result".)
- **M1 (earlier) did NOT beat random** — 34% (±9%) vs 30% baseline; that run's
  blockers (slow ε, thin features) are the ones M2 fixed. (See "M1 training result".)
- **Immediate next fixes** (high value, small): (1) **save the BEST checkpoint** by
  eval win-rate, not the latest — would capture the ~55–65% policy the run already
  produces; (2) **stabilize** the swings (more eval games for selection, Polyak/soft
  target updates or lower lr). Then (M3) curriculum-switch to the heuristic.
- **Still-open lever if needed:** sparse reward / long-horizon credit assignment
  (prize shaping only fires on KOs) and state-Pokémon feature enrichment.

Run what exists:
```bash
uv run pokemon-train smoke -g 5    # collect transitions; verify throughput
uv run pokemon-train train -n 5 --eval-every 1 --eval-games 10  # short training run
uv run pokemon-train eval --ckpt data/checkpoints/params.msgpack -g 20  # eval a checkpoint
just check                         # fmt + lint + pyright + 35 tests (all green)
uv run pokemon-play -g 5 -v        # existing heuristic agent (the baseline to beat in M2)
```

---

## Goal & success bar

Train a DQN whose **success bar is beating the heuristic `fire_agent`**
head-to-head — not merely beating `random_agent`.

- **Primary:** DQN (greedy) wins **>50%** (target ≥55%) of ≥200 games vs the
  heuristic `fire_agent`.
- **Secondary:** wins **>85%** vs `random_agent`.
- For reference, the heuristic wins ~74% vs random, so "beat the heuristic" is
  the genuinely hard target.

---

## Decisions locked in (and why)

| Decision | Choice | Why |
|----------|--------|-----|
| Framework | **JAX + flax + optax + orbax** (no PyTorch) | PyTorch has no Python 3.14 wheels yet; the JAX stack is already installed. |
| Action-space handling | **Option-scoring DQN** — `Q(state, option)→scalar`, argmax over the offered options | The engine hands a variable-length, heterogeneous option list each turn; there is no fixed action vector. Scoring options sidesteps that and mirrors the existing `score_option`. |
| Target | Double-DQN; max over **options offered at s'** (padded + masked) | Correct Bellman target for a variable action set. |
| Opponent | **Curriculum: random → heuristic** | Stable early learning, then optimize directly against the real target. |
| Reward | **Potential-based prize shaping + terminal ±1** | `Φ = opp_prizes_remaining − my_prizes_remaining`; policy-invariant, dense KO/prize signal. Sign **empirically confirmed** in M0. |
| Compute | **CPU-only** | GPU driver mismatch + no CUDA jaxlib. Rollouts (native engine, serial) are the bottleneck → favors replay + parallel rollout workers. |

---

## Architecture (one screen)

Each decision: encode the state once and each of the *K* offered options; the
network scores all *K* in one batched pass; pick `argmax` (ε-greedy when
training). Transitions `(s, o, r, s', A(s'), done)` go to a replay buffer; the
DQN target maxes over the option set `A(s')` offered at the next state.

```
obs(JSON) ─► features.encode_decision ─► (state[126], options[K,49], k)
                                              │
                            net.QNet  Q(state, option) ─► Q[K] ─► argmax
                                              │
        rollout.play_game ─► transitions ─► replay.ReplayBuffer ─► (M1) train.py
                                              ▲
                          reward.shaped_reward (prize potential + terminal)
```

Feature dims (fixed, asserted in tests): **STATE_DIM = 126**, **OPTION_DIM = 90**
(M2 enriched options from 49 with catalog-backed card/attack semantics).

---

## Milestone roadmap & status

| Milestone | Scope | Status |
|-----------|-------|--------|
| **Design** | Brainstormed spec, approved | ✅ done (`8ebb8cf`) |
| **M0 — wire-check** | Encoders, Q-net, replay, reward, rollout, `smoke` CLI. **No learning.** | ✅ **done** |
| **M1 — learning loop** | ε-greedy policy, Double-DQN updates, target net, replay training, checkpoints, basic eval. Train vs `random_agent`, show win-rate climb. | ✅ **done** |
| **M2 — make it learn (vs random)** | Fix ε schedule; enrich option features (catalog card/attack stats, `OPTION_DIM`→90). Re-train vs random. | ◐ **partial** — learns (back-half ~54%), but checkpoint saves latest-not-best + policy unstable, so saved artifact = 33.5%. |
| **M2.1 — capture & stabilize** | Save BEST checkpoint by eval; more eval games for selection; soft target updates / lower lr to tame 20%↔80% swings. | ⬜ next |
| **M3 — beat the heuristic** | Curriculum switch to heuristic opponent; head-to-head eval; tune until >50% vs `fire_agent`. | ⬜ not started |
| **M4 — polish** | Gameplay walkthrough doc, optional dueling head / parallel rollouts / self-play. | ⬜ not started |

---

## M0 — what was built (DONE)

New package `src/pokemon/rl/`:

| Module | Responsibility | Status |
|--------|----------------|--------|
| `config.py` | `DQNConfig` hyperparameters (γ, lr, batch, replay capacity, ε schedule, target-update interval, `k_max`, …) | ✅ |
| `features.py` | `encode_state`, `encode_option`, `encode_decision`; `STATE_DIM`, `OPTION_DIM` | ✅ |
| `reward.py` | `prizes_remaining`, `potential`, `shaped_reward` (prize potential + terminal) | ✅ |
| `net.py` | flax `QNet` (`concat[state,option]→MLP→scalar`), `init_params`, `q_values` | ✅ |
| `replay.py` | `ReplayBuffer` ring buffer; stores next-state padded option set + mask | ✅ |
| `rollout.py` | `make_collector` (records decisions, random policy for M0), `play_game` → transitions | ✅ |
| `cli.py` | Typer app; `pokemon-train smoke` command | ✅ |
| `tests/rl/` | unit tests for each module + a slow real-engine rollout test (26 tests total in repo) | ✅ |

**Feature encoding (M0 version):**
- *State* (126 dims), for both players: active Pokémon (HP ratio, energy count,
  presence), 5 bench slots, hand/deck/discard/**prize** counts, 5 status-condition
  flags; plus turn, game flags, one-hot `SelectType`/`SelectContext`, and
  selection min/max counts + remaining cost/damage.
- *Option* (49 dims): one-hot `OptionType` + `area` + `inPlayArea`, numeric
  fields (`number`, `count`, has-attack, has-card), and an in-hand flag + raw
  card id. **Rich card/attack stats (type, HP, attack damage from the catalog)
  are deferred to M2.**

**Measured in M0:**
- **Throughput: ~4–5 games/sec** on CPU. ⇒ ~100k transitions ≈ a few hours
  single-threaded ⇒ **M1 should parallelize rollouts** (multiprocessing workers).
- **Prize-sign confirmed:** a WIN yields `terminal_reward=+1` and the shaping
  potential lines up — the reward design is correct (spec risk #1 closed).

**Acceptance (all met):** smoke runs clean; `just check` green (ruff + pyright +
26 tests); throughput recorded; prize semantics confirmed.

### M0 commit trail (on `feat/dqn-agent`)
```
8ebb8cf docs: add DQN agent design spec (option-scoring DQN for CABT)
1cd59b2 docs: add M0 implementation plan for the DQN agent
0240834 feat(rl): add DQN package skeleton, config, pokemon-train script
aeb4ed1 feat(rl): prize-potential reward shaping
d6236c3 feat(rl): state encoder (both players + selection meta)
48b586b feat(rl): option + decision encoders
d353a0f feat(rl): flax option-scoring Q-network
fd3dbee feat(rl): replay buffer with padded next-option sets
81a1928 feat(rl): rollout collector + transition assembly
5616a1d feat(rl): pokemon-train smoke command (M0 wire-check)
7f9e01e fix(rl): wrap q_values apply result so pyright sees a plain array
```

---

## M1 — what was built (DONE)

New modules in `src/pokemon/rl/`:

| Module | Responsibility | Status |
|--------|----------------|--------|
| `policy.py` | `greedy_act(model,params)`, `eps_act(model,params,eps,rng)` — ε-greedy action selection over the offered option list | ✅ |
| `learner.py` | `create_train_state`, `make_update_step` — Double-DQN jitted gradient step with flax `TrainState` + optax Adam | ✅ |
| `checkpoint.py` | `save_params` / `load_params` via flax msgpack serialization | ✅ |
| `eval.py` | `evaluate(act, n_games, seed) -> float` — win-rate harness vs any opponent | ✅ |
| `train.py` | `train(cfg, …) -> (state, history)` — full collect/replay/update/target-sync loop with periodic eval + checkpoint | ✅ |
| `cli.py` | Added `pokemon-train train` and `pokemon-train eval` Typer commands | ✅ |
| `tests/rl/` | Added `test_eval.py`, `test_train.py`; total 35 tests | ✅ |

**Commands:**
- `uv run pokemon-train train -n <N> [--games-per-iter N] [--eval-every N] [--ckpt-dir PATH]`
- `uv run pokemon-train eval --ckpt <path> [-g N]`

**Short 5-iteration smoke run output (2026-06-20):**
```
iter    1 | step      0 | eps 1.000 | loss nan | winrate 0.00%
iter    2 | step     40 | eps 0.999 | loss 0.1284 | winrate 30.00%
iter    3 | step     80 | eps 0.998 | loss 0.1286 | winrate 20.00%
iter    4 | step    120 | eps 0.998 | loss 0.1139 | winrate 10.00%
iter    5 | step    160 | eps 0.997 | loss 0.1794 | winrate 30.00%
best win-rate 30.00% at iter 2
```
Win-rate of a 5-iter checkpoint greedy-evaluated over 20 games: **15%**. (Expected —
barely any training; M2 will run longer with curriculum.)

### M1 training result (200 iterations vs random, 2026-06-20)

A real run — `pokemon-train train -n 200 --games-per-iter 8 --updates-per-iter 100
--eval-every 10 --eval-games 30` (~10 min CPU; loss 0.09 → 0.03). Greedy win-rate
per eval bounced in a **~30–50% band with no upward trend** (peak 56.7% at iter 110
was eval noise). Measured over a larger 100-game sample:

| Agent (100 games vs `random_agent`) | Win-rate |
|---|---|
| DQN trained (this run) | **34.0%** (±9.3%) |
| Random-policy baseline (same deck) | 30.0% (±9.0%) |
| Heuristic `fire_agent` (reference) | ~74% |

**Conclusion: the trained agent is statistically indistinguishable from random** —
the loop *runs and reduces loss*, but does not learn to beat random. See the
ranked diagnosis in the TL;DR (slow ε anneal → mostly-random data; thin features;
sparse long-horizon reward). The fix is M2 (features + ε schedule), not more
compute on the current setup.

### M2 result (features + ε fix, 200 iterations vs random, 2026-06-20)

Re-train after the two fixes — `pokemon-train train -n 200 --games-per-iter 8
--updates-per-iter 100 --eval-every 10 --eval-games 30 --eps-decay-steps 30000`
(ε reaches the 0.05 floor by ~iter 130, so the back half is near-greedy collection).

Per-iter greedy eval (30 games each) climbed out of the baseline band:
```
iter  10: 53%   iter  70: 50%   iter 130: 40%   iter 190: 60%
iter  30: 60%   iter  90: 33%   iter 150: 67%   iter 200: 20%
iter  50: 43%   iter 110: 80%   iter 180: 80%
```
Back-half (iters 130–200, ε=0.05; 240 games aggregated) averages **~54%** — clearly
above the 30% baseline. **This is real learning; the features + ε fix worked.**

**But the saved checkpoint underperforms:** measured over 200 games it is **33.5%
(±6.5%)** — because (a) `train.py` saves the *latest* checkpoint each eval, not the
*best*, and (b) the policy is **unstable iter-to-iter** (20%↔80%). Iter 200 was a
down-swing (20%), so the saved artifact is a weak snapshot; the strong iter-110/180
policies were overwritten.

| Run | Saved-checkpoint win-rate vs random | Note |
|---|---|---|
| M1 (thin features, slow ε) | 34% (±9%, n=100) | at baseline — never learned |
| M2 (rich features, fast ε) | 33.5% (±6.5%, n=200) | saved a down-swing; *back-half avg ~54%* |
| Random-policy baseline | 30% | — |

**Takeaway:** M2 unblocked learning; the gap now is **capturing and stabilizing** it
→ M2.1 (save best-by-eval checkpoint, more eval games for selection, soft target
updates / lower lr).

---

## NOT done yet (so expectations are clear)

- **No curriculum.** Training is vs `random_agent` only. Curriculum switch to
  `fire_agent` heuristic is M2.
- **No rich features.** Card/attack stats (type, HP, damage) not yet encoded. → M2.
- **`maxCount > 1`** decisions: records only the first chosen index (pick-1). → M2.
- **Win-rate vs `random_agent` needs longer runs** to climb past 85%. M1 proves the
  loop works; convergence is M2's job.

---

## Known items / notes

- **JAX deps are transitive, not direct.** `jax`/`flax`/`optax`/`orbax-checkpoint`
  are present via `kaggle-environments → gymnax → flax`, so `uv sync` reproduces
  them today. Best practice (do at M1): declare the ones we import directly in
  `pyproject.toml [project.dependencies]`.
- **`docs/CABT.md`** option-type table is partly stale; the authoritative enums
  live in `src/pokemon/cabt_enums.py` / the `000` plan. Encoders use the enums.
- The 3 pytest warnings are pre-existing Pydantic deprecations inside
  `kaggle_environments`, not our code.

---

## Next step

**M2**: write the M2 plan (beat the heuristic). Key items: curriculum switch to
`fire_agent`, enrich option features with catalog-backed card/attack stats (HP,
type, attack damage), longer training runs, and eval vs `fire_agent` until >50%
head-to-head win-rate.
