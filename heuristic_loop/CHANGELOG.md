# Heuristic change log

Context page for `src/pokemon/heuristics.py` and `src/pokemon/heuristics_dragapult.py`.
Every change to those files that came out of the log-driven loop (PKM-019/PKM-020)
gets an entry here **before or at the same time** the code change lands — the point
is to have a record of *why* a heuristic looks the way it does, so we don't flip-flop
(revert a fix, forget why it was added, re-add the bug it fixed) as more changes
stack up over time.

Newest entries first. Don't edit past entries except to fix typos — if a kept
change later turns out to be wrong, add a new entry that supersedes it and link
back, rather than rewriting history.

## Entry template

```
## YYYY-MM-DD — <short title>

**Trigger:** <what log/batch prompted this — link the log dir under heuristic_loop/logs/
or the finding from the analyze-losses workflow>

**Finding:** <the concrete, cited mistake — decision/turn/option ids, not "seemed
suboptimal">

**Change:** <function(s) touched, what changed, one paragraph>

**Validation:** OLD <w/l/d, win-rate> vs NEW <w/l/d, win-rate> over N games
(`heuristic_loop/eval_heuristic_change.py`), or "not yet validated" if landed
without running the harness (should be rare — flag why).

**Verdict:** KEPT | REVERTED | SUPERSEDED BY <link>
```

---

## 2026-07-10 — Phase 3 batch 1: default Play-vs-Attack ordering, attach_energy active-priority scope, Crispin routing, Crushing Hammer targeting

**Trigger:** `heuristic_loop/logs/20260710_122935` (fresh 30-game batch, 13
losses; inbox/logs were empty going into this, so `run_batch.py` was run to
seed evidence for `docs/008_review_implementation_plan.md` Phase 3). Full
per-game findings in `heuristic_loop/logs/20260710_122935/issues_log.md`.

**Finding:** Four findings, three cross-game recurring. (A) No heuristic
ever played a legal Item/Supporter alongside a legal Attack —
`attack_choice` won the Main-phase menu by default, forfeiting the rest of
the turn's Plays (games 017/020/021; worst case a 5-consecutive-turn stretch
in game_021 with Crispin/Crushing Hammer/Boss's Orders all sitting unused).
(B) `attach_energy`'s unconditional "prefer active" short-circuit defeated
its own documented attacker-line priority whenever a non-attacker-line
Pokemon (Munkidori) was active (games 010/014/026). (C) Crispin's own
`ATTACH_TO`/`ATTACH_FROM` energy-shuffle sub-decisions had zero heuristic
coverage, falling to random (games 010/014/015). (D) Crushing Hammer's
discard-energy target selection (also used for our own retreat-cost
discard) had no heuristic either way (games 008/009).

**Change:** `heuristics_dragapult.py` — `play_crushing_hammer` (new) plays
Crushing Hammer whenever the opponent has any attached energy, regardless of
what else is legal that decision. `supporter_tiebreak`'s gate loosened from
requiring >=2 legal Supporters to >=1 (each branch already has its own
payoff/chain gating, so a single candidate is exactly as safe as a tied
pair). `attach_energy`'s active-priority short-circuit rescoped to only the
attacker line itself (Dreepy/Drakloak/Dragapult ex) via a new shared
`_fuel_priority` helper — completing the current active Dragapult ex's own
cost still jumps the line, but Munkidori/Budew as active no longer
auto-beats a higher-priority bench target. `crispin_energy_routing` (new)
covers both Crispin sub-decisions: `ATTACH_TO` picks the scarcer energy type
across our board, `ATTACH_FROM` reuses `_fuel_priority`. `discard_energy_target`
(new) disambiguates Crushing-Hammer-vs-retreat-cost via each option's
`playerIndex`: targeting the opponent, prefers fully stripping a low-energy
target over a partial hit; discarding our own energy, reuses
`_discard_priority`'s "least costly to lose" ordering. 8 new tests (44
total, `PYTHONPATH=src python -m pytest tests/ -q`).

**Validation:** OLD (HEAD) 50/120 (42%) vs NEW (working tree) 73/120 (61%)
over 120 games (`heuristic_loop/eval_heuristic_change.py -g 120`). **Delta
+19pp, verdict KEEP** — well clear of the ±7pp noise band seen at this N in
the Phase 1/2 batches.

**Verdict:** KEPT

---

## 2026-07-09 — heuristic_loop tooling created (no heuristic change yet)

**Trigger:** none — this is the tooling itself (PKM-019/PKM-020 formalized into
scripts), not a heuristic change. First real log-driven finding will be the
first dated entry below it.

**Change:** N/A.

**Validation:** N/A.

**Verdict:** N/A — placeholder entry so the file has a working example of the
format before the first real one.
