# 008 — Review Implementation Plan (post-`008a_review_brief.md`)

Source: `docs/plans/008a_review_brief.md` (external implementation-review brief for the Dragapult ex /
Munkidori heuristic agent), reconciled against the actual state of
`src/pokemon/heuristics_dragapult.py` and `docs/plans/007_heuristics_logic_plan.md`.
Everything in the brief is wanted eventually — this doc orders it and notes
where the brief's assumptions don't match this codebase.

**Ground rule for all of this:** the engine (`libcg.so`) hands the agent one
legal-option menu per real decision — there is no exposed forward model
(`simulate_actions`/`apply_action`/`wins_game`) the agent can roll forward
speculatively. The brief's "shallow search" modules (Lethal Line Finder,
Boss+Munkidori+Attack search, beam search) assume that primitive. It doesn't
exist and building it is a separate, large project (effectively
re-implementing or repeatedly re-invoking the real rules engine). Until that
exists, those modules are **out of scope** — approximate their value with
closed-form derived-state checks over the current option menu instead. This
is the one place this plan deviates from the brief's own recommendation
bias.

**Sequencing principle (per user 2026-07-10):** heuristics first. Everything
below is heuristic-rule work — no search infra, no opponent simulation — so
it can all proceed in the order listed without unblocking on anything else.
Validate every change through the existing `heuristic_loop/` before/after
win-rate harness (PKM-020) before marking it done, same discipline as the
`fa87ffe` batch.

**Status (2026-07-10): Phase 1, Phase 2, and Phase 3's first batch are
implemented, tested, and validated — see their sections below for what
changed.**

**Repo state a fresh agent should know before starting Phase 3:**
- Phase 1 + 2 changes are **uncommitted** in the working tree (not yet on a
  commit) — `git status` will show `src/pokemon/heuristics.py`,
  `src/pokemon/heuristics_dragapult.py`, and
  `tests/test_heuristics_dragapult.py` as modified. Don't discard them;
  build Phase 3 on top, and check with the user before committing anything
  (Phase 1/2 haven't been committed yet either — that's a decision for the
  user, not implied by this doc).
- `tests/test_heuristics_dragapult.py` now has 36 tests (was 21), all
  passing (`PYTHONPATH=src python -m pytest tests/ -q` — no WSL/engine
  needed for unit tests).
- The win-rate harness (`heuristic_loop/eval_heuristic_change.py`) needs
  WSL (`wsl bash -lc "cd /mnt/c/.../pokemon && export UV_LINK_MODE=copy &&
  uv run python heuristic_loop/eval_heuristic_change.py -g <N>"`) since
  `libcg.so` is Linux-only. It's noisy at low N — both runs draw fresh
  unseeded random games each invocation, so even the *same* OLD version's
  win rate bounced 50%→58%→63% across separate runs at n=30-60. Don't trust
  single small-N deltas; n=120 is a more reasonable floor, and the verdict
  line's naive `delta<0 → REVERT` shouldn't be taken literally without
  checking whether |delta| clears the noise band for that N.

---

## Phase 1 — Chain preservation + Munkidori defense (highest ROI, do first) — ✅ DONE

These are pure derived-state predicates, no new engine capability needed.

1. **`_breaks_dragapult_chain(ctx)` predicate.** Answers "does taking this
   action forgo the energy/Supporter needed to Phantom Dive next turn."
   Wire into:
   - `supporter_tiebreak` — block/penalize Boss's Orders when Crispin is
     chain-critical this turn (currently `_energy_short` only checks energy
     count, not whether Boss is about to consume the turn that should've
     gone to Crispin).
   - `boss_orders_target` — fold as a negative term alongside the existing
     lethal/matchup-priority scoring tuple.
2. **Munkidori defensive-heal rule.** Currently `attach_energy`'s Darkness
   routing is offense-only (gates on `opp_damaged`). Add a rule for the
   "move damage FROM my board" source-select step: if Dragapult (or the
   only live attacker) is one Adrena-Brain shift away from surviving an
   opponent KO next turn, that outranks any offensive Munkidori use this
   turn.
3. **Munkidori KO threshold in Phantom Dive allocation.** `bench_spread_target`
   has one flat `<=60` tier. Add a `<=30` ("one Adrena-Brain can finish")
   tier above it, per `docs/plans/008a_review_brief.md`'s threshold table.
