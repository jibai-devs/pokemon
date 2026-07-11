# 010 — Meta deck library from human tournament data + in-game opponent identification

**Tickets:** PKM-022 (library), PKM-023 (identifier), PKM-024 (future: replay-list refresh)
**Feeds:** PKM-015 / plan 009 determinization (hidden-zone priors), Tier 5 replacement in
`heuristics_dragapult.py`, deck-score writeup (Strategy competition, 20% weight)

---

## Why

The current opponent-adaptation mechanism (`archetype_latch` +
`TIER5_PRIORITY_TARGETS` in `heuristics_dragapult.py`) is a hard one-shot
classification into ten hand-written buckets, and the only thing it changes is
Boss's Orders / Phantom Dive targeting. Two empirical findings (2026-07-11)
say we can do far better:

1. **The opponent pool is a lookup table, not a distribution.** Across all
   3,000 deck instances in the 1,500 downloaded replays there are only **137
   unique exact 60-card lists**; the top 20 cover 82% of games and 91% of
   instances use a list seen ≥10 times. Every opponent is another
   competitor's fixed submission — identifying the list means knowing all 60
   cards, which collapses the hidden-information game (exact card counting,
   hand probabilities, and near-exact determinization for `SearchBegin`).

2. **Human tournament lists are the better library source.** The current
   Kaggle bot meta (Cinderace/Mega Starmie 25%, Archaludon, Hop's decks) barely
   overlaps the human tournament meta for the same card pool
   (https://limitlesstcg.com/tournaments/550/statistics — Regional Melbourne,
   179 players: Dragapult 39%, Festival Lead, Raging Bolt, Ogerpon Box,
   Rocket's Honchkrow, N's Zoroark, Hydrapple, Slowking, Rocket's Mewtwo,
   Alakazam). Today's replay pool is low-elo (it's where our submissions
   start); as competitors improve and netdeck toward the deadline, the bot
   meta should drift toward the human meta. Spot-check confirms every headline
   tournament Pokémon exists in the competition's 1,267-card catalog.

**Decision (2026-07-11):** build the library from Limitless tournament lists.
Replay-extracted lists are deliberately **out of scope** — they're the current
low-elo pool, worth merging only once we climb the ladder / as a
pre-deadline refresh (PKM-024).

## Architecture: three levels of graceful degradation

The identifier maintains a belief over the library and exposes whatever
precision the evidence supports:

- **Level 1 — exact list match:** opponent reveals are consistent with one
  known 60-card list. `opp_remaining(card)` is an exact count;
  `p_in_hand(card)` is hypergeometric over the known remaining deck.
