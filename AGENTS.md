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

**Phase: Dragapult ex heuristic agent live-validated and iterating; opponent-modeling layer under construction.**

The baseline random agent is submitted. Replay format is confirmed and parser is working.
**PKM-007** (1,500 replays downloaded) is done. The Dragapult ex deck ("Pult Noir") is registered
in `pokemon.decks.DECKS`, and a full deck-specific heuristic agent covering all five tiers of
`docs/plans/007_heuristics_logic_plan.md` is built — see `src/pokemon/heuristics_dragapult.py`,
registered as `HEURISTIC_SETS["dragapult"]`. Unlike the earlier phase, this has now actually been
**run against the real engine in WSL and iterated on real losses**, not just unit-tested.

**Log-driven iteration loop is live and has already paid off (PKM-019/PKM-020, `heuristic_loop/`):**
`run_batch.py` plays N games in WSL → `prepare_analysis.py` bundles losses → an agent (or the
`analyze-heuristic-losses` skill) reads the bundle and logs every questionable decision →
implement a fix → `eval_heuristic_change.py` measures win-rate delta old-vs-new via `git worktree`
→ record the finding/change/validation in `heuristic_loop/CHANGELOG.md` (append-only, don't rewrite
past entries). The first real batch (2026-07-10, `heuristic_loop/logs/20260710_122935`, 30 games/13
losses) found four recurring gaps — a legal Item/Supporter never competing with a legal Attack for
the turn, an `attach_energy` short-circuit defeating its own attacker-line priority, Crispin's two
sub-decisions and Crushing-Hammer-vs-retreat-cost discard both falling entirely to random — fixed
them and validated **42% → 61% win-rate over 120 games**. See `CHANGELOG.md` for the full writeup;
that's the template every future heuristic change should follow (finding cited by game/turn, not
"seemed suboptimal"; a measured win-rate delta, not an assumption).

**Opponent modeling (plan 010, PKM-022/023/024) is now under construction alongside the loop:**
the current matchup-adaptation mechanism (`archetype_latch` + `TIER5_SIGNATURES`, a 10-bucket
hand-written signature table keyed to the *low-elo bot* meta) is being supplemented — not yet
replaced — by a belief system built from *human tournament* decklists. **PKM-022 (done):**
`data/meta_decks/library.json`, scraped from a 179-player Regional (Limitless), 22 archetypes,
Dragapult itself the #1 human archetype at 39% share. **PKM-023 (in-progress):**
`src/pokemon/deck_id.py`'s `DeckIdentifier` — Bayesian elimination over that library from the
opponent's cumulative revealed cards, three graceful-degradation levels (exact list → archetype
core → true fringe). Wired in additively (`deck_belief_update` populates `ctx.state["deck_id"]`
every decision) but **not yet consumed by any targeting heuristic** — the library's human-meta
archetype names don't overlap `TIER5_SIGNATURES`' bot-meta keys, so swapping Tier 5 over needs a
per-archetype playbook mapping (deferred, plan 010 Phase 3) plus a win-rate parity check first.
Offline eval against all 1,500 replays (`scripts/eval_deck_identifier.py`) shows the honest
picture: today's bot pool mostly doesn't match tournament lists (89% stay at fringe/level 3), which
is exactly why PKM-024 (merging replay-extracted lists into the library) is parked until the ladder
climbs or a pre-deadline refresh. `src/pokemon/determinize.py` (plan 009 Phase 1) is a separate,
smaller piece already built — a legal-and-consistent hidden-zone sampler for a future decision-time
search (`SearchBegin`), currently a placeholder resample-from-revealed-cards for the opponent side;
`identified_list()` from PKM-023 is meant to replace that placeholder once trustworthy (see PKM-023
"Downstream" in its ticket).

**Known open bug (PKM-021):** `heuristics.py:prizes_remaining()` always returns 0 — the prize array
is `None`-filled even for untaken prizes (only its *length* shrinks as prizes are taken), so
`_boss_orders_wins_game`'s "does this KO actually end the game" check is currently vacuous
(behaves like plain "is this KO lethal"). One-line fix (`len()` not a `None`-filtered count), not
yet applied — check no other caller depends on the current broken behavior first.

