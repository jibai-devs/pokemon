# Pokémon TCG AI Battle — Project Guide

`CLAUDE.md` is a symlink to this file. This is the single reference for any contributor (human or AI) starting cold.

---

## Mission

Build an agent that plays the **Pokémon TCG AI Battle (CABT)** Kaggle competition.  
Prize money ($240K across 8 finalists) is in the linked **Strategy** competition — it requires a working simulation entry **and** a written report.

### Key dates

| Date | Event |
|------|-------|
| Aug 9, 2026 | Simulation entry deadline |
| Aug 16, 2026 | Final simulation submission |
| Sep 13, 2026 | Strategy writeup deadline |

### Scoring (Strategy competition)

| Category | Weight |
|----------|--------|
| Model score (agent performance + leaderboard rank) | 70% |
| Deck score (concept + card choice rationale) | 20% |
| Report score (structure + figures) | 10% |

Middle-leaderboard teams can still win through strong analysis. High rank alone is not enough.

---

## Current phase

**Phase: training data collection + featurization.**

The baseline random agent is submitted. Replay format is confirmed and parser is working.
**PKM-007** (1,500 replays downloaded) and **PKM-012** (meta analysis, recommendation: stay with
Fire deck) are done. The plan is **behavioral cloning → PPO fine-tuning**. Next actions in order:

1. **PKM-008** — featurize replays into numpy tensors (same-deck games only if BC; filter `valid=False`)
2. **PKM-009** — train BC policy; gate on > 70% win-rate vs random
3. **PKM-010** — PPO self-play fine-tuning from BC checkpoint
4. **PKM-011** — deck evaluation (feeds from PKM-012 output)

Do not build the full CORAL coaching pipeline (Task6.md) — useful as a strategy report writeup but out of scope for the Aug 9 deadline.

---

## Current codebase state

| File | Status |
|------|--------|
| `src/pokemon/agent.py` | Clean random agent with verbose logging — baseline only |
| `src/pokemon/decks.py` | Fire deck (Gouging Fire ex + Magcargo ex, 60 cards) |
| `src/pokemon/catalog.py` | Card/attack name lookup + option formatting (enums corrected) |
| `src/pokemon/cli.py` | CLI runner (`pokemon-play` / `python -m pokemon`) |
| `main.py` | Kaggle submission entry point — random agent, reads `deck.csv` |
| `deck.csv` | 60 card IDs for the submission bundle |
| `reverse-engineering/data/` | `all_cards.json` (1267 cards), `all_attacks.json` (1556 attacks) |
| `scripts/parse_replay.py` | Parse a Kaggle replay JSON or run a local game; prints each decision step human-readably. Supports Kaggle ver=2 (string enums, `selected` label) and local (int enums) formats. Marks ~10% of frames `valid=False` where `selected` encodes card serials instead of option-list indices. |
| `scripts/process_cards.py` | Processes `data/EN_Card_Data.csv` (2022 rows, one per move) into one-row-per-card CSVs. Outputs `data/cards_processed.csv` (1267 cards, all), plus split files: `cards_pokemon.csv` (1056), `cards_trainer.csv` (191), `cards_energy.csv` (20). Adds `hp_int`, `retreat_int`, `damage_int` numeric columns and `moves_json` array. Run: `python scripts/process_cards.py --no-duckdb`. |
| `data/EN_Card_Data.csv` | Raw card data (2022 rows, one per move, 17 columns). Source for process_cards.py. |
| `data/cards_processed.csv` | Cleaned card dataset — 1267 cards, one row per card, moves as JSON array. |
| `data/cards_pokemon.csv` | Pokemon cards only (1056): Basic, Stage 1, Stage 2. |
| `data/cards_trainer.csv` | Trainer cards only (191): Item, Supporter, Pokemon Tool, Stadium. |
| `data/cards_energy.csv` | Energy cards only (20): Basic Energy, Special Energy. |
| `docs/000_plan_engine_enum_extraction.md` | Plan to add full enum awareness (SelectType, SelectContext) |
| `docs/001_training_pipeline.md` | Replay format, featurization spec, network architecture, training strategy |

