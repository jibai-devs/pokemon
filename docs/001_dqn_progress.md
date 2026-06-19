# 001 — DQN agent: build progress & status

**Living status doc** for the deep Q-learning agent that plays the CABT Pokémon
TCG environment. Update this as milestones land. Last updated: **2026-06-20**.

- **Branch:** `feat/dqn-agent`
- **Design spec:** `docs/superpowers/specs/2026-06-20-dqn-agent-design.md`
- **M0 plan:** `docs/superpowers/plans/2026-06-20-dqn-m0.md`
- **Code:** `src/pokemon/rl/`

---

## TL;DR (where we are right now)

- **M0 is DONE and runnable.** The full data path exists: observation → feature
  encoders → option-scoring Q-network → replay buffer, plus prize-based reward
  shaping and a rollout collector that turns real games into DQN transitions.
  `just check` is green (26 tests).
- **It does NOT learn yet.** The acting policy is still **uniform random**. There
  is no training loop, no ε-greedy, no gradient updates, no evaluation vs the
  heuristic. M0 is the *foundation*, not a trained agent.
- **Next is M1**: the actual learning loop (ε-greedy + Double-DQN updates +
  curriculum + checkpoints + eval).

Run what exists:
```bash
uv run pokemon-train smoke -g 5    # collect transitions from real games; report throughput
just check                         # fmt + lint + pyright + tests (all green)
uv run pokemon-play -g 5 -v        # existing heuristic agent (the baseline to beat)
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

Feature dims (fixed, asserted in tests): **STATE_DIM = 126**, **OPTION_DIM = 49**.

---

## Milestone roadmap & status

| Milestone | Scope | Status |
|-----------|-------|--------|
| **Design** | Brainstormed spec, approved | ✅ done (`8ebb8cf`) |
| **M0 — wire-check** | Encoders, Q-net, replay, reward, rollout, `smoke` CLI. **No learning.** | ✅ **done** |
| **M1 — learning loop** | ε-greedy policy, Double-DQN updates, target net, replay training, checkpoints, basic eval. Train vs `random_agent`, show win-rate climb. | ⬜ not started |
| **M2 — beat the heuristic** | Curriculum switch to heuristic; head-to-head eval; enrich features (catalog-backed card/attack stats); tune until >50% vs heuristic. | ⬜ not started |
| **M3 — polish** | Eval CLI, checkpoint mgmt, gameplay walkthrough doc, optional dueling head / parallel rollouts / self-play if needed. | ⬜ not started |

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

## NOT done yet (so expectations are clear)

- **No learning.** Policy is uniform random; no ε-greedy, no gradient steps, no
  target-network sync, no training CLI. → M1.
- **No evaluation** vs heuristic/random as a win-rate harness. → M1.
- **No checkpointing** of trained params (orbax wired in M1).
- **`maxCount > 1`** decisions: M0 records only the first chosen index
  (pick-1). Multi-select handling (top-k) → M1.
- **Rich features** (catalog-backed card/attack stats) → M2.

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

Write the **M1 plan** (learning loop) and build it the same way: spec already
covers the design → bite-sized TDD plan → subagent execution with review gates.
M1 ends when win-rate vs `random_agent` visibly climbs past ~85%.