**Still not started:** behavioral cloning / PPO (PKM-008–010) — the heuristic agent remains the
nearer-term improvement over random while that track waits. The **off-by-one `selected` bug**
(see Known issues below) must be fixed before any BC training, or every label will be shifted by
one decision.

Next actions in order:

1. Fix **PKM-021** (`prizes_remaining`) — cheap, currently corrupting one win-detection heuristic.
2. Confirm **PKM-023**'s win-rate non-regression via `heuristic_loop/eval_heuristic_change.py` (not
   yet run this ticket — the additive `deck_belief_update` hook is low-risk but unconfirmed).
3. Keep running the **heuristic_loop** batch → fix → validate cycle against fresh losses as the
   agent plays more games — this is the main lever on ladder rank right now.
4. Decide whether/how to wire `DeckIdentifier` into Tier 5 targeting (needs a playbook mapping from
   library archetypes to priority targets — plan 010 Phase 3, not started).
5. **PKM-008** — featurize replays into numpy tensors (same-deck games only if BC; filter
   `valid=False`; fix the off-by-one `selected` bug first)
6. **PKM-009** — train BC policy; gate on > 70% win-rate vs random
7. **PKM-010** — PPO self-play fine-tuning from BC checkpoint
8. **PKM-011** — deck evaluation (feeds from PKM-012 output)

Do not build the full CORAL coaching pipeline (Task6.md) — useful as a strategy report writeup but out of scope for the Aug 9 deadline.

---

## Current codebase state

