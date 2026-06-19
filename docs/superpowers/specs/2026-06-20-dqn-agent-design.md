# DQN agent for CABT — design spec

**Date:** 2026-06-20
**Status:** Approved (brainstorming complete; ready for implementation plan)
**Topic:** Train a deep Q-learning agent that beats the heuristic `fire_agent` at the Pokémon TCG (CABT) environment.

---

## Goal & success bar

Build a deep Q-learning (DQN) agent for the CABT engine whose **success bar is
beating the existing heuristic `fire_agent`** in head-to-head play — not merely
beating `random_agent`.

- **Primary acceptance:** the trained DQN, playing greedily, wins **> 50%**
  (target ≥ 55%) of ≥ 200 games head-to-head vs the heuristic `fire_agent`.
- **Secondary:** wins **> 85%** vs `random_agent`; a learning curve is logged.
- The heuristic baseline today wins ~74% vs `random_agent` over 50 games
  (`docs/000_plan_engine_enum_extraction.md`), so "beat the heuristic" is a
  genuinely harder target than "beat random."

## Context (verified this session)

- **Decoding is done.** Phases 1–2 of the enum-extraction plan are complete and
  all acceptance boxes checked; the agent reads `select.type`/`select.context`
  and uses the real `cabt_enums`. The top-level `CLAUDE.md` warning ("don't train
  until decoding is solid") refers to a gate that is now satisfied. Training is
  unblocked.
- **Stack:** no PyTorch (Python 3.14 has no wheels yet). Available and used:
  **`jax` + `flax` + `optax` + `orbax-checkpoint` + `chex`**, plus `numpy`,
  `gymnasium`/`gymnax` (unused here), `kaggle-environments`.
- **Compute is CPU-only** (GPU driver mismatch, no CUDA jaxlib). The native CABT
  engine runs serially in Python, so **game rollouts are the bottleneck**, not
  gradient steps. This favors DQN's sample-efficient replay buffer and an
  optional parallel-rollout seam.
- **The opponent always plays a fixed deck.** `random_agent` returns a
  module-level `deck` and samples options uniformly; the heuristic plays
  `FIRE_DECK`. So both curriculum stages have a known, stationary opponent deck
  (vs-heuristic is a fire mirror match).
- **Action space is variable & heterogeneous:** each decision the engine hands a
  variable-length `select.option[]` list of mixed option kinds and we return
  index/indices. There is no fixed action vector.

## Non-goals

- Not building general multi-deck play; v1 targets the 000 fire deck as *our*
  deck. Card features come from the catalogs so the design can generalize later.
- Not self-play in v1 (curriculum vs random→heuristic instead). Self-play is a
  documented future extension.
- Not changing the heuristic agent or the engine; the heuristic stays as the
  baseline opponent and sanity reference.

---

## Architecture: option-scoring DQN ("action-as-input")

The network is `Q(state, option) → scalar`. Each decision:

1. Featurize the state once and each of the *K* presented options.
2. Run the net over all *K* options in one batched pass → `Q[K]`.
3. Pick `argmax` (ε-greedy while training; top-k for the rare `maxCount > 1`,
   a documented v1 approximation).

The Bellman target maxes over **options offered at the next state**:

```
y = r + γ (1 − done) · Q_target(s', argmax_{o' ∈ A(s')} Q_online(s', o'))   # Double DQN
```

so the replay buffer stores each next state's **whole option set, padded to a
max K with a boolean mask**.

**Why this over a fixed global action space + masking:** the option set is deeply
heterogeneous and contextual (NUMBER selections disambiguated by
`SelectContext`, per-target attaches, contextual cards). A fixed global index
would be brittle, deck-specific, and re-introduce the "OK#n" ambiguity the enum
work just removed. Option-scoring handles variable count natively, generalizes
across cards (it scores option *features*), and directly mirrors the existing
`score_option(opt, …)` — making it easy to sanity-check against the heuristic.

---

## Module layout — new package `src/pokemon/rl/`

Keeps RL separate from the heuristic agent; durable code lives in `src/pokemon/`
per repo conventions.

| Module | Responsibility |
|--------|----------------|
| `config.py` | Hyperparameter dataclass (γ, lr, batch size, replay capacity, ε schedule, target-update interval, network sizes, curriculum thresholds, `K_max`). |
| `features.py` | `encode_state(obs) → np.ndarray[float32, S]`; `encode_option(opt, obs) → np.ndarray[float32, O]`; `encode_decision(obs) → (state[S], options[K,O], k)`. Uses `cabt_enums` + `catalog`. **The crux.** |
| `net.py` | flax `QNet` (`concat[state, option] → MLP → scalar`); batched scoring of an option set with a mask → `Q[B,K]`. |
| `replay.py` | numpy ring buffer of transitions; stores next state's padded option matrix `[K_max,O]` + mask `[K_max]`. |
| `reward.py` | Potential-based prize shaping + terminal ±1. |
| `rollout.py` | Stateful "collector" kaggle-agent recording `(obs, options, chosen)` and acting ε-greedy; `play_game(params, opponent, eps) → list[transition]`. Seam for multiprocessing workers. |
| `train.py` | Curriculum loop, ε schedule, target net, Double-DQN update (optax Adam, Huber), orbax checkpoints, periodic eval, CSV logging. |
| `policy.py` | Wrap a checkpoint as a greedy kaggle-agent that plugs into the existing CLI/eval exactly like `fire_agent`. |
| `eval.py` | Head-to-head win-rate vs `random_agent` and vs heuristic `fire_agent`. |
| CLI | New Typer app exposed as console script `pokemon-train` with subcommands `train` / `eval` / `play`. |

---

## Feature encoding (detail — the make-or-break component)

### State `vec[S]` (from `obs["current"]`), for **both** players
- **Active Pokémon:** HP ratio (`hp/maxHp`), total energy count, per-`EnergyType`
  energy counts, 5 special-condition flags (poison/burn/sleep/paralyze/confuse).
- **Bench:** padded to `benchMax` slots, each with HP ratio + energy count; plus
  bench size.
- **Counts:** hand, deck, discard, and **prize remaining** (the win clock).
- **Turn/flags:** turn number (scaled), `supporterPlayed`, `stadiumPlayed`,
  `energyAttached`, `retreated`, whose turn / `yourIndex`, `firstPlayer`.
- **Selection meta:** `SelectType` one-hot, `SelectContext` one-hot, `minCount`,
  `maxCount`, `remainEnergyCost`, `remainDamageCounter`.

### Option `vec[O]` (per `select.option[i]`)
- `OptionType` one-hot (17), `AreaType` + `inPlayArea` one-hots.
- Numeric fields normalized: `number`, `count`.
- **Card semantics from catalogs** (`all_cards.json` / `all_attacks.json`):
  cardType one-hot, energy type, HP/stage for Pokémon, attack damage & energy
  cost for attacks. This is what lets the net understand *what a choice does*.
- For ATTACH/EVOLVE: the **target slot's** current HP ratio + energy count
  (resolved via `inPlayArea`/`inPlayIndex`).

Encoders are pure and deterministic; dimensions `S` and `O` are fixed constants
asserted in tests. Unknown enum ints flow through `cabt_enums.safe` without
crashing.

---

## Learning details

- **Network:** `QNet` = `concat[state, option] → Dense(256) → ReLU → Dense(256)
  → ReLU → Dense(1)`. Batched to score `[B, K]` options; masked positions get
  `−inf` before argmax/max.
- **Target:** Double DQN as above; Huber loss; optax Adam; **hard** target-net
  copy every `C` steps. Online params + opt-state + step checkpointed via orbax.
- **Exploration:** ε-greedy with linear decay; partial ε reset at the curriculum
  phase switch.

## Reward (`reward.py`)

Potential-based shaping, policy-invariant:

```
Φ(s)        = opp_prizes_remaining(s) − my_prizes_remaining(s)
r_shaped     = γ · Φ(s') − Φ(s)            # per step between our decisions
r_terminal   = +1 (win) / −1 (loss) / 0 (draw)   # added on the terminal transition
```

Potential-based shaping does not change the optimal policy yet provides a dense
KO/prize signal — matching the chosen "shaped but principled" approach.
**Validation step:** confirm the `prize` field's decrease-on-KO semantics
empirically before trusting the sign.

## Training flow & curriculum

Collect *G* games (collector vs current opponent) → push transitions → *U*
gradient updates → repeat.

- **Phase 1:** opponent = `random_agent`, until eval-vs-random ≥ ~85% (or a step
  cap).
- **Phase 2:** opponent = heuristic `fire_agent` (partial ε reset on switch),
  optimizing toward the primary acceptance bar.

Single-process for v1; `rollout.py` exposes a seam to fan rollouts across
multiprocessing workers (each with a frozen param snapshot) if CPU throughput is
limiting.

---

## Evaluation & acceptance criteria

- [ ] DQN (greedy) wins **> 50%** (target ≥ 55%) of ≥ 200 head-to-head games vs
      the heuristic `fire_agent`.
- [ ] DQN wins **> 85%** vs `random_agent`.
- [ ] Learning curve (step, loss, ε, eval win-rates) logged to CSV.
- [ ] `just check` green: `ruff check` + `ruff format --check` + pyright + new
      `tests/`. Tests cover: encoder output shapes & determinism, replay
      roundtrip + mask correctness, net forward shapes, target computation on a
      toy transition, potential-shaping telescoping, and a fast end-to-end smoke
      run (a handful of steps; no long training).
- [ ] A checkpoint loads and plays a full game via `policy.py` through the
      existing CLI path.

## Build order (incremental — respects CPU reality)

- **M0** — `features` + `net` + `replay` + `rollout` collector wired end-to-end;
  smoke-tested; **no learning yet**. Validate rollout throughput (games/sec) and
  the prize-field semantics here.
- **M1** — full train loop vs `random_agent`; demonstrate win-rate vs random
  climbing past ~85%.
- **M2** — curriculum switch to heuristic; head-to-head eval; iterate features /
  hyperparameters to cross the 50% bar.
- **M3** — polish: `eval` CLI, checkpoint management, a `deck/000` RL gameplay
  walkthrough doc, and optional dueling-head / parallel rollout / self-play if
  the bar isn't met single-process.

## Known risks & mitigations

- **CPU rollout throughput** — measure games/sec at M0; parallelize rollouts if
  it gates progress.
- **Prize-field semantics** — verify the decrease-on-KO direction empirically
  before trusting the shaping sign.
- **`maxCount > 1`** — v1 picks top-k independently (documented approximation);
  most decisions are pick-1.
- **Feature completeness** — start with the solid set above and iterate at M2 if
  learning stalls.
- **Curriculum non-stationarity** — partial ε reset and a fresh replay-warm
  window at the phase switch.

## Files

| Path | Role |
|------|------|
| `src/pokemon/rl/__init__.py` | package marker |
| `src/pokemon/rl/config.py` | **new** — hyperparameters |
| `src/pokemon/rl/features.py` | **new** — state/option encoders |
| `src/pokemon/rl/net.py` | **new** — flax `QNet` |
| `src/pokemon/rl/replay.py` | **new** — replay buffer |
| `src/pokemon/rl/reward.py` | **new** — prize-potential shaping |
| `src/pokemon/rl/rollout.py` | **new** — collector agent + game driver |
| `src/pokemon/rl/train.py` | **new** — training loop |
| `src/pokemon/rl/policy.py` | **new** — checkpoint → greedy kaggle-agent |
| `src/pokemon/rl/eval.py` | **new** — head-to-head evaluation |
| `src/pokemon/rl/cli.py` | **new** — Typer app (`pokemon-train`) |
| `pyproject.toml` | edit — add `pokemon-train` console script (deps already present) |
| `tests/` | **new** — encoder/replay/net/target/reward/smoke tests |
| `deck/000_*` | edit/add — RL gameplay walkthrough at M3 |

## References

- `docs/000_plan_engine_enum_extraction.md` — enum reference + ABI + decoding state.
- `src/pokemon/cabt_enums.py` — the enums the encoders consume.
- `src/pokemon/agent.py` — heuristic `fire_agent` (baseline opponent & reference).
- `src/pokemon/catalog.py` — card/attack name + feature lookups.
- `reverse-engineering/data/all_cards.json`, `all_attacks.json` — card/attack features.
- `.venv/.../cabt/cg/{sim,game}.py` — ctypes ABI boundary (read-only).
