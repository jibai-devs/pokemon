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

**Phase: Dragapult ex heuristic agent built, needs live/WSL validation.**

The baseline random agent is submitted. Replay format is confirmed and parser is working.
**PKM-007** (1,500 replays downloaded) is done. The Dragapult ex deck ("Pult Noir") is registered
in `pokemon.decks.DECKS` (2026-07-08), and a full deck-specific heuristic agent has been built
against `docs/007_heuristics_logic_plan.md` (v2) and `dragapult_deck_explanation.md` (v3) — see
`src/pokemon/heuristics_dragapult.py`, registered as `HEURISTIC_SETS["dragapult"]`. The plan is
still **behavioral cloning → PPO fine-tuning**, with this heuristic agent as the nearer-term
improvement over the random baseline.

**What's implemented (2026-07-08):** all five tiers from the logic plan — Tier 1 setup-phase
priority, Tier 2 mulligan + forced-active-replacement, Tier 3 energy/Munkidori-Darkness routing,
discard sequencing, Supporter tiebreak, Watchtower/Meowth ex sequencing, bench-exposure
discretion, Tier 4 ex-damage-blocker fallback + Boss's Orders/Phantom-Dive-spread targeting +
default attack choice, and Tier 5 archetype-signature latch + per-matchup priority-target
overrides for all ten Section 8 write-ups. Tier 5 is a deliberate simplification: it reuses one
signature-detection + priority-target mechanism across all ten matchups rather than ten fully
bespoke functions — it doesn't implement judgment-heavy prose (Judge's hand-deduction use,
full Battle Cage/stadium awareness), which stays a random-fallback decision by design.
Unit tests for every rule are in `tests/test_heuristics_dragapult.py` (synthetic `obs` dicts, no
engine needed) and pass, along with `ruff`/`pyright` on the new/changed files.

**Not yet done — the real next step:** none of this has been run against the actual engine
(`libcg.so`, WSL-only). Several field-shape assumptions are best-effort and *unverified*
(Phase 2 of `docs/000_plan_engine_enum_extraction.md`): notably which `SelectContext` Boss's
Orders' switch-in and Phantom Dive's bench-spread targeting actually use, and whether CARD-option
`area`/`index` resolve against the opponent's board the way `_resolve_opp_card` assumes. Each
heuristic is written to degrade to `None` (falls back to random) rather than guess wrong, but
this **must be run via `uv run python -m pokemon play -a heuristic -g N -v` in WSL** before
trusting it — watch the verbose log for which heuristics actually fire vs. silently no-op.

Next actions in order:

1. **Run the heuristic agent in WSL** (`play -a heuristic -g 20 -v`) and confirm it doesn't
   crash, that mulligan/setup/forced-switch fire as expected, and that Boss's Orders/bench-spread
   targeting actually resolves opponent cards (the two most speculative field-shape guesses above).
   **Partially done (2026-07-09):** a 1-game smoke test in WSL ran clean (exit 0, no crash,
   `attach_energy`/`active_replacement`/`boss_orders_target` all fired at least once) — a real
   20-game batch with the loop below is still needed.
2. Run PKM-019/PKM-020's log-driven improvement loop, now formalized in `heuristic_loop/`
   (`run_batch.py` → `prepare_analysis.py` → agent reads the bundle → implement a fix →
   `eval_heuristic_change.py` → record in `heuristic_loop/CHANGELOG.md`), against real
   heuristic-agent replays to check which rules fire, which no-op, and where the
   archetype-signature latch and priority targets need correction
3. **PKM-008** — featurize replays into numpy tensors (same-deck games only if BC; filter `valid=False`)
4. **PKM-009** — train BC policy; gate on > 70% win-rate vs random
5. **PKM-010** — PPO self-play fine-tuning from BC checkpoint
6. **PKM-011** — deck evaluation (feeds from PKM-012 output)

Do not build the full CORAL coaching pipeline (Task6.md) — useful as a strategy report writeup but out of scope for the Aug 9 deadline.

---

## Current codebase state