| File | Status |
|------|--------|
| `src/pokemon/agent.py` | `make_agent(deck)` builds a random-legal-move agent bound to any deck; `default_agent` is bound to `ACTIVE_DECK` |
| `src/pokemon/heuristics.py` | Deck-agnostic heuristic agent framework (`Ctx`, `_build_ctx`, `_option_card_id`, `make_heuristic_agent(deck, rules)`) — falls back to random. `Ctx` carries a `state: dict` that persists across every decision in one game (owned by the agent closure, reset on deck submission) for heuristics that need cross-turn memory. `HEURISTIC_SETS["dragapult"]` is registered here (imports from `heuristics_dragapult.py` at the bottom of the file to avoid a circular import). Also home to `prizes_remaining()` — **currently broken, see PKM-021 below** |
| `src/pokemon/heuristics_dragapult.py` | Dragapult ex deck-specific heuristics (PKM-017/007), all five tiers of `docs/plans/007_heuristics_logic_plan.md`, live-iterated via `heuristic_loop/` (see "Current phase" and `heuristic_loop/CHANGELOG.md`). `deck_belief_update` (PKM-023) also registered here — populates `ctx.state["deck_id"]` but not yet consumed by any targeting rule |
| `src/pokemon/deck_id.py` | PKM-023: `DeckIdentifier` — Bayesian-elimination belief over `data/meta_decks/library.json` from the opponent's cumulative revealed cards. Three-level API: `archetype_belief()`, `opp_remaining(card_id)`, `p_in_hand(card_id)`, `identified_list()`. Not yet wired into any targeting heuristic (see "Current phase") |
| `src/pokemon/determinize.py` | Plan 009 Phase 1: `sample_determinization(obs, my_deck)` builds a legal, composition-consistent guess for every hidden zone the native `SearchBegin` search needs. Own side is exact (we know our 60-card list); opponent side is a placeholder resample-from-revealed-cards, meant to eventually be replaced by `deck_id.identified_list()` |
| `src/pokemon/cabt_enums.py` | IntEnum transcription of the engine's real enums (`SelectType`, `SelectContext`, `OptionType`, `AreaType`, `CardType`, ...) — not yet empirically verified (Phase 2 of the enum extraction plan) |
| `src/pokemon/decks.py` | Deck registry (`DECKS`, `ACTIVE_DECK_NAME`/`ACTIVE_DECK`) — `"dragapult"` registered (60 cards, `dragapult_deck_explanation.md` Section 1) |
| `src/pokemon/catalog.py` | Card/attack name lookup + option formatting (enums corrected). `card_info(id)`/`attack_info(id)` return the raw catalog dict (hp, basic/ex/stage flags, evolvesFrom, attacks, weakness/resistance; damage, energies cost) — used by the Dragapult heuristics' breakpoint/energy-cost math and `deck_id`'s Pokemon-vs-Trainer weighting |
| `src/pokemon/cli.py` | CLI runner (`pokemon-play` / `python -m pokemon`). `play -a random\|heuristic` picks the agent |
| `tests/test_heuristics.py` | Framework-level tests (fallback-to-random, deck-submission) against synthetic `obs` dicts — runs without WSL/the engine |
| `tests/test_heuristics_dragapult.py` | Tests for every Dragapult-specific rule — synthetic `obs` dicts, no engine needed |
| `tests/test_deck_id.py` | PKM-023: `DeckIdentifier` against a synthetic library — elimination, level transitions, exact/range remaining counts, hypergeometric `p_in_hand`, Pokemon-vs-Trainer weighting, plus a smoke test against the real library |
| `tests/test_determinize.py` | `sample_determinization` against synthetic `obs` (exact invariants) and real captured logs (structural sanity) |
| `tests/test_meta_deck_library.py` | PKM-022: sanity checks on the built `library.json` (loads, every list sums to 60, cores non-empty, Dragapult is top archetype) |
| `main.py` | Kaggle submission entry point — random agent, reads `deck.csv` |
| `deck.csv` | 60 card IDs for the submission bundle. Regenerate from the registry with `python -m pokemon export-deck -d <name>` — do not hand-edit |
| `reverse-engineering/data/` | `all_cards.json` (1267 cards), `all_attacks.json` (1556 attacks) |
| `scripts/parse_replay.py` | Parse a Kaggle replay JSON or run a local game; prints each decision step human-readably. Supports Kaggle ver=2 (string enums, `selected` label) and local (int enums) formats. Marks ~10% of frames `valid=False` where `selected` encodes card serials instead of option-list indices. **Does not yet correct the off-by-one `selected` bug — see Known issues.** |
| `scripts/analyze_heuristic_logs.py` | Deck-agnostic Kaggle-replay analyzer (PKM-019). Corrects the off-by-one `selected` bug and resolves any card option's zone (hand/bench/active/deck/discard/prize) for either player generically. Prints a condensed per-turn decision trace + end-of-game summary. `python scripts/analyze_heuristic_logs.py <replay.json> --player N` |
| `scripts/download_replays.py` | Bulk-downloads episode replays via the Kaggle API into `data/replays/raw/` (1,500 currently downloaded) |
| `scripts/analyze_meta.py` | Fingerprints replay decks into archetypes by unique Pokemon-id set, reports count/win-rate/key-Pokemon per archetype (`data/meta_report.txt`) — the *bot-meta* counterpart to `fetch_limitless_decks.py`'s human-tournament meta |
| `scripts/fetch_limitless_decks.py` | PKM-022: scrapes a Limitless tournament's decklists, maps card names to competition IDs via exact `(set, number)` lookup against `data/cards_processed.csv` (falls back to name matching for basic energies/off-catalog reprints), computes per-archetype cores/flex, writes `data/meta_decks/library.json`. Loud, nonzero-exit on any unmapped/ambiguous card — no silent matching |
| `scripts/eval_deck_identifier.py` | PKM-023: offline eval harness — drives `DeckIdentifier` with the 1,500 replays' reveal sequences (no engine needed), reports level distribution, turn-of-first-concentration, and accuracy vs. the actual submitted list. Writes `data/meta_decks/deck_id_eval_report.txt` |
| `scripts/process_cards.py` | Processes `data/EN_Card_Data.csv` (2022 rows, one per move) into one-row-per-card CSVs: `data/cards_processed.csv` (1267 cards), `cards_pokemon.csv` (1056), `cards_trainer.csv` (191), `cards_energy.csv` (20). Run: `python scripts/process_cards.py --no-duckdb` |
| `data/meta_decks/library.json` | PKM-022 output: 22 archetypes from a 179-list Regional, cores/flex/meta-share per archetype. Dragapult is #1 at 39% |
| `heuristic_loop/` | PKM-019/020's log-driven improvement loop: `run_batch.py` → `prepare_analysis.py` → fix → `eval_heuristic_change.py` → `CHANGELOG.md`. See `heuristic_loop/README.md` and "Current phase" above for the first real result (42% → 61% win-rate) |
| `docs/plans/000_plan_engine_enum_extraction.md` | Plan to add full enum awareness (SelectType, SelectContext) |
| `docs/plans/001_training_pipeline.md` | Replay format, featurization spec, network architecture, training strategy |
| `docs/plans/007_heuristics_logic_plan.md` | Dragapult ex five-tier heuristic logic plan — what `heuristics_dragapult.py` implements |
| `docs/plans/008_review_implementation_plan.md` / `008a_review_brief.md` | Review-driven heuristic gap-closing (feeds the `heuristic_loop` batches) |
| `docs/plans/009_native_search_plan.md` | Decision-time search over the native engine (`SearchBegin`) — Phase 1 (`determinize.py`) done, later phases not started |
| `docs/plans/010_meta_deck_library_plan.md` | Meta deck library + in-game opponent identification (PKM-022/023/024) — this is the plan behind the "Opponent modeling" paragraph above |