4. **Strengthen `_boss_orders_has_payoff`.** Currently "can my current
   attack KO a benched target" — extend to check whether the resulting KO
   actually ends the game (`prizes_remaining`), which is the cheap,
   menu-local approximation of `docs/plans/008a_review_brief.md`'s Lethal Finder that's actually
   buildable without a simulator.

Regression tests for each, added to `tests/test_heuristics_dragapult.py`
alongside the change (already the house style — see the 21 existing tests).

**Implemented as:** `_breaks_dragapult_chain` (gates `supporter_tiebreak`'s
Boss's Orders pick, folded into `boss_orders_target`'s scoring tuple as
`chain_risk`), `munkidori_defensive_heal` (new heuristic, registered right
before `bench_spread_target`), a `<=30` HP tier in `bench_spread_target`'s
`_hp_tier`, and `_boss_orders_wins_game` (uses the new deck-agnostic
`prizes_remaining` helper in `heuristics.py`) overriding the chain gate when
Boss's Orders would win outright. 8 new tests.

**Validated:** win-rate harness runs were noisy at n=30-60 (swung from
+25pp down to -20pp across runs); the honest read is "no clear signal
against a random-move opponent" — plausible since these are edge-case rules
(energy-short-plus-Crispin-in-hand, near-lethal defense) a random opponent
rarely triggers coherently. Kept anyway: each rule is independently
correctness-justified (closed-form, degrades to `None` safely) and the loop
of interest is really Phase 3's real-loss-driven evidence, not aggregate
win-rate against random.

---

## Phase 2 — Boss/energy tightening (once Phase 1 is validated) — ✅ DONE

5. **Two-prize weighting in `boss_orders_target`.** Prefer a damaged
   Rule-Box (ex) target over an equal-HP one-prizer when both are
   reachable.
6. **Stranded-energy penalty in `attach_energy`.** Penalize attaching to a
   Pokemon that's about to be Boss'd away or can't attack again this game.
7. **Backup-Dragapult energy investment.** When the active Dragapult ex is
   already fully fueled, prefer routing Fire/Psychic to a benched
   Dreepy/Drakloak building toward the *next* Dragapult ex over topping up
   redundant energy on the active one.

**Implemented as:** item 5 — `boss_orders_target`'s ex tiebreak now requires
`damaged_ex` (`0 < hp < maxHp`), so an untouched full-HP ex no longer
auto-beats a damaged one-prizer. Item 6 — `_stranded_energy_risk` (hp <= 30
proxy, since opponent hand/Boss-holding isn't observable) sorts ahead of the
attacker-line ordering in `attach_energy`. Item 7 — `_dragapult_fully_fueled`
replaces a buggy `energy_count(c) >= 2` readiness check (which falsely
treated 2 Fire-no-Psychic as ready) with a real `can_pay_cost` check against
Phantom Dive's actual cost; this is what makes the backup-routing fall
through correctly. 8 new tests.

**Validated:** n=60 run showed -7pp (within noise band for that N); n=120
run showed **+6pp (58%→64%), verdict KEEP**. Treat as directional, not
conclusive proof, given how much these numbers moved run-to-run earlier —
but no regression signal strong enough to walk anything back.

---

## Phase 3 — Feed from real losses — batch 1 ✅ DONE, batch 2 🔜 NEXT

`heuristic_loop/CHANGELOG.md` has no real findings yet beyond the `fa87ffe`
batch — these modules stay unwritten until a logged loss batch actually
shows the mistake. Building them earlier risks tuning against imagined
scenarios instead of real ones (same trap `docs/plans/008a_review_brief.md` itself warns against
in its "What To Ignore Or Avoid" section).

### Batch 1 (2026-07-10, `heuristic_loop/logs/20260710_122935`, 30 games / 13
losses) — ✅ DONE

Ran `run_batch.py` fresh (inbox/logs were empty), analyzed all 13 losses
against the raw replay JSON (`heuristic_loop/logs/20260710_122935/issues_log.md`
has full per-game detail), found four findings — three cross-game recurring:

- **(A) No heuristic ever played a legal Item/Supporter alongside a legal
  Attack** — `attack_choice` won the Main-phase menu by default whenever
  nothing else fired, forfeiting every other Play option for the turn
  (attacking ends the turn). Worst instance: Crispin/Crushing Hammer/Boss's
  Orders sat legal and unused for 5 consecutive turns in one game while the
  opponent had a benched 2-prize ex the whole time. This is what
  `docs/plans/008a_review_brief.md`'s Lethal/tactical-search modules were trying to route around —
  turns out the actual gap was upstream of targeting, at "should we even be
  attacking this decision."