**Known issues:**
- ~~PKM-004~~ Fixed: OptionType 7/8 swap in `catalog.py`
- ~~PKM-006~~ Fixed: `selected` in Kaggle replays encodes card serials in some `Card/*` contexts (Switch, SetupActivePokemon, Night Stretcher ToHand). ~10% of frames are marked `valid=False` and skipped by the featurizer. `Main/Main` frames (56%) are all valid.

---

## Repo layout

| Path | Contents | Put new things here |
|------|----------|---------------------|
| `src/pokemon/` | Installed package. `agent.py`, `catalog.py`, `decks.py`, `cli.py`, `__main__.py` | All shared, reusable code |
| `deck/` | Per-deck artifacts: `NNN_<name>.py` (thin re-export), `NNN_<name>.md` (decklist), gameplay walkthrough | New deck → add to `pokemon.decks`, then artifacts here |
| `docs/` | Engine notes, execution plans (`NNN_plan_*.md`) | Specs, plans, engine notes |
| `reverse-engineering/` | RE cookbook, scripts, `data/` (symbol dumps + card/attack JSON) | Anything about extracting data from `libcg.so` |
| `data/` | DuckDB / datasets (empty; `just data` opens duckdb) | Generated data, game logs, training datasets |
| `notebooks/` | Jupyter exploration | Throwaway EDA notebooks |
| `scripts/` | Ad-hoc tooling | One-off scripts |
| `tests/` | Pytest | Tests for `src/pokemon/` |

The CABT engine is vendored at `.venv/lib/python3.14/site-packages/kaggle_environments/envs/cabt/` — **read-only.**

---

## Setup (one-time, WSL)

The engine (`libcg.so`) is a Linux binary — all game execution requires **WSL (Ubuntu)**.

```bash
sudo apt-get update && sudo apt-get install -y \
  libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev \
  gcc python3-dev
```

Verify `uv` is available in WSL:

```bash
~/.local/bin/uv --version
```

---

## Running games

From a WSL terminal:

```bash
cd /mnt/c/Users/Luqman/Desktop/projects/pokemon

~/.local/bin/uv run python -m pokemon -g 1 -v   # 1 game, verbose
~/.local/bin/uv run python -m pokemon -g 10      # 10 games, summary
```

From PowerShell:

```powershell
wsl -e bash -c "cd /mnt/c/Users/Luqman/Desktop/projects/pokemon && ~/.local/bin/uv run python -m pokemon -g 1 -v"
```

### Common errors

| Error | Fix |
|-------|-----|
| `fatal error: Python.h` | `sudo apt-get install -y python3-dev` |
| `Unable to run "sdl-config"` | `sudo apt-get install -y libsdl2-dev gcc` |
| `404 Not Found` during apt | Run `sudo apt-get update` first |
| `No module named pokemon` | Use `uv run` not bare `python` |

---

## Kaggle submission

Bundle and upload:

```bash
tar -czf submission.tar.gz main.py deck.csv src/
```

- Upload at `pokemon-tcg-ai-battle` on Kaggle
- Up to 5 submissions/day; only the latest 2 are active in matchmaking
- `main.py` must expose `agent(obs_dict) -> list[int]` at the top level
- `deck.csv` must be exactly 60 card IDs, one per line

---

## Engine API (CABT)

Each turn the engine calls your agent with `obs`:

- `obs["select"]` — `None` = deck submission phase; otherwise `{"option": [...], "maxCount": N, "type": ..., "context": ...}`
- `obs["current"]` — full board state: `players`, `turn`, `yourIndex`, `supporterPlayed`, etc.
- Agent returns a list of integer indices into `options`

### OptionType (option.type)

| ID | Name | Fields |
|----|------|--------|
| 0 | NUMBER | `number` |
| 1 | YES (go first) | — |
| 2 | NO (go second) | — |
| 7 | PLAY | `index` (hand) |
| 8 | ATTACH | `area, index, inPlayArea, inPlayIndex` |
| 9 | EVOLVE | `area, index, inPlayArea, inPlayIndex` |
| 10 | ABILITY | `area, index` |
| 11 | DISCARD | `area, index` |
| 12 | RETREAT | — |
| 13 | ATTACK | `attackId` |
| 14 | END | — |