| File | Status |
|------|--------|
| `src/pokemon/agent.py` | `make_agent(deck)` builds a random-legal-move agent bound to any deck; `default_agent` is bound to `ACTIVE_DECK` |
| `src/pokemon/heuristics.py` | Deck-agnostic heuristic agent framework (`Ctx`, `_build_ctx`, `_option_card_id`, `make_heuristic_agent(deck, rules)`) — falls back to random. `Ctx` carries a `state: dict` that persists across every decision in one game (owned by the agent closure, reset on deck submission) for heuristics that need cross-turn memory. `HEURISTIC_SETS["dragapult"]` is registered here (imports from `heuristics_dragapult.py` at the bottom of the file to avoid a circular import) |
| `src/pokemon/heuristics_dragapult.py` | Dragapult ex deck-specific heuristics (PKM-017/007) — all five tiers from `docs/007_heuristics_logic_plan.md`, see "Current phase" above for what's implemented/simplified |
| `src/pokemon/cabt_enums.py` | IntEnum transcription of the engine's real enums (`SelectType`, `SelectContext`, `OptionType`, `AreaType`, ...) — not yet empirically verified (Phase 2 of the enum extraction plan) |
| `src/pokemon/decks.py` | Deck registry (`DECKS`, `ACTIVE_DECK_NAME`/`ACTIVE_DECK`) — `"dragapult"` registered (60 cards, `dragapult_deck_explanation.md` Section 1) |
| `src/pokemon/catalog.py` | Card/attack name lookup + option formatting (enums corrected). `card_info(id)`/`attack_info(id)` return the raw catalog dict (hp, basic/ex/stage flags, evolvesFrom, attacks, weakness/resistance; damage, energies cost) — added for the Dragapult heuristics' breakpoint/energy-cost math |
| `src/pokemon/cli.py` | CLI runner (`pokemon-play` / `python -m pokemon`). `play -a random\|heuristic` picks the agent |
| `tests/test_heuristics.py` | Framework-level tests (fallback-to-random, deck-submission) against synthetic `obs` dicts — runs without WSL/the engine |
| `tests/test_heuristics_dragapult.py` | Tests for every Dragapult-specific rule (mulligan, forced-switch tiers, discard sequencing, ex-attack-blocker, Watchtower/Meowth sequencing, supporter tiebreak, archetype latch + priority targeting) — synthetic `obs` dicts, no engine needed |
| `main.py` | Kaggle submission entry point — random agent, reads `deck.csv` |
| `deck.csv` | 60 card IDs for the submission bundle. Regenerate from the registry with `python -m pokemon export-deck -d <name>` — do not hand-edit |
| `reverse-engineering/data/` | `all_cards.json` (1267 cards), `all_attacks.json` (1556 attacks) |
| `scripts/parse_replay.py` | Parse a Kaggle replay JSON or run a local game; prints each decision step human-readably. Supports Kaggle ver=2 (string enums, `selected` label) and local (int enums) formats. Marks ~10% of frames `valid=False` where `selected` encodes card serials instead of option-list indices. **Does not yet correct the off-by-one `selected` bug — see Known issues.** |
| `scripts/analyze_heuristic_logs.py` | Deck-agnostic Kaggle-replay analyzer (PKM-019). Corrects the off-by-one `selected` bug and resolves any card option's zone (hand/bench/active/deck/discard/prize) for either player generically — not hardcoded to any deck. Prints a condensed per-turn decision trace + end-of-game summary (option-type counts, attacks used, picks by select context). `python scripts/analyze_heuristic_logs.py <replay.json> --player N` |
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
- **Open, higher priority than it looks** (found during PKM-019, 2026-07-06): the Kaggle replay format's `selected` field is **off by one frame** — the option chosen for the decision at `vis[i]` is actually stored on `vis[i + 1]["selected"]`, not `vis[i]["selected"]`. Confirmed empirically: shifting recovers a valid in-range selection for 182/183 decisions in one real game vs. 151/183 unshifted (mostly coincidental overlap, not signal). `scripts/parse_replay.py` and PKM-006's `valid` flag do **not** account for this — they can look "valid" while reporting the wrong choice. `scripts/analyze_heuristic_logs.py` applies the shift; **fix this in `parse_replay.py`/the featurization plan (PKM-008) too before any behavioral-cloning training**, or BC will train on misaligned labels.
- **Open** (found during PKM-017): `catalog.format_option` always indexes into `hand` for OptionType 3/7, regardless of the option's `area` field — mislabels bench/active/deck-area options in verbose logs (e.g. a legitimate bench switch shows the wrong card name). Doesn't affect which option actually gets chosen, only log readability. Fix by threading board state into `format_option` and branching on `area`. (`scripts/analyze_heuristic_logs.py` has its own generic, area-aware resolver and isn't affected; `catalog.format_option` itself, used by the local-format verbose CLI, is still unfixed.)
- **Note:** `submission.tar.gz` must bundle `reverse-engineering/data/*.json`, or any `catalog` data-backed lookup (e.g. `min_attack_energy_cost`) silently returns empty/`None` on Kaggle — see the bundling command below. This bit PKM-019 once already (fixed 2026-07-06); re-check it any time catalog-dependent heuristics are added for the new deck.
- The Psychic-deck-specific heuristics (PKM-017/019/021: Seek Inspiration targeting, fodder-stacking, energy/switch logic for Slowking) were deleted along with the Psychic deck on 2026-07-08 — see git history before this date if any of that logic is worth reusing for the new deck.

---

## Repo layout

| Path | Contents | Put new things here |
|------|----------|---------------------|
| `src/pokemon/` | Installed package. `agent.py`, `heuristics.py`, `cabt_enums.py`, `catalog.py`, `decks.py`, `cli.py`, `__main__.py` | All shared, reusable code |
| `deck/` | Per-deck artifacts: `NNN_<name>.py` (thin re-export), `NNN_<name>.md` (decklist), gameplay walkthrough | New deck → add to `pokemon.decks`, then artifacts here |
| `docs/` | Engine notes, execution plans (`NNN_plan_*.md`) | Specs, plans, engine notes |
| `reverse-engineering/` | RE cookbook, scripts, `data/` (symbol dumps + card/attack JSON) | Anything about extracting data from `libcg.so` |
| `data/` | DuckDB / datasets (empty; `just data` opens duckdb) | Generated data, game logs, training datasets |
| `notebooks/` | Jupyter exploration | Throwaway EDA notebooks |
| `scripts/` | Ad-hoc tooling | One-off scripts |
| `heuristic_loop/` | Log-driven heuristic improvement loop (PKM-019/PKM-020): run a batch, bundle losses for an agent to read, validate a change's win-rate, `CHANGELOG.md` context page | Anything about iterating on `heuristics_dragapult.py` from real game logs — see `heuristic_loop/README.md` |
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

~/.local/bin/uv run python -m pokemon play -g 1 -v            # 1 game, verbose, active deck
~/.local/bin/uv run python -m pokemon play -g 10               # 10 games, summary
~/.local/bin/uv run python -m pokemon play -d <name> -g 10     # override deck for this run
~/.local/bin/uv run python -m pokemon export-deck -d <name>    # regenerate deck.csv from the registry
```

From PowerShell:

```powershell
wsl -e bash -c "cd /mnt/c/Users/Luqman/Desktop/projects/pokemon && ~/.local/bin/uv run python -m pokemon play -g 1 -v"
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
tar -czf submission.tar.gz main.py deck.csv src/ reverse-engineering/data/all_cards.json reverse-engineering/data/all_attacks.json
```

The two catalog JSON files are required — without them, `pokemon.catalog`'s
data-backed lookups (card/attack names beyond the hardcoded override map,
`min_attack_energy_cost`) silently return empty/`None` on Kaggle. Missing
until 2026-07-06 (see PKM-019); rebuild any older `submission.tar.gz` before
relying on catalog-dependent heuristics.

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
- **`selected` is also off by one frame** (found PKM-019, 2026-07-06): the true label for the decision at `vis[i]` lives on `vis[i + 1]["selected"]`, not `vis[i]`. Not yet corrected in `parse_replay.py` or accounted for in this pipeline's plan — must be fixed before featurization/BC training (PKM-008/009), or every label will be shifted by one decision.
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
| PKM-011 | Deck evaluation — survey meta and assess new deck | todo | medium |
| PKM-012 | Deck extraction and meta analysis script | done | high |
| PKM-013 | Process Pokemon cards CSV for analytics and ML | done | high |
| PKM-014 | MCTS decision-time search on top of BC/PPO policy | todo | medium |
| PKM-015 | Opponent belief modeling via archetype determinization (ISMCTS) | todo | medium |
| PKM-016 | Switch active deck to Psychic and add a central deck registry | superseded | high |
| PKM-017 | Build a modular heuristic-based agent (Psychic-specific rules) | superseded | high |
| PKM-018 | Build a card/attack reference sheet for the Psychic deck | superseded | medium |
| PKM-019 | Log-driven heuristic improvement loop | superseded | medium |
| PKM-020 | Automated before/after win-rate validation for heuristic changes | todo | medium |

Full ticket details in `tickets/`.

---

## Conventions

- **Decks are canonical in `pokemon.decks`** — numbered `deck/NNN_*` artifacts document them
- **Card/attack names** from `reverse-engineering/data/` via `pokemon.catalog` — no hand-typed maps
- **Enums over magic ints** — use `src/pokemon/cabt_enums.py` (not yet used everywhere it could be — `catalog.py`'s `format_option` still branches on raw ints)
- Style: ruff, line length 100, double quotes, py314. Type-check with pyright
- Commit messages end with the `Co-Authored-By` trailer