- **(B) `attach_energy`'s active-priority short-circuit defeated its own
  documented attacker-line order** whenever a non-attacker-line Pokemon
  (Munkidori) was active, silently out-prioritizing a bench Dreepy/Drakloak
  building toward the next Dragapult ex.
- **(C) Crispin's own energy-shuffle sub-decisions (`ATTACH_TO`/`ATTACH_FROM`)
  had zero heuristic coverage** — fell entirely to random despite Crispin
  being one of the most frequently played cards in the deck.
- **(D) Crushing Hammer's discard-energy target selection had no
  heuristic** (also used for our own retreat-cost energy discard) — fell to
  random both ways.

**Implemented as:** `play_crushing_hammer` + `supporter_tiebreak`'s guard
loosened from requiring >=2 legal Supporters to >=1 (item A, split across an
Item rule and a Supporter fix since they're different `OptionType`s but the
same underlying gap); `attach_energy`'s active-priority short-circuit scoped
to only the attacker line itself (Dreepy/Drakloak/Dragapult ex) via a new
shared `_fuel_priority` helper (item B); `crispin_energy_routing`, a new
heuristic covering both Crispin sub-decisions, reusing `_fuel_priority` for
the destination step (item C); `discard_energy_target`, disambiguating
Crushing-Hammer-vs-retreat-cost via each option's `playerIndex`, reusing
`_discard_priority` for the retreat-cost branch (item D). 8 new tests (44
total).

**Validated:** n=120 win-rate harness run: OLD 42% (50/120) vs NEW 61%
(73/120), **delta +19pp, verdict KEEP** — well clear of the noise band
observed at this N in Phase 1/2 (which topped out around ±7pp). The clearest
signal so far in this loop, consistent with finding A being both the most
severe and the most mechanically simple to fix (a default-selection ordering
bug, not a targeting judgment call).

### Batch 2 — 🔜 NEXT (repeat the loop)

Re-run `run_batch.py` against the now-updated heuristics to see what
surfaces once findings A-D are fixed — some of Phase 3's original
placeholder items (Tempo Disruption Evaluator's EV-based Hammer targeting
beyond "opponent has any energy," Judge/Xerosic/Unfair Stamp timing,
Recovery Planner, Opponent Threat Abstraction) may or may not still be real
gaps once the bigger default-ordering bug (finding A) stops masking them.
Don't pre-build those — look at what the next batch's losses actually show.

---

## Out of scope for now (search infra) — see `docs/plans/009_native_search_plan.md`

Not being built until/unless a real forward model exists for this engine:

- Exact Lethal Line Finder (multi-branch Boss + Adrena-Brain + attack +
  allocation search).
- Boss + Munkidori + attack tactical search.
- General beam search over a turn.

**Update (2026-07-11):** the "no forward model exists" premise above turned
out to be wrong — `libcg.so` exports a native MCTS search API
(`AgentStart`/`SearchBegin`/`SearchStep`/`SearchEnd`/`SearchRelease`) that
was never previously investigated, and the exact serialized state it needs
is already delivered to every agent as `obs["search_begin_input"]` on every
decision (silently unused until now). See `docs/plans/009_native_search_plan.md`
for the evidence and a phased plan — the prerequisite is now a bounded RE
spike to pin down `SearchBegin`'s argument layout, not a rules-engine
rewrite. This section's heuristic-only fallback still stands if that spike
doesn't pan out.

---

## Already covered — no new work needed

- **Regression test discipline** — `tests/test_heuristics_dragapult.py`
  (36 tests as of Phase 1/2) + `heuristic_loop/eval_heuristic_change.py`'s before/after
  win-rate harness (PKM-020) already is the infrastructure `docs/plans/008a_review_brief.md` asks
  for under "Regression Tests." Just keep using it for every change above.
- **Phantom Dive Allocator base logic** — `bench_spread_target` already
  exists with matchup-priority + HP-threshold scoring; Phase 1 item 3 only
  adds a missing tier, not the whole module.
- **Boss target selection base logic** — `boss_orders_target` already does
  lethal-first, matchup-priority, ex-priority scoring; Phase 1/2 items
  tighten it, they don't replace it.

---

## Reference

Full module-by-module reasoning and the original decision table: see the
review conversation (2026-07-10) that produced this doc, and `docs/plans/008a_review_brief.md`
itself for the un-reconciled original brief.