- **Level 2 — archetype core match:** reveals match an archetype's **core**
  (cards in ≥90% of that archetype's lists) but no single list. We know
  ~45–50 of their 60 cards plus the game plan; flex slots are ranges.
  Similarity weights Pokémon evolution lines and the draw engine heavily,
  trainers lightly — engines (Dudunsparce line, Starmie shell) recur across
  decks and are the most identity-revealing cards.
- **Level 3 — true fringe:** nothing matches. Fall back to per-Pokémon threat
  defaults computed from the card catalog (max damage vs our HPs, own HP,
  prize value). Even here, engine recognition usually still fires — novel
  decks borrow known consistency engines.

One mechanism (Bayesian elimination over lists/cores) produces all three
levels; consumers just read the belief's concentration.

## Phase 1 — Scrape + ingest (PKM-022)

`scripts/fetch_limitless_decks.py`:

- Fetch `https://limitlesstcg.com/tournaments/550/decklists` (and
  `/statistics`); cache raw HTML under `data/meta_decks/raw/` so re-parsing
  never re-hits the site. Parameterize tournament ID — more events in this
  format can be added later.
- Parse each player's list: `count, card name, [set code]` per line, three
  sections (Pokémon / Trainer / Energy). Verify each list sums to 60.
- **Name → competition card ID mapping** against `data/cards_processed.csv`
  (+ `pokemon.catalog` fallback). Set codes don't exist in the competition
  catalog, so matching is by name with a **validation report**: every scraped
  name either maps to exactly one competition ID, or is flagged
  (unmapped / ambiguous multi-print) for manual resolution in a small
  override map checked into the script. **No silent best-effort matching** —
  a list only enters the library fully resolved.
- Output `data/meta_decks/library.json`:
  `{archetype: {lists: [{player, placing, cards: {id: count}}], core: {id: count}, flex: [...], meta_share, source_url}}`
  with cores/flex computed per archetype (core = present in ≥90% of the
  archetype's lists at min count).

Acceptance: library contains the top ~10 archetypes from tournament 550 with
every card resolved to a competition ID; validation report empty or every
entry consciously resolved; a `pytest` test loads the library and asserts
60-card sums and non-empty cores.

## Phase 2 — In-game identifier (PKM-023)

`src/pokemon/deck_id.py`:

- Track opponent-revealed cards cumulatively in `ctx.state` (visible zones:
  active/bench/discard/stadium/attached; plus anything the obs reveals when
  played). Counting duplicates matters — 3 seen Dreepy is stronger evidence
  than 1.
- Belief = consistency scoring: a candidate list/core is eliminated (or
  down-weighted) when reveals exceed its counts; among survivors, weight by
  tournament meta share as the prior.
- API for heuristics and search:
  - `archetype_belief() -> dict[str, float]`
  - `opp_remaining(card_id) -> (lo, hi, expected)` — exact at level 1
  - `p_in_hand(card_id) -> float | None` — hypergeometric, level 1/2 only
  - `identified_list() -> dict[int, int] | None`
- Replace `archetype_latch`/`TIER5_SIGNATURES` as the Tier 5 mechanism:
  `TIER5_PRIORITY_TARGETS` keys move onto library archetypes; latch becomes a
  soft belief read (keep the latch as a fallback until parity is shown).
- **Offline eval harness** (no engine needed): drive the identifier with the
  1,500 replays' reveal sequences and measure (a) by which turn the belief
  concentrates, (b) level-1/2/3 distribution, (c) accuracy vs the known
  submitted deck. Note: bot decks mostly won't exact-match tournament lists —
  this measures level-2/3 fallback quality, which is exactly what we need to
  trust before the meta drifts.

Acceptance: identifier tests pass on synthetic reveal sequences; offline eval
report checked into `data/meta_decks/`; heuristic win-rate not regressed
(`heuristic_loop/eval_heuristic_change.py`).

## Phase 3 — Consumers (separate work, listed for orientation)

- **Determinization** (plan 009 / PKM-015): sample hidden zones for
  `SearchBegin` from `identified_list()` minus reveals instead of an
  archetype guess.
- **Per-archetype playbooks / posture layer**: win condition, setup deadline,
  piece-to-deny per library archetype — hand-written from tournament-list
  knowledge, consumed as posture dials by existing heuristics. Plan
  separately once the identifier exists.
- **Deck-score writeup**: the human-tournament grounding of our own deck
  choice (Dragapult = 39% of Regional Melbourne) goes in the Strategy report.

## Out of scope

- Replay-extracted lists (the 137) — PKM-024, revisit when climbing ranks or
  as a pre-deadline refresh; the level-2/3 fallback covers unmatched bot
  decks meanwhile.
- The full per-Pokémon threat table beyond the computed level-3 defaults.
- Any BC/PPO interaction.

## Risks

- **Format mismatch:** some tournament cards may not exist in the competition
  pool despite headline Pokémon existing. The validation report catches this
  at ingest; lists with truly unavailable cards get flagged, not silently
  trimmed.
- **Name ambiguity:** multiple prints share a name (e.g. two `Cinderace`
  entries in the catalog). Resolved via the override map; ambiguities are
  loud, not guessed.
- **Meta drift both ways:** the bot meta may *not* converge to tournament
  lists. Mitigation is PKM-024's refresh — the library format accepts lists
  from any source, so merging replay lists later is additive, not a redesign.
- **Scrape brittleness / site ToS:** raw HTML is cached; parsing is offline
  and re-runnable. Keep request volume minimal (a handful of pages, once).
