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

**Phase: Dragapult ex heuristic agent live-validated and iterating; deck-based heuristics (plan 011) mid-build.**

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

**Deck-based heuristics (plan 011, supersedes plan 010's Phase 3) is the active track.** Plain-
language version: `docs/STRATEGY.md`. Status by phase, as of 2026-07-12:

- **Phase 0 (housekeeping) — done.** **PKM-021 fixed:** `heuristics.py:prizes_remaining()` now
  returns `len(player.get("prize") or [])` — prize array entries are `None` even for *untaken*
  prizes (hidden from the owner too); only the array's length shrinks as prizes are taken. This
  was making `_boss_orders_wins_game`'s "does this KO actually end the game" check vacuous
  (behaved like plain "is this KO lethal"). PKM-023's separate non-regression check is folded
  into Phase 2's win-rate gate below (same eval run settles both).
- **Phase 1 (replay-extracted library, PKM-024) — done, gate passed decisively.** The original
  opponent-identification problem: `deck_id.py`'s `DeckIdentifier` (PKM-023) was built against a
  *human tournament* library (PKM-022, 22 archetypes from a 179-player Limitless Regional) and
  was nearly blind against our actual Kaggle opponents (89% no-read, wrong whenever it did
  commit) — bots play their own low-elo brews, not tournament lists. `scripts/extract_replay_decks.py`
  (new, re-runnable) mines the 1,500 already-downloaded replays for the ~137 unique 60-card lists
  our opponents actually submit, clusters them into 67 bot archetypes, and merges them into
  `data/meta_decks/library.json` under `source: "replays"` tags, alongside the original
  `"limitless_550"` human archetypes (89 archetypes total, dual-source; `--replay-weight` controls
  the identifier's prior split, default 0.85 to replays). Both halves are kept — replays identify
  today's actual opponents, the human half becomes relevant again if the meta netdecks toward the
  deadline. Re-eval over 3,000 perspectives (`scripts/eval_deck_identifier.py`,
  `data/meta_decks/deck_id_eval_report.txt`): level 1+2 (exact list or archetype known) = **92%**
  of games by mean turn 2.1 for archetype / 7.3 for exact list, with **zero** wrong exact-match
  commits (1190/1190 correct) — vs. the old baseline's 2%/10%/89% with zero correct commits.
- **Phase 2 (targeting swap) — code done, win-rate gate still pending (blocked on WSL).** The
  smallest real behavior change: `boss_orders_target`/`bench_spread_target` now resolve the
  matchup via `_matchup_bucket` — the deck-id belief (classified through the existing
  `TIER5_SIGNATURES` name table) preferred over the old `archetype_latch` board-observation read,
  which only fired once a signature Pokémon was physically seen in play. Net effect: the same
  hand-written priority targets, available from ~turn 2 instead of only after a signature card
  shows up (turn 8+, or never). No new hand-written matchup knowledge was added for replay-extracted
  (bot) archetypes — per the plan's principle 5, bot brews get *computed* knowledge only (Phase 3),
  hand-written investment is reserved for human-tournament archetypes. **Gate:**
  `eval_heuristic_change.py -g 60 --old-ref HEAD` — non-regression required, gain expected; not
  yet run (WSL unavailable — "insufficient system resources", needs reboot/RAM freed). **Nothing
  from Phase 0-2 is committed yet** — the plan's own rule is nothing lands until this gate passes.
  The identification/classification machinery (`TIER5_SIGNATURES`/`TIER5_PRIORITY_TARGETS`,
  `archetype_latch`, `deck_belief_update`, `_matchup_bucket`) has since been split out of
  `heuristics_dragapult.py` into its own module, `src/pokemon/dragapult_matchups.py` — a pure
  move, no behavior change, verified via `ruff check` + `py_compile` (full `pytest` run still
  pending the same WSL outage).
- **Reference doc, not yet consumed by the live in-game detector:** `docs/tournament_archetype_cores.md` —
  hand-verified (not formula-derived; two formula attempts both surfaced noise, see the file's
  git history/session notes) defining Pokémon per archetype, e.g. Dragapult → Dragapult ex,
  Raging Bolt Ogerpon → Raging Bolt ex. Originally scoped to the 20 human-tournament archetypes
  only; extended 2026-07-12 with 8 more entries (Archaludon, Hop's Phantump, Iono's Bellibolt,
  Spheal Walrein, Crustle, Comfey, Mega Abomasnow, Ethan's Cyndaquil) found missing by
  `scripts/classify_replay_decks.py` (below) — 29 archetypes total now. A follow-up overlap check
  found the 5 archetypes already covered by `TIER5_SIGNATURES` (alakazam, mega_lucario,
  n_zoroark, cynthia_garchomp, grimmsnarl, plus the mirror bucket) account for **~59% of all bot
  game-instances**, while every currently-uncovered *human* archetype combined adds up to only
  ~1.3% — i.e. expanding the signature table further is low-value *right now* given today's bot
  pool, though the reference doc will matter more once the meta shifts toward human lists. Still
  not wired into `deck_id.py`/`_matchup_bucket` — those consume `library.json`'s computed cores,
  not this hand-verified doc; the doc is currently only consumed by the offline classifier below.
- **Full-information archetype-core classifier:** `scripts/classify_replay_decks.py` /
  `data/meta_decks/archetype_core_match_report.txt` (2026-07-12) — a simpler, offline sanity
  check on `tournament_archetype_cores.md` distinct from `eval_deck_identifier.py`'s incremental
  partial-reveal belief eval. Since every replay already exposes both players' complete 60-card
  lists, this just checks per-deck whether a known archetype's core Pokémon (matched by name,
  any printing — apostrophe-normalized against the catalog's curly quotes) is a subset of the
  deck. No hidden-info modeling. First run: only 60% of the 3,000 bot game-instances matched a
  known core (40% "unmatched" — turned out to be real, recurring, unnamed decks, not noise).
  After adding the 8 archetypes above: **98% matched, 2% ambiguous (decks legitimately running
  two full cores at once), <1% unclassified.** Re-runnable; re-run after any replay refresh or
  `tournament_archetype_cores.md` edit.
- **Phase 3 (derived threat profile) — not started.** The load-bearing next phase per the plan:
  computed (not hand-written) opponent threat facts — max plausible damage next turn, gust risk,
  bench-snipe capability — derived from `identified_list()` + the card catalog, consumed one
  decision point at a time (safe benching first).
- **Phase 4 (posture playbooks) — explicit go/no-go, not started**, gated on Phase 3 showing
  measurable wins; human-tournament archetypes only per principle 5.

`src/pokemon/determinize.py` (plan 009 Phase 1) is a separate, smaller piece already built — a
legal-and-consistent hidden-zone sampler for a future decision-time search (`SearchBegin`),
currently a placeholder resample-from-revealed-cards for the opponent side; `identified_list()`
is meant to replace that placeholder once Phase 2's gate confirms the belief is trustworthy in
practice (see PKM-023 "Downstream" in its ticket).

**Still not started:** behavioral cloning / PPO (PKM-008–010) — the heuristic agent remains the
nearer-term improvement over random while that track waits. The **off-by-one `selected` bug**
(see Known issues below) must be fixed before any BC training, or every label will be shifted by
one decision.

Next actions in order:

1. Restore WSL, then run the one gate that unblocks everything: `eval_heuristic_change.py -g 60
   --old-ref HEAD`. Pass → commit Phases 0-2 + the `dragapult_matchups.py` split, close PKM-023,
   `heuristic_loop/CHANGELOG.md` entry. Fail → diagnose via a loss batch before reverting (the
   belief may be right and a *rule* wrong).
2. Build **Phase 3** (`ThreatProfile`) — see `docs/plans/011_deck_based_heuristics_plan.md` for
   the ordered decision points (safe benching first).
3. Keep running the **heuristic_loop** batch → fix → validate cycle against fresh losses as the
   agent plays more games — this is the main lever on ladder rank right now.
4. Refresh cadence: re-run `extract_replay_decks.py` after every new `download_replays.py` batch.
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
| `src/pokemon/heuristics.py` | Deck-agnostic heuristic agent framework (`Ctx`, `_build_ctx`, `_option_card_id`, `make_heuristic_agent(deck, rules)`) — falls back to random. `Ctx` carries a `state: dict` that persists across every decision in one game (owned by the agent closure, reset on deck submission) for heuristics that need cross-turn memory. `HEURISTIC_SETS["dragapult"]` is registered here (imports from `heuristics_dragapult.py` at the bottom of the file to avoid a circular import). Also home to `prizes_remaining()` — fixed PKM-021, returns `len(player.get("prize") or [])` |
| `src/pokemon/heuristics_dragapult.py` | Dragapult ex deck-specific heuristics (PKM-017/007), all five tiers of `docs/plans/007_heuristics_logic_plan.md`, live-iterated via `heuristic_loop/` (see "Current phase" and `heuristic_loop/CHANGELOG.md`). Tier 5 matchup identification/classification (the signature table, the belief hook, the latch) has been split out into `dragapult_matchups.py` — this file now only holds the decision rules that consume it (`boss_orders_target`, `bench_spread_target`, etc.) |
| `src/pokemon/dragapult_matchups.py` | Tier 5 matchup identification/classification, extracted from `heuristics_dragapult.py` (plan 011, no behavior change): `TIER5_SIGNATURES`/`TIER5_PRIORITY_TARGETS` (hand-written signature + priority-target tables), `archetype_latch` (board-observation detection hook), `deck_belief_update` (PKM-023 hook, maintains `ctx.state["deck_id"]`), `_matchup_bucket` (plan 011 Phase 2 resolver — prefers the deck-id belief over the latch) |
| `src/pokemon/deck_id.py` | PKM-023: `DeckIdentifier` — Bayesian-elimination belief over `data/meta_decks/library.json` from the opponent's cumulative revealed cards. Three-level API: `archetype_belief()`, `opp_remaining(card_id)`, `p_in_hand(card_id)`, `identified_list()`. Consumed by `dragapult_matchups._matchup_bucket` (plan 011 Phase 2) |
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
| `scripts/classify_replay_decks.py` | Full-information archetype-core classifier (no hidden-info modeling, distinct from `eval_deck_identifier.py`): checks each replay's known 60-card list against `docs/tournament_archetype_cores.md`'s core Pokémon (name match, apostrophe-normalized). Writes `data/meta_decks/archetype_core_match_report.txt` |
| `scripts/extract_replay_decks.py` | PKM-024 / plan 011 Phase 1: mines `data/replays/raw/*.json` for the ~137 unique 60-card lists our bot opponents actually submit, clusters into archetypes by unique-Pokemon-set fingerprint, computes core/flex, merges into `data/meta_decks/library.json` under `source: "replays"` tags alongside the human `"limitless_550"` half. Re-runnable/idempotent (drops and rebuilds only the replay-tagged archetypes each run); `--replay-weight` (default 0.85) sets the identifier's prior split between the two sources |
| `scripts/process_cards.py` | Processes `data/EN_Card_Data.csv` (2022 rows, one per move) into one-row-per-card CSVs: `data/cards_processed.csv` (1267 cards), `cards_pokemon.csv` (1056), `cards_trainer.csv` (191), `cards_energy.csv` (20). Run: `python scripts/process_cards.py --no-duckdb` |
| `data/meta_decks/library.json` | Dual-source: PKM-022's 22 human-tournament archetypes (179-list Limitless Regional) plus PKM-024's 67 replay-extracted bot archetypes (137 unique lists from the 1,500 downloaded replays), 89 archetypes total. Each tagged `source: "limitless_550"` or `"replays"`; `meta_share` = within-source share × source weight (`--replay-weight` in `extract_replay_decks.py`, default 0.85 to replays) |
| `heuristic_loop/` | PKM-019/020's log-driven improvement loop: `run_batch.py` → `prepare_analysis.py` → fix → `eval_heuristic_change.py` → `CHANGELOG.md`. See `heuristic_loop/README.md` and "Current phase" above for the first real result (42% → 61% win-rate) |
| `docs/plans/000_plan_engine_enum_extraction.md` | Plan to add full enum awareness (SelectType, SelectContext) |
| `docs/plans/001_training_pipeline.md` | Replay format, featurization spec, network architecture, training strategy |
| `docs/plans/007_heuristics_logic_plan.md` | Dragapult ex five-tier heuristic logic plan — what `heuristics_dragapult.py` implements |
| `docs/plans/008_review_implementation_plan.md` / `008a_review_brief.md` | Review-driven heuristic gap-closing (feeds the `heuristic_loop` batches) |
| `docs/plans/009_native_search_plan.md` | Decision-time search over the native engine (`SearchBegin`) — Phase 1 (`determinize.py`) done, later phases not started |
| `docs/plans/010_meta_deck_library_plan.md` | Meta deck library + in-game opponent identification (PKM-022/023/024) — original plan; Phase 3 (consumption) superseded by plan 011 |
| `docs/plans/011_deck_based_heuristics_plan.md` | Deck-based heuristics: replay-extracted library first, then gated consumption (targeting swap, threat profile, posture playbooks) — this is the plan behind the "Deck-based heuristics" section above. Plain-language version: `docs/STRATEGY.md` |

**Known issues:**
- ~~PKM-004~~ Fixed: OptionType 7/8 swap in `catalog.py`
- ~~PKM-006~~ Fixed: `selected` in Kaggle replays encodes card serials in some `Card/*` contexts (Switch, SetupActivePokemon, Night Stretcher ToHand). ~10% of frames are marked `valid=False` and skipped by the featurizer. `Main/Main` frames (56%) are all valid.
- ~~PKM-021~~ Fixed (2026-07-12): `heuristics.py:prizes_remaining()` always returned 0 — real `obs` data shows prize-array entries are `None` whether or not that prize has been taken (a prize's contents are hidden even from its own owner until taken); what actually signals a taken prize is the array *shrinking*. Was making `_boss_orders_wins_game` in `heuristics_dragapult.py` vacuous (behaved like plain "is this KO lethal", dropping the "and it actually ends the game" half of its purpose). Fixed to `len(player.get("prize") or [])`. Not yet committed (rides with the rest of plan 011 Phase 0-2 pending the win-rate gate).
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
| `docs/STRATEGY.md` | Plain-language living overview of the whole strategy — what we have, why, what's next. **Update it whenever the strategy meaningfully changes** | Strategy-level changes, milestone results |
| `docs/tournament_archetype_cores.md` | Hand-verified defining Pokemon per human-tournament archetype (`library.json`'s `"limitless_550"` half) — not formula-derived; used as the reference for judging which archetypes are worth hand-writing matchup knowledge for (plan 011 principle 5) | Corrections/additions to the human-archetype reference |
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

- **Active:** PKM-023 (in-progress, opponent deck identifier — Phase 2 targeting swap code done,
  win-rate gate pending on WSL)
- **Done, uncommitted:** PKM-021 (bug, `prizes_remaining()`), PKM-024 (replay-extracted library
  merge) — both fixed/built this session but ride with PKM-023's pending gate before committing
- **Backlog, not started:** PKM-008/009/010 (BC/PPO), PKM-011 (deck eval), PKM-014/015
  (MCTS/ISMCTS search)
- **Superseded:** PKM-016–019 (Psychic-deck-era work, dropped when the deck switched to Dragapult)

See `TICKETS.md` for the full, current list.

---

## Conventions

- **Decks are canonical in `pokemon.decks`** — numbered `deck/NNN_*` artifacts document them
- **Card/attack names** from `reverse-engineering/data/` via `pokemon.catalog` — no hand-typed maps
- **Enums over magic ints** — use `src/pokemon/cabt_enums.py` (not yet used everywhere it could be — `catalog.py`'s `format_option` still branches on raw ints)
- Style: ruff, line length 100, double quotes, py314. Type-check with pyright
- Commit messages end with the `Co-Authored-By` trailer