**Known issues:**
- ~~PKM-004~~ Fixed: OptionType 7/8 swap in `catalog.py`
- ~~PKM-006~~ Fixed: `selected` in Kaggle replays encodes card serials in some `Card/*` contexts (Switch, SetupActivePokemon, Night Stretcher ToHand). ~10% of frames are marked `valid=False` and skipped by the featurizer. `Main/Main` frames (56%) are all valid.
- **PKM-021, open:** `heuristics.py:prizes_remaining()` always returns 0 — real `obs` data shows prize-array entries are `None` whether or not that prize has been taken (a prize's contents are hidden even from its own owner until taken); what actually signals a taken prize is the array *shrinking*. This makes `_boss_orders_wins_game` in `heuristics_dragapult.py` vacuous (behaves like plain "is this KO lethal", dropping the "and it actually ends the game" half of its purpose). Fix is `len(player.get("prize") or [])`, not a `None`-filtered count — not yet applied.
- **Open, higher priority than it looks** (found during PKM-019, 2026-07-06): the Kaggle replay format's `selected` field is **off by one frame** — the option chosen for the decision at `vis[i]` is actually stored on `vis[i + 1]["selected"]`, not `vis[i]["selected"]`. Confirmed empirically: shifting recovers a valid in-range selection for 182/183 decisions in one real game vs. 151/183 unshifted. `scripts/parse_replay.py` and PKM-006's `valid` flag do **not** account for this. `scripts/analyze_heuristic_logs.py` applies the shift; **fix this in `parse_replay.py`/the featurization plan (PKM-008) too before any behavioral-cloning training**, or BC will train on misaligned labels.
- **Open** (found during PKM-017): `catalog.format_option` always indexes into `hand` for OptionType 3/7, regardless of the option's `area` field — mislabels bench/active/deck-area options in verbose logs. Doesn't affect which option actually gets chosen, only log readability. (`scripts/analyze_heuristic_logs.py` has its own generic, area-aware resolver and isn't affected.)
- **Note:** `submission.tar.gz` must bundle `reverse-engineering/data/*.json`, or any `catalog` data-backed lookup (e.g. `min_attack_energy_cost`) silently returns empty/`None` on Kaggle — see the bundling command below. This bit PKM-019 once already; re-check it any time catalog-dependent heuristics are added.
- The Psychic-deck-specific heuristics (PKM-017: Seek Inspiration targeting, fodder-stacking, energy/switch logic for Slowking — *not* the current PKM-021, which is an unrelated bug ticket reusing that number range) were deleted along with the Psychic deck on 2026-07-08 — see git history before this date if any of that logic is worth reusing.

---

## Repo layout

| Path | Contents | Put new things here |
|------|----------|---------------------|
| `src/pokemon/` | Installed package. `agent.py`, `heuristics.py`, `heuristics_dragapult.py`, `deck_id.py`, `determinize.py`, `cabt_enums.py`, `catalog.py`, `decks.py`, `cli.py`, `__main__.py` | All shared, reusable code |
| `deck/` | Everything about the current deck: `NNN_<name>.py` (thin re-export), `NNN_<name>.md` (decklist), `decklist.md`, gameplay walkthrough (`dragapult_deck_explanation.md`) | New deck → add to `pokemon.decks`, then artifacts here |
| `docs/plans/` | Numbered execution plans (`NNN_plan_*.md`) — see the codebase-state table above for what each one covers | New design/execution plans |
| `docs/CABT.md` | Engine/environment reference notes | Engine notes |
| `reverse-engineering/` | RE cookbook, scripts, `data/` (symbol dumps + card/attack JSON) | Anything about extracting data from `libcg.so` |
| `data/` | Card CSVs, `replays/raw/` (1,500 downloaded episodes), `meta_decks/` (PKM-022 library + PKM-023 eval report) | Generated data, game logs, training datasets |
| `notebooks/` | Jupyter exploration | Throwaway EDA notebooks |
| `scripts/` | Ad-hoc tooling — replay parsing/analysis, meta scraping (`fetch_limitless_decks.py`), deck-id offline eval | One-off scripts |
| `heuristic_loop/` | Log-driven heuristic improvement loop (PKM-019/PKM-020): run a batch, bundle losses for an agent to read, validate a change's win-rate, `CHANGELOG.md` context page | Anything about iterating on `heuristics_dragapult.py` from real game logs — see `heuristic_loop/README.md` |
| `tests/` | Pytest | Tests for `src/pokemon/` |
| `tickets/`, `TICKETS.md` | Per-ticket detail files + the summary index — canonical ticket tracking (see "Tickets" below) | New tickets, per the format in the top-level `~/Desktop/projects/CLAUDE.md` |

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

See `docs/plans/000_plan_engine_enum_extraction.md` for the full enum reference (SelectType, SelectContext, AreaType, etc.).

---

## Training data pipeline

Full details in `docs/plans/001_training_pipeline.md`. Summary:

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

Canonical index is **`TICKETS.md`** (one-line summary table, always current) with full detail per
ticket in `tickets/PKM-NNN.md` — don't duplicate the table here, it will just drift out of sync
again (this file's copy did, badly, before this update). Highlights as of this writing:

- **Active:** PKM-021 (bug, `prizes_remaining()`), PKM-023 (in-progress, opponent deck identifier)
- **Backlog, not started:** PKM-008/009/010 (BC/PPO), PKM-011 (deck eval), PKM-014/015
  (MCTS/ISMCTS search), PKM-024 (merge replay lists into the meta library, parked until the ladder
  climbs)
- **Superseded:** PKM-016–019 (Psychic-deck-era work, dropped when the deck switched to Dragapult)

See `TICKETS.md` for the full, current list.

---

## Conventions

- **Decks are canonical in `pokemon.decks`** — numbered `deck/NNN_*` artifacts document them
- **Card/attack names** from `reverse-engineering/data/` via `pokemon.catalog` — no hand-typed maps
- **Enums over magic ints** — use `src/pokemon/cabt_enums.py` (not yet used everywhere it could be — `catalog.py`'s `format_option` still branches on raw ints)
- Style: ruff, line length 100, double quotes, py314. Type-check with pyright
- Commit messages end with the `Co-Authored-By` trailer