See `docs/000_plan_engine_enum_extraction.md` for the full enum reference (SelectType, SelectContext, AreaType, etc.).

---

## Training data pipeline

Full details in `docs/001_training_pipeline.md`. Summary:

**Kaggle replay format (confirmed from `example_replay.json`):**
- Top-level: `{steps, rewards, statuses, info: {Agents: [{Name}]}, ...}`
- Vis frames at `steps[0][0]["visualize"]` — list of `{select, selected, current, logs, ver:2}`
- `selected` = chosen option indices (training label); `None` for deck submission frame. ~10% of frames encode card serials instead — these are marked `valid=False` by the parser and must be filtered before featurization.
- `select.type` / `opt.type` are **strings**: `'Main'`, `'Card'`, `'YesNo'` / `'Play'`, `'Attack'`, `'End'`, etc.
- Both players' hands fully visible in replay data (opponent hand only hidden at inference)
- Card objects carry inline `name` field — no catalog lookup needed for display
- Area codes in `Card` options: `2=Hand`, `5=Bench`, `6=Prize`, `1/3=Deck search result`

**Getting replays:**
```bash
kaggle competitions episodes <submission-id>   # list episode IDs
kaggle competitions replay <episode-id>        # download episode-XXXXX-replay.json
```

**Parsing replays:**
```powershell
# Pure Python — run anywhere (PowerShell or WSL)
python scripts/parse_replay.py example_replay.json
python scripts/parse_replay.py example_replay.json --max-steps 50
python scripts/parse_replay.py example_replay.json --dump-step 5
```
```bash
# --local requires WSL (spins up libcg.so)
~/.local/bin/uv run python scripts/parse_replay.py --local
```

**Training approach:**
1. Behavioral cloning on top-agent replays — cross-entropy on chosen option index
2. PPO fine-tuning with self-play — value head, reward = game outcome
3. Network scores each option independently; state encoder → `board_vec` (256d), option encoder → `option_vec` (64d), MLP scores each `(board_vec, option_vec)` pair → logit

**Network inputs:** ~434-dim board state + 64-dim per-option. Card/attack IDs → `nn.Embedding`, not one-hot.

---

## Tickets

| ID | Title | Status | Priority |
|----|-------|--------|----------|
| PKM-001 | Create deck.csv | done | high |
| PKM-002 | Create main.py entry point | done | high |
| PKM-003 | Bundle and submit to Kaggle | done | high |
| PKM-004 | Fix OptionType enum (7/8 swap) | done | medium |
| PKM-005 | Build replay parser (parse_replay.py) | done | high |
| PKM-006 | Fix `selected` alignment for Card-type contexts | done | medium |
| PKM-007 | Download top-agent replay batch from Kaggle | done | high |
| PKM-008 | Build featurize.py — replay → training tensors | todo | high |
| PKM-009 | Build behavioral cloning training loop | todo | high |
| PKM-010 | PPO self-play fine-tuning | todo | medium |
| PKM-011 | Deck evaluation — survey meta and assess fire deck | todo | medium |
| PKM-012 | Deck extraction and meta analysis script | done | high |
| PKM-013 | Process Pokemon cards CSV for analytics and ML | done | high |
| PKM-014 | MCTS decision-time search on top of BC/PPO policy | todo | medium |
| PKM-015 | Opponent belief modeling via archetype determinization (ISMCTS) | todo | medium |

Full ticket details in `tickets/`.

---

## Conventions

- **Decks are canonical in `pokemon.decks`** — numbered `deck/NNN_*` artifacts document them
- **Card/attack names** from `reverse-engineering/data/` via `pokemon.catalog` — no hand-typed maps
- **Enums over magic ints** — use `src/pokemon/cabt_enums.py` once it exists
- Style: ruff, line length 100, double quotes, py314. Type-check with pyright
- Commit messages end with the `Co-Authored-By` trailer
