---
name: analyze-heuristic-losses
description: Read a directory of Dragapult heuristic-agent loss replay JSONs and log every questionable decision in every game — not just cross-game recurring patterns — for the user to review themselves. Use when the user has dropped loss replay JSON files into heuristic_loop/inbox/ (or points at another directory / a heuristic_loop/logs/<batch> dir) and asks to analyze losses, find what the bot is doing wrong, or run the heuristic loop analysis step.
---

# Analyze heuristic losses

Turns a folder of loss replay JSONs into a logged, per-game inventory of
every questionable decision `src/pokemon/heuristics_dragapult.py` made —
the analysis step (step 3) of `heuristic_loop/README.md`'s loop. The user
reviews the log and decides on heuristic changes themselves; this skill's
job ends at producing a trustworthy, exhaustive log, not at proposing or
implementing fixes.

## Steps

1. **Resolve the target directory.** If the user named one, use it.
   Otherwise default to `heuristic_loop/inbox/`. If that's empty, say so and
   stop — don't fabricate an analysis. If pointed at a mixed win/loss
   `heuristic_loop/logs/<batch>/` dir instead, use
   `--pattern "game_*_loss.json"` so only losses get bundled.

2. **Bundle the losses.** Run (needs WSL — the analyzer imports
   `pokemon.catalog`, pure Python, but keep it consistent with the rest of
   the repo's WSL convention):
   ```bash
   wsl -e bash -lc "cd /mnt/c/Users/Luqman/Desktop/projects/pokemon && uv run python heuristic_loop/prepare_analysis.py <target_dir>"
   ```
   This writes `<target_dir>/analysis_bundle.md` — a condensed, per-game
   decision trace for every loss (off-by-one `selected` bug and area-blind
   option labels already fixed, per PKM-019). If it errors because there
   are zero matching files, report that to the user instead of guessing.
   The bundle is the index into each game, not the evidence itself — every
   finding still has to be checked against the raw replay JSON (step 4).

3. **Read for real understanding, not the bundle alone.** Read
   `<target_dir>/analysis_bundle.md`, then also read
   `src/pokemon/heuristics_dragapult.py` (what each heuristic is supposed to
   do) and `docs/plans/007_heuristics_logic_plan.md` (intended design/tiers). A
   mistake is only real if you can point at *what should have happened
   instead* given the actual heuristic logic — not just "that decision
   looks bad."

4. **Sweep every decision in every game — not just what recurs.** Go
   turn-by-turn through each replay and scrutinize every decision where the
   agent had a real choice (more than one legal, meaningfully different
   option). Be critical: default to suspicious of a pick, not charitable.
   A single-game finding is not noise here — log it — but it must clear one
   bar before logging: **verify it wasn't a forced move.** Load the raw
   replay JSON (`steps[0][0]["visualize"][i]`, per
   `scripts/analyze_heuristic_logs.py`'s frame shape) for that decision's
   frame and confirm more than one meaningfully different option actually
   existed — e.g. checking the hand/bench contents behind the option list,
   the way a Discard's `option` array only lists what's actually in hand.
   If only one real option existed, or all options were equivalent, don't
   log it as a finding — note the pattern was considered and ruled out only
   if it seemed like an obvious candidate at bundle-read time.

   Use a fork (or forks per game, run in parallel) to do this raw-JSON
   verification work — it's mechanical and produces a lot of intermediate
   tool output you don't need to keep in context. Each fork should report
   back a list of candidate findings with file/turn/step/option ids and its
   forced-move check result; you assemble those into the log.

5. **Log every surviving finding**, grouped by game file, to
   `<target_dir>/issues_log.md`. For each: the file, turn, and step/option
   id(s) (cite the actual raw-JSON values, e.g. hand contents, not just the
   bundle's rendered label), which heuristic function is responsible (or
   the absence of one — a gap where the random fallback fired on something
   important), what should have happened instead given the heuristic's own
   intended logic, and a confidence note — whether it also showed up in
   other games in this batch (signal) or only this one (still logged, but
   flagged as single-instance so the user can weigh it accordingly).

6. **Report a short summary to the user** (counts per game, most notable
   findings) and point them at `issues_log.md` for the full list. Do not
   propose code changes, implement fixes, run
   `heuristic_loop/eval_heuristic_change.py`, or write to
   `heuristic_loop/CHANGELOG.md` — the user reviews the log and prompts for
   any heuristic changes themselves.

## What this skill does not do

Doesn't filter findings down to only cross-game recurring patterns — every
game gets its own full sweep, logged in full, including single-instance
findings (clearly marked as such). Doesn't skip the raw-JSON forced-move
check — an unverified "this looks bad" is not a finding, it's a guess.
Doesn't propose fixes, implement changes, validate win-rate deltas, or
touch `heuristic_loop/CHANGELOG.md` — that's the user's call, made after
reading the log.
