# AGENTS.md — Pokémon TCG agent

Guidance for any AI/human contributor working in this repo. `CLAUDE.md` is a
symlink to this file.

## Mission

Build and train an agent that plays the **Pokémon TCG AI Battle (CABT)**
environment from `kaggle_environments`. The engine is a native C++ library
(`libcg.so`) driven through a thin ctypes/JSON boundary.

## Where we are right now

**Two threads, both past their risky unknowns:**

1. **Engine decoding — DONE.** Observations and option codes are decoded against
   the engine's real enums (`src/pokemon/cabt_enums.py`). The heuristic
   `fire_agent` reads `select.type` + `select.context` (not just `option.type`)
   and wins ~74% vs `random_agent`. Details + enum reference + ABI:
   `docs/000_plan_engine_enum_extraction.md` (Phases 1–2 complete).
2. **DQN agent — IN PROGRESS.** We're building a deep Q-learning agent whose
   success bar is **beating the heuristic `fire_agent`** (not just random). The
   living status doc — decisions, architecture, milestone roadmap — is
   **`docs/001_dqn_progress.md`**. Read it first for the DQN.
   - **M0 (done):** the full data path — feature encoders, option-scoring
     Q-network, replay buffer, prize-potential reward, rollout collector —
     behind `pokemon-train smoke`. **It does not learn yet** (uniform-random
     policy); M0 only proves the pipeline runs on real games (~5 games/sec on
     CPU; prize-sign confirmed).
   - **M1 (next):** the actual learning loop — ε-greedy acting + Double-DQN
     updates + target net + curriculum (random→heuristic) + checkpoints + eval.
   - **M2:** beat the heuristic (curriculum switch, richer features, tune).
   - **M3:** polish (eval CLI, checkpoint mgmt, optional dueling/parallel/self-play).

**Approach (locked in):** JAX/flax/optax/orbax (no PyTorch — no py3.14 wheels);
option-scoring DQN `Q(state, option)→scalar` with argmax over the variable
option list; Double-DQN target over the next state's offered options;
potential-based prize-count reward. CPU-only, so rollouts are the bottleneck.

## Running things

- Environment is Nix flake + `direnv` (`.envrc` = `use flake`) with a `uv`-managed
  venv at `.venv/` (Python 3.14). Entering the dir syncs deps.
- Common tasks via `just` (see `justfile`): `just test`, `just lint`, `just fmt`,
  `just typecheck`, `just check` (all of them), `just sync`.
- Play the fire deck with the heuristic agent (single-command Typer app):
  ```bash
  uv run pokemon-play -g 5 -v        # 5 games, verbose
  uv run python -m pokemon -g 1 -v   # equivalent
  just run -g 1 -v                   # equivalent
  ```
- Drive the DQN pipeline (M0 = wire-check; M1 adds real training/eval subcommands):
  ```bash
  uv run pokemon-train smoke -g 5    # play games, collect DQN transitions, report throughput
  ```
- Lint/format must pass before committing: `uv run ruff check . && uv run ruff format --check .`

## Repo layout — what lives where

| Path | Contents | Put here |
|------|----------|----------|
| `src/pokemon/` | Installed package (`uv` editable). `cabt_enums.py` (engine `IntEnum`s), `catalog.py` (card/attack names + option formatting), `decks.py` (decks + checksum), `agent.py` (`fire_agent`, `score_option`), `cli.py` + `__main__.py` (the `pokemon-play` script). | **All shared, reusable code** — enums, observation parsing, scoring, agents. |
| `src/pokemon/rl/` | The deep Q-learning agent: `config.py` (`DQNConfig`), `features.py` (obs→fixed vectors), `net.py` (flax `QNet`), `replay.py` (replay buffer), `reward.py` (prize shaping), `rollout.py` (game→transitions), `cli.py` (the `pokemon-train` script). | DQN code — encoders, network, replay, reward, and the training loop (M1+). |
| `deck/` | Per-deck artifacts, numbered `NNN_<name>`: a thin decklist `.py` re-exporting `pokemon.decks`, a decklist `.md`, and a gameplay walkthrough `.md`. `000` is the fire deck. | A new deck → add it to `pokemon.decks`, then a `NNN_<name>.*` artifact set here. |
| `docs/` | Engine + project notes. `CABT.md` = obs/option reference (partly stale). `000_plan_engine_enum_extraction.md` = engine-decoding plan + enum reference. `001_dqn_progress.md` = DQN status. `superpowers/specs/` + `superpowers/plans/` = DQN design spec & build plans. | Specs, plans, engine/agent notes. Plans get a `NNN_plan_` prefix or live under `superpowers/plans/`. |
| `reverse-engineering/` | `README.md` (RE command cookbook), `scripts/` (engine explorers/extractors), `data/` (symbol dumps + `all_cards.json` 1267 cards / `all_attacks.json` 1556 attacks). | Anything about prying data/behavior out of `libcg.so`. The card/attack JSON here is the authoritative id→name source. |
| `notebooks/` | Jupyter exploration (empty). | Throwaway/EDA notebooks. |
| `scripts/` | One-off scripts (empty). | Ad-hoc tooling that isn't a deck or RE script. |
| `data/` | DuckDB / datasets (empty; `just data` opens duckdb here). | Generated data, game logs, training datasets. |
| `tests/` | Pytest (`testpaths = ["tests"]`). Engine-enum + format-option tests; `tests/rl/` covers the DQN package (encoders, net, replay, reward, a slow real-engine rollout). | Tests for `src/pokemon/`. |

