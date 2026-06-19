# AGENTS.md — Pokémon TCG agent

Guidance for any AI/human contributor working in this repo. `CLAUDE.md` is a
symlink to this file.

## Mission

Build and train an agent that plays the **Pokémon TCG AI Battle (CABT)**
environment from `kaggle_environments`. The engine is a native C++ library
(`libcg.so`) driven through a thin ctypes/JSON boundary.

## Where we are right now

**Phase: understanding the engine, not training yet.** We are decoding what the
engine's observations and option codes actually *mean* so we can act on them
correctly. The current vehicle is the **000 fire deck**: we run it (and play
games ourselves) against the built-in `random_agent` with verbose logging to see
the real game flow, then reconcile what we observe against the engine's
documented enums.

Concretely, the active thread is:
1. Play fire-deck games with `pokemon-play -v` (or `python -m pokemon -v`) and read the turn-by-turn log.
2. Decode selections via the real enums — see **`docs/000_plan_engine_enum_extraction.md`**
   (the live plan). Key fact: a selection is `select.type` + `select.context`,
   and `option.type` alone is not enough (this is why "OK#n" options look identical).
3. Only after we trust the observation model do we move to actually training an agent.

Do **not** jump ahead to training/RL infrastructure until the observation/option
decoding is solid.

## Running things

- Environment is Nix flake + `direnv` (`.envrc` = `use flake`) with a `uv`-managed
  venv at `.venv/` (Python 3.14). Entering the dir syncs deps.
- Common tasks via `just` (see `justfile`): `just test`, `just lint`, `just fmt`,
  `just typecheck`, `just check` (all of them), `just sync`.
- Play the fire deck (single-command Typer app — no subcommand name):
  ```bash
  uv run pokemon-play -g 5 -v        # 5 games, verbose
  uv run python -m pokemon -g 1 -v   # equivalent
  just run -g 1 -v                   # equivalent
  ```
- Lint/format must pass before committing: `uv run ruff check . && uv run ruff format --check .`

## Repo layout — what lives where

| Path | Contents | Put here |
|------|----------|----------|
| `src/pokemon/` | The installed package (`pip`/`uv` editable). `catalog.py` (card/attack names + option formatting), `decks.py` (deck definitions + checksum), `agent.py` (`fire_agent`, `score_option`), `cli.py` (Typer `app`), `__main__.py` (`python -m pokemon`). Exposed as the `pokemon-play` console script. | **All shared, reusable code** — engine enums, observation parsing, scoring, agents. New durable modules go here (e.g. the planned `src/pokemon/cabt_enums.py`). |
| `deck/` | Per-deck artifacts, numbered `NNN_<name>`: a thin decklist `.py` re-exporting `pokemon.decks`, a decklist `.md`, and a gameplay walkthrough `.md`. `000` is the fire deck. | A new deck → add it to `pokemon.decks`, then a `NNN_<name>.*` artifact set here. |
| `docs/` | Engine + project notes. `CABT.md` = observation/option reference (partly reverse-engineered, partly stale). `000_plan_*.md` = execution plans. | Specs, plans, engine notes. Plans get a `NNN_plan_` prefix. |
| `reverse-engineering/` | `README.md` (RE command cookbook), `scripts/` (engine explorers/extractors), `data/` (symbol dumps + `all_cards.json` 1267 cards / `all_attacks.json` 1556 attacks). | Anything about prying data/behavior out of `libcg.so`. The card/attack JSON here is the authoritative id→name source. |
| `notebooks/` | Jupyter exploration (empty). | Throwaway/EDA notebooks. |
| `scripts/` | One-off scripts (empty). | Ad-hoc tooling that isn't a deck or RE script. |
| `data/` | DuckDB / datasets (empty; `just data` opens duckdb here). | Generated data, game logs, training datasets. |
| `tests/` | Pytest (`testpaths = ["tests"]`; not yet created). | Tests for `src/pokemon/`. |

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
- **Enums over magic ints.** Once `src/pokemon/cabt_enums.py` exists, import
  `IntEnum`s instead of writing `if opt["type"] == 7`. The integers' meanings are
  defined by the engine; transcribe from the plan doc, verify empirically.
- Style: ruff, line length 100, double quotes, target py314. Type-check with pyright.
- Commit messages end with the `Co-Authored-By` trailer.

## Known rough edges (don't be surprised)

- **Stale option labels:** `pokemon.catalog.format_option` and
  `pokemon.agent.score_option` still use the older reverse-engineered type→label
  mapping, which is partly wrong vs the engine's real `OptionType` (e.g. it treats
  7=ATTACH/8=USE; the engine says 7=PLAY/8=ATTACH). Fixing this is Phase 1 of the
  plan doc.
- **`docs/CABT.md` is partly wrong:** its option-type table predates the official
  enums and mislabels some `OptionType`s (e.g. 7/8). When it conflicts with
  `docs/000_plan_engine_enum_extraction.md`, the plan (sourced from the engine
  docs) wins. Reconcile when touched.

## Start-here reading order

1. This file.
2. `docs/000_plan_engine_enum_extraction.md` — the current plan + full enum reference + ABI.
3. `docs/CABT.md` — observation shape (treat the option-type table with suspicion).
4. `reverse-engineering/README.md` — how to extract more from the engine.
5. `src/pokemon/agent.py` + `catalog.py` — the working reference agent.
