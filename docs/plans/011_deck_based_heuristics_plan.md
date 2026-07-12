# 011 — Deck-based heuristics: right library first, then consumption

**Tickets:** PKM-021 (done 2026-07-12), PKM-023 (in-progress — closes with Phase 2's eval),
PKM-024 (done 2026-07-12, Phase 1), new tickets for Phase 3 when it starts.
**Builds on:** plan 010 (library + identifier — both built), plan 007 (the heuristic tiers),
`heuristic_loop/` (the validation discipline every phase must pass through).

---

## Status — updated 2026-07-12 (end of first implementation session)

| Phase | State |
|---|---|
| 0 — housekeeping | **Half done.** PKM-021 fixed and closed. PKM-023's non-regression check was NOT run separately — it is folded into Phase 2's pending eval (the hook now has a consumer, so a standalone "inert hook" check is moot). |
| 1 — replay library | **Done, gate passed.** `scripts/extract_replay_decks.py` built (re-runnable); 137 unique lists → 67 bot archetypes merged into `library.json` (89 archetypes total, dual-source). Eval over 3,000 perspectives: level 1 40% (1190/1190 exact matches **correct**), level 2 52% (84% correct), level 3 8% — vs. baseline 2%/10%/89% with **zero** correct commits. PKM-024 closed. |
| 2 — targeting swap | **Code done, gate pending.** `_matchup_bucket` built + wired into both targeting rules; 77/77 tests pass. Win-rate eval blocked on WSL ("insufficient system resources" — reboot/free RAM). **Nothing committed until this gate.** |
| 3 — threat profile | Not started. |
| 4 — playbooks | Not started; go/no-go after Phase 3. Human-tournament archetypes only (principle 5). |

**Moving forward, in order:**

1. Restore WSL, then run the one gate that unblocks everything:
   `uv run python heuristic_loop/eval_heuristic_change.py -g 60 --old-ref HEAD`.
   Pass → commit + `heuristic_loop/CHANGELOG.md` entry, close PKM-023. Fail → diagnose via
   a loss batch before reverting anything (the belief may be right and a *rule* wrong).
2. **Latch removal is deferred and measured, not aesthetic** (decided 2026-07-12): after
   step 1 passes, optionally run a second eval with `archetype_latch` disabled; delete it
   only on a ~zero delta. Until then it stays — it covers the detector's blind spots
   (level-3 fringe, stale-library windows between refreshes).
3. Build Phase 3 (`ThreatProfile`) — the load-bearing phase for near-term rank now that
   principle 5 caps hand-written investment in the current pool. Consume one decision point
   per eval cycle, in the order listed in Phase 3 below.
4. Refresh cadence: re-run `extract_replay_decks.py` after every new
   `download_replays.py` batch; revisit `--replay-weight` (and the human half's relevance)
   as the deadline approaches.

## The situation in three sentences (as written 2026-07-12, pre-implementation)

We have a rule-based Dragapult agent (61% win rate, loop-validated) whose only matchup
adaptation is a hand-written 11-deck signature table that changes attack targeting and nothing
else. We also have a proper Bayesian deck identifier (`deck_id.py`) that nothing consumes —
and offline eval proved that against the current opponent pool it identifies almost nothing
(89% no-match) and is wrong essentially every time it does commit, because its library holds
*human tournament* lists while our opponents are *other competitors' bot submissions*.
Meanwhile our own replay analysis shows those opponents use only **137 unique 60-card lists**
(top 20 cover 82% of games), all fully visible in replays we already downloaded — so the
correct library is sitting on disk, unextracted.

**Direction decided (2026-07-12):** deck-based heuristics is the way forward. That makes the
replay-extracted library the foundation (un-park PKM-024 now), with each consumption step
gated by measured win rate, never assumption.

## Principles

1. **Identify → know → act, in that order.** No heuristic consumes deck identity until the
   identifier is proven accurate on the current pool (Phase 1 gate).
2. **Prefer computed knowledge over hand-written knowledge.** Once the opponent's exact list
   is known, threat facts (max damage, gust availability, bench snipe) are derivable from the
   card catalog for all 137 decks at once. Hand-write only what can't be derived (posture,
   deny-piece) — and only for human-tournament archetypes (see principle 5).
3. **Every behavior change goes through `heuristic_loop/eval_heuristic_change.py`** and gets a
   `CHANGELOG.md` entry — same discipline that produced 42% → 61%.
4. **The flat rule list survives.** Rules gain smarter *inputs* (belief, threat profile);
   we do not fork per-deck rule sets. A per-deck rule registry would duplicate the ~80% of
   logic that is matchup-invariant and multiply every future loop fix by N.
5. **Replay-extracted (bot) decks are recognition-only** (decided 2026-07-12, Luqman's call
   on review). They earn their keep in the identifier — a list entry only matches an opponent
   actually playing it, and is inert otherwise — but receive **no hand-crafted strategy
   investment**: new hand-written matchup knowledge (priority-target entries, Phase 4
   playbooks) is written for **human-tournament archetypes only**, since low-elo bot brews
   are expected to vanish as we climb / the meta netdecks toward the deadline. Bot brews get
   computed knowledge only (Phase 3 threat profiles, which derive from any identified list at
   zero marginal effort). The pre-existing bot-meta `TIER5_SIGNATURES`/
   `TIER5_PRIORITY_TARGETS` tables predate this rule: keep as fallback, don't extend.

---

## Phase 0 — Housekeeping (half a day)

1. **Fix PKM-021**: `heuristics.py:prizes_remaining()` → `len(player.get("prize") or [])`.
   Check no caller depends on the broken always-0 behavior first. Prize math feeds any future
   pacing logic; it is currently lying.
   → **Done 2026-07-12.** `_boss_orders_wins_game` confirmed the only consumer; test fixtures
   switched to realistic `None`-filled prize arrays (the old fixture was masking the bug), so
   existing tests double as regression coverage. Ticket closed.
2. **Close PKM-023**: run the pending win-rate non-regression check for the (additive,
   currently inert) `deck_belief_update` hook via `eval_heuristic_change.py`. Expected: no
   delta. This was the last open acceptance item on the ticket.
   → **Superseded 2026-07-12:** the hook is no longer inert (Phase 2 consumes it), so this
   check is folded into Phase 2's win-rate gate — one eval run settles both.

**Gate:** tests pass; non-regression confirmed. *(Pending — rides on Phase 2's eval.)*

## Phase 1 — The replay-extracted library (PKM-024, un-parked; ~1 day)

Build `scripts/extract_replay_decks.py`:

- Read `data/replays/raw/*.json`; both players' full 60-card submitted lists are visible in
  each replay. Extract, dedupe → the ~137 unique lists, with per-list frequency counts.
- Group lists into archetypes by unique-Pokémon-set fingerprint (reuse/adapt
  `scripts/analyze_meta.py`'s logic); compute per-archetype core/flex the same way
  `fetch_limitless_decks.py` does.
- Merge into `data/meta_decks/library.json` under **source tags** (`"replays"` vs
  `"limitless_550"`). Keep both populations — the human lists become relevant again if the
  meta drifts toward netdecks near the deadline (the original PKM-024 thesis). Identifier
  priors weight by source: replay frequency now, re-weightable later.
- Script must be **re-runnable**: the pool shifts as competitors resubmit and we climb the
  ladder. Refreshing the library = re-download replays (PKM-007 tooling) + re-run this script.

**Gate (the cheap falsification point):** re-run `scripts/eval_deck_identifier.py` against all
1,500 replays. Success = level-1 (exact list) identification becomes the common case **and**
its conclusions are actually correct (target: ≥70% of perspectives at level 1/2 by game end,
exact matches overwhelmingly `exact_hit`). Compare against the current baseline in
`data/meta_decks/deck_id_eval_report.txt` (2% level-1, all wrong). If accuracy does not jump,
**stop here and rethink the direction** — nothing downstream has been built yet.

→ **Done 2026-07-12, gate passed decisively:** level 1+2 = 92% (target ≥70%); level-1 40%
with 1190/1190 exact matches correct (baseline: 54/54 wrong); archetype read by mean turn
2.1, exact list by mean turn 7.3. Full numbers in `tickets/PKM-024.md` and the regenerated
`data/meta_decks/deck_id_eval_report.txt` (old report in git history). Caveat recorded:
in-sample eval (library built from the pool it's scored on) — which is also the deployment
scenario. Library artifact tests updated for the dual-source format.

## Phase 2 — First consumption: targeting swap (~1 day + eval time)

The smallest real behavior change, on the decision the old system already handles.
**As built (2026-07-12)**, with one deliberate divergence from the original sketch: no
per-archetype entries were added for the replay-library names (the sketch's first bullet) —
which also keeps principle 5 satisfied, since that would have been new hand-crafted knowledge
keyed to bot decks. Instead, `_matchup_bucket` classifies the belief's *predicted decklist*
(exact list at level 1, core+flex at level 2) through the existing `TIER5_SIGNATURES` name
table — targeting knowledge stays in one place, works for any library source, and survives
archetype renames on re-extraction:

- `boss_orders_target` and `bench_spread_target` resolve the matchup as: identifier belief
  (classified via `_tier5_bucket_from_names`) first, old `archetype_latch` as fallback. The
  old latch is **not deleted** until parity is shown. Net effect: the same priority targets,
  available by ~turn 2 instead of only after a signature Pokemon is physically played.
- Covered by 5 synthetic tests (belief-over-latch, both fallback paths, no-signal case, and
  a pre-signature integration test); full suite green (77 passed).
- **Since split into its own module** (2026-07-12, no behavior change): the identification/
  classification machinery (`TIER5_SIGNATURES`/`TIER5_PRIORITY_TARGETS`, `archetype_latch`,
  `deck_belief_update`, `_matchup_bucket`) moved verbatim to `src/pokemon/dragapult_matchups.py`,
  separate from the decision rules that consume it in `heuristics_dragapult.py`. Pure move,
  verified via `ruff check` (clean on unused imports/undefined names) and `py_compile`; full
  `pytest` run still pending the same WSL outage blocking Phase 2's gate below.

**Gate (pending — WSL down at build time):** `eval_heuristic_change.py -g 60 --old-ref HEAD`
— non-regression required, gain expected. CHANGELOG entry. The same run settles PKM-023's
outstanding non-regression check (Phase 0 item 2).

## Phase 3 — Derived threat profile (2–3 days, incremental)

`ThreatProfile` computed from `identified_list()` minus observed reveals + the card catalog:

- Opponent's max plausible damage next turn (their attackers × attack table × energy state).
- Gust risk: `opp_remaining("Boss's Orders" / "Counter Catcher")` — is dragging our damaged
  benched Dragapult out still possible?
- Bench-snipe / spread capability; item lock; energy acceleration.

Consumed one decision point at a time, each its own loop cycle:

1. Safe benching / bench sizing (don't bench a damaged, energized attacker into live gust;
   cap bench vs spread decks).
2. `munkidori_defensive_heal`'s survival math (it already estimates opponent damage from the
   visible active only — the known list makes this exact).
3. Retreat / promote decisions informed by what the opponent can actually do next turn.

**Gate:** each consumption change individually measured; revert anything that doesn't pay.

## Phase 4 — Posture playbooks (explicit go/no-go, decide after Phase 3)

Hand-written per-archetype posture (race vs. conserve, setup deadline, deny-piece),
consumed as dials by existing rules. Per principle 5, playbooks are written for
**human-tournament archetypes only** (the likely deadline meta) — never for replay-extracted
bot brews, however frequent they are on today's ladder; those get only Phase 3's computed
profiles. **Do not start** unless Phases 2–3 showed measurable wins — this is where
effort/payoff is least certain, and plan 009's search track may be the better spend by then.

## Interaction with everything else

- **`heuristic_loop` batches continue throughout** — still the main ladder-rank lever; this
  plan's phases ride inside that cycle, not instead of it.
- **Determinization** (plan 009): once Phase 1's identifier is trustworthy,
  `determinize.py`'s placeholder opponent-side sampler should switch to
  `identified_list()` minus reveals — that was always its intended endpoint.
- **BC/PPO (PKM-008/009/010):** unaffected; still parked behind the off-by-one label fix.
- **Strategy writeup:** Phase 1's eval numbers (before/after library swap) are exactly the
  kind of figure the report score wants — keep the old report file for the comparison.

## Risks

- **Library staleness:** the pool refreshes as competitors resubmit. Mitigated by the
  re-runnable extraction script; refresh alongside each new replay download batch.
- **Belief threshold tuning:** too eager → wrong-archetype targeting (the current human-library
  failure mode, reintroduced); too shy → falls back to latch and nothing changes. Phase 1's
  eval report gives the data to pick the threshold offline.
- **Meta drift toward human lists near the deadline** is the scenario the dual-source library
  already covers — re-weight priors, don't rebuild.