The CABT engine itself is vendored under the venv:
`.venv/lib/python3.14/site-packages/kaggle_environments/envs/cabt/` — `cg/sim.py`
+ `cg/game.py` are the ctypes ABI; `cg/libcg.so` is the engine. **Read-only.**

## Conventions

- **Decks are canonical in `pokemon.decks`**; the numbered `deck/NNN_<name>.*`
  artifacts (thin decklist py + decklist md + gameplay md) document them. Reuse
  `000` as the template.
- **Card/attack names** come from the catalogs in `reverse-engineering/data/`,
  not hand-typed maps. Look up by `cardId`/`attackId` via `pokemon.catalog`; keep
  a small override map only for nicer display names.
- **Enums over magic ints.** Import `IntEnum`s from `src/pokemon/cabt_enums.py`
  instead of writing `if opt["type"] == 7`. The integer meanings are defined by
  the engine; they're transcribed from the `000` plan doc and verified empirically.
- **DQN code is JAX.** flax (`nn.Module`), optax, orbax for checkpoints. Keep
  feature encoders pure/deterministic with fixed, test-asserted dimensions.
- Style: ruff, line length 100, double quotes, target py314. Type-check with pyright.
- Commit messages end with the `Co-Authored-By` trailer.

## Known rough edges (don't be surprised)

- **`docs/CABT.md` is partly stale:** its option-type/area tables predate the
  official enums and mislabel some values (e.g. 7/8). The authoritative source is
  `src/pokemon/cabt_enums.py` (verified empirically) and the `000` plan. When
  they conflict, the enums win; reconcile `CABT.md` when you touch it.
  *(The old `format_option`/`score_option` mislabeling is already fixed — that
  fix lifted the fire deck's win-rate from ~43% to ~74% vs random.)*
- **JAX deps are transitive, not direct:** `jax`/`flax`/`optax`/`orbax-checkpoint`
  come in via `kaggle-environments → gymnax → flax`, so `uv sync` reproduces them
  today, but they aren't declared in `pyproject.toml [project.dependencies]`.
  Declare the directly-imported ones at M1.
- **The DQN doesn't learn yet:** M0 is a random-policy wire-check. Don't mistake
  `pokemon-train smoke` output for a trained agent — see `docs/001_dqn_progress.md`.

## Start-here reading order

1. This file.
2. **`docs/002_dqn_next_steps.md`** — handoff/roadmap; **speed (A) + option-feature fix done; next = re-baseline → stabilize (B1) → beat the heuristic (B2/M3)**. Start here to continue the DQN work. For the hyperparameter sweep, see **`docs/003_autoresearch_prep.md`**.
3. `docs/001_dqn_progress.md` — DQN build status, decisions, results, diagnosis.
3. `docs/000_plan_engine_enum_extraction.md` — engine decoding plan + full enum reference + ABI.
4. `docs/CABT.md` — observation shape (treat the option-type table with suspicion).
5. `src/pokemon/agent.py` + `catalog.py` + `cabt_enums.py` — the working heuristic agent.
6. `src/pokemon/rl/` — the DQN package (start at `features.py`, then `rollout.py`).
