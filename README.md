# Pokémon TCG AI Battle

An agent for the **Pokémon TCG AI Battle** Kaggle competition (CABT engine), plus the tooling
we built to collect training data and analyze the meta. Full project context, engine API notes,
and conventions live in [`AGENTS.md`](AGENTS.md) (`CLAUDE.md` symlinks to it) — this README is a
quicker "what's done, what to run" overview for teammates picking this up.

Tracking is done via lightweight tickets in [`TICKETS.md`](TICKETS.md) / [`tickets/`](tickets/).
Below is a walkthrough grouped by what each batch of work actually accomplished.

## Status at a glance

**Submitted:** a heuristic agent for the Psychic deck (PKM-017), encoding Slowking's Seek
Inspiration win condition. Confirmed win rate over the random baseline in local batches; a
real Kaggle loss (PKM-019) surfaced a heuristic gap since fixed, not yet re-validated (see
[Still open](#still-open)).
**In progress:** log-driven heuristic improvement loop (PKM-019) — reading real game logs to
find and fix specific heuristic mistakes; training data pipeline — replays downloaded and meta
analyzed; featurization and behavioral cloning are the next unclaimed work.

## What's been built

### 1. Competition submission (PKM-001, PKM-002, PKM-003)

The competition needs a self-contained `.tar.gz` with `main.py` (exposing
`agent(obs_dict) -> list[int]`) and `deck.csv` (60 card IDs, one per line) at the top level —
`main.py` can't import from `src/pokemon/` since only the bundled files exist in the
competition container.

- `main.py` — reads `deck.csv` at import time, returns the deck during the deck-submission
  phase, otherwise picks `maxCount` random legal options. Good enough to pass validation and
  enter matchmaking; not yet using any real strategy.
- `deck.csv` — the current Fire deck (2× Gouging Fire ex, 4× Slugma, 4× Magcargo ex, trainers,
  33× Fire Energy). Canonical deck definition lives in `src/pokemon/decks.py`
  (`FIRE_DECK`) — regenerate `deck.csv` from there if the deck changes.

To rebuild and submit:

```bash
tar -czf submission.tar.gz main.py deck.csv
# Upload under "My Submissions" on the competition page, then check validation status.
```

### 2. Engine correctness fix (PKM-004)

`OptionType` 7 (`PLAY`) and 8 (`ATTACH`) were swapped in `src/pokemon/agent.py` (scoring) and
`src/pokemon/catalog.py` (display labels) relative to the engine's real enum. Fixed — not a
blocker for the random baseline, but needed before any heuristic/learned scoring is meaningful.

### 3. Replay parser (PKM-005, PKM-006)

`scripts/parse_replay.py` turns a Kaggle episode replay JSON (or a locally-run game, via
`--local`, WSL only) into a human-readable, step-by-step decision log — this is the tool used to
understand the replay format and, later, to feed featurization.

```bash
python scripts/parse_replay.py example_replay.json
python scripts/parse_replay.py example_replay.json --max-steps 50
python scripts/parse_replay.py example_replay.json --dump-step 5
```

Along the way we found that the `selected` field (the training label — which option the player
picked) doesn't always mean "index into the option list": for a handful of `Card/*` contexts
(`Switch`, `SetupActivePokemon`, Night Stretcher's `ToHand`) it's actually a card serial number
instead. The parser now validates every sample and flags mismatches with `valid=False`
(~10% of frames in a sample replay) — anything downstream (featurization) must filter on
`valid == True`.

### 4. Training data collection (PKM-007)

`scripts/download_replays.py` bulk-downloads replays from top-rated leaderboard agents to use as
behavioral-cloning training data. Rather than scraping individual submissions, it uses Kaggle's
daily published dataset (`kaggle/pokemon-tcg-ai-battle-episodes-<date>`), which ships a
`manifest.csv` per day with each episode's `avg_score` (agent rating) — we sort by that and pull
only the top-N episodes/day instead of a multi-GB full archive.

```bash
uv run python scripts/download_replays.py                      # default: top 100/day, 15 days
uv run python scripts/download_replays.py --top-per-day 100 --out data/replays/raw
```

Already run once: **1,500 replays (top 100/day × 15 days), 4.6GB**, stored in
`data/replays/raw/` (manifests cached in `data/replays/manifests/`). Re-running is resumable —
it skips files already on disk, so it's safe to bump `--top-per-day` and re-run to pull more.

`data/replays/` is **gitignored** (4.6GB is too large to commit) — it's a build artifact you
regenerate locally, not something you pull from git. To get it:

```bash
uv run python scripts/download_replays.py   # ~15-30 min depending on connection; 4.6GB download
```

Once you have it, here's how to actually look at what's inside:

- **Inspect a single replay** (human-readable, step by step): `scripts/parse_replay.py` — see
  the [replay parser](#3-replay-parser-pkm-005-pkm-006) section above.
- **Query across all replays** (deck archetypes, win-rates): `scripts/analyze_meta.py` — see
  the [meta analysis](#6-meta-analysis-pkm-012) section below; it already produces
  `data/meta_report.txt` (which *is* committed) so you don't need the raw replays to see the
  results, only to reproduce or extend the analysis.
- **Raw format**: each file is a Kaggle episode JSON (`ver=2`) — decision steps are at
  `steps[0][0]["visualize"]`, each with `select` (options presented), `selected` (index of the
  option the player picked — the training label), and `current` (full board state). Frame 0's
  `action` field holds both players' 60-card deck submissions. Full field-by-field breakdown is
  in [`docs/plans/001_training_pipeline.md`](docs/plans/001_training_pipeline.md).

### 5. Card dataset processing (PKM-013)

`scripts/process_cards.py` turns the raw card CSV (`data/EN_Card_Data.csv`, one row per *move*,
2022 rows) into clean, one-row-per-*card* datasets used by every other script that needs card
names/types/stats.

```bash
python scripts/process_cards.py            # writes data/cards.duckdb too
python scripts/process_cards.py --no-duckdb
```

Outputs (already generated, committed under `data/`):

| File | Contents |
|---|---|
| `data/cards_processed.csv` | All 1267 cards, one row each, moves as a JSON array |
| `data/cards_pokemon.csv` | Pokémon cards only (1056) |
| `data/cards_trainer.csv` | Trainer cards only (191) |
| `data/cards_energy.csv` | Energy cards only (20) |

### 6. Meta analysis (PKM-012)

`scripts/analyze_meta.py` reads every downloaded replay, extracts each player's submitted 60-card
deck (frame 0), fingerprints it by its unique Pokémon IDs, clusters the 3,000 deck instances
(1,500 replays × 2 players) into archetypes, and reports win-rate + meta share per archetype.

```bash
uv run python scripts/analyze_meta.py                                   # writes data/meta_report.txt
uv run python scripts/analyze_meta.py --replays-dir data/replays/raw --top 15
```

Key findings (full report in [`data/meta_report.txt`](data/meta_report.txt)):

- **Cinderace/Mega Starmie** is the most common archetype (18% meta share, 52% win-rate) — no
  single dominant deck.
- **Archaludon ex (Metal)** is the best-performing archetype at 68% win-rate, though a second,
  distinct Archaludon ex variant only hits 38% — grouping has to be by exact fingerprint, not by
  name, since "Metal" isn't one deck.
- **Our Fire deck doesn't appear in any of the 1,500 replays** — no direct win-rate signal from
  this dataset for our own deck; head-to-head evaluation (PKM-011) will need simulation instead.
- No archetype clears both switch thresholds (>55% win-rate *and* >30% meta share) →
  recommendation from the script: **stay with the Fire deck**.

### 7. Heuristic agent + log-driven improvement loop (PKM-016, PKM-017, PKM-019)

Switched the active deck to Psychic (Mega Kangaskhan ex / Latias ex control-ish shell, win
condition is Slowking's Seek Inspiration) and replaced the random baseline with
`src/pokemon/heuristics.py` — a priority list of small, independently testable rule functions
(`DEFAULT_PSYCHIC_HEURISTICS`), falling back to random when none apply. This is what's live in
`main.py`/`submission.tar.gz` now.

Three real bugs were found by reading actual game traces, not from unit tests alone (see
`AGENTS.md` Known issues and the tickets for details):

- A hand-area option getting overridden by an unrelated `select.deck` entry.
- A multi-card search heuristic under-counting its selection, which the engine accepted
  silently as a draw instead of an error — a whole class of "return < minCount" bugs is now
  guarded against in `make_heuristic_agent`'s dispatch loop.
- Fodder-search heuristics (Ultra Ball/Poke Pad) competing with deck-stacking heuristics
  (Ciphermaniac's Codebreaking) for the same scarce copy targets, undermining the deck's own win
  condition. Fixed by splitting hand-search targets from deck-stacking targets.

A **real Kaggle loss** (`data/recent_log.txt`) surfaced a fourth, subtler gap: Slowking got 6
energy attachments over one game but was never once switched back into the active spot, while
the backup attackers sat active the whole game without enough energy to attack either — zero
attacks fired all game. Fixed (`attach_energy_to_attacker`, `switch_to_backup_attacker`), but not
yet win-rate validated — see [Still open](#still-open).

Reading that replay also surfaced two replay-format bugs serious enough to matter beyond this one
fix: `scripts/parse_replay.py`'s `selected` field turns out to be off by one frame in the Kaggle
export, and its Kaggle-format option labels are area-blind the same way `catalog.format_option`
is. `scripts/analyze_heuristic_logs.py` is a new, deck-agnostic replay analyzer that fixes both —
resolves any card/attack for either player generically, and corrects the off-by-one shift — and
prints a condensed per-turn decision trace instead of raw board-state JSON:

```bash
python scripts/analyze_heuristic_logs.py data/recent_log.txt --player 1
python scripts/analyze_heuristic_logs.py data/recent_log.txt --summary-only
```

## Still open

These are scoped but not yet built — see the linked ticket for the full spec:

| Ticket | What it is |
|---|---|
| [PKM-008](tickets/PKM-008.md) | `scripts/featurize.py` — turn replays into numpy training tensors (state/options/label arrays) |
| [PKM-009](tickets/PKM-009.md) | Behavioral cloning training loop (`train_bc.py`) |
| [PKM-010](tickets/PKM-010.md) | PPO self-play fine-tuning (`train_rl.py`) |
| [PKM-011](tickets/PKM-011.md) | Deck evaluation — assess Fire deck against top archetypes (via simulation, since no direct replay data exists) |
| [PKM-014](tickets/PKM-014.md) | MCTS decision-time search on top of the trained policy |
| [PKM-015](tickets/PKM-015.md) | Opponent belief modeling via archetype determinization (ISMCTS) |
| [PKM-020](tickets/PKM-020.md) | Automated before/after win-rate validation for heuristic changes |

The planned order is featurize → behavioral cloning → PPO fine-tune → deck evaluation, per
`AGENTS.md`'s "Current phase" section.

## Running games locally

The CABT engine (`libcg.so`) is a Linux binary, so local games require **WSL**:

```bash
wsl -e bash -c "cd /mnt/c/Users/Luqman/Desktop/projects/pokemon && ~/.local/bin/uv run python -m pokemon -g 1 -v"
```

See `AGENTS.md` for setup steps, common errors, and the full engine API reference.
