# heuristic_loop — log-driven heuristic improvement loop

Formalizes PKM-019 (read verbose playtest logs, find concrete recurring
mistakes with cited evidence, propose a specific heuristic change) and
PKM-020 (validate every change with a measured before/after win-rate,
instead of trusting a single trace's reasoning). Everything for this loop
lives in this directory, separate from `scripts/` (general-purpose replay
tooling) and `docs/` (design plans) so the iterate-and-measure workflow
doesn't get tangled up with either.

All scripts here need the real engine (`libcg.so`, Linux-only) and must be
run under **WSL**, same as the rest of the repo — see `AGENTS.md` setup.

## Quick path: drop files, run the skill

If you already have loss replay JSONs (from `run_batch.py`, a Kaggle
download, wherever) and just want the analysis, skip straight to this:

1. Drop the JSON files into `heuristic_loop/inbox/` (gitignored — drop
   anything there, filenames don't matter).
2. Run the `analyze-heuristic-losses` skill (`/analyze-heuristic-losses` or
   just ask to "analyze the losses in the inbox"). It bundles them
   (`prepare_analysis.py`) and reads the result for you — no manual script
   invocation needed.

This is steps 2-3 of the full loop below, automated into one ask. Steps
1 (generating losses in the first place) and 4-7 (implement, validate,
record) are still separate — the skill stops at reporting findings and
waits for you to say a finding's worth acting on.

## The loop

```
 1. run_batch.py          play N games, save every loss as a replay JSON
 2. prepare_analysis.py   bundle those losses into one readable file
 3. (agent step)          read the bundle + heuristics_dragapult.py + docs,
                           find recurring mistakes, propose a code change
 4. implement the change  edit src/pokemon/heuristics_dragapult.py (+ tests)
 5. eval_heuristic_change.py   measure old vs new win-rate over N games
 6. CHANGELOG.md          record trigger, finding, change, and the
                           validation result — kept or reverted
```

Steps 1-2 and 5 are scripts. Step 3 is deliberately **not** a script —
judging whether a specific decision was a mistake needs domain reasoning
(attack costs, board state, what the heuristic *should* have done) that
isn't worth encoding as rules; that's exactly the kind of judgment call an
agent should make by reading the bundle, not something to fake with
pattern-matching. Dispatch it as a fresh subagent (no prior framing bias)
with:

- `heuristic_loop/logs/<batch>/analysis_bundle.md` (from step 2)
- `src/pokemon/heuristics_dragapult.py` (current logic)
- `docs/plans/007_heuristics_logic_plan.md` (intended design)
- `reverse-engineering/data/all_cards.json` / `all_attacks.json` if the
  question is about a specific card's numbers

and ask it to report *recurring* patterns across games (not one-off
variance), each with the specific replay file, turn, and option cited —
same evidence bar as the original PKM-017 Seek Inspiration fix. Findings
that don't recur across multiple games are noise, not signal — say so
explicitly rather than acting on a single game's trace.

## Usage

```bash
# 1. Play a batch, keep only the losses (default: 20 games, dragapult, heuristic agent)
uv run python heuristic_loop/run_batch.py -g 20 --losses-only

# 2. Bundle the losses from that batch into one file
uv run python heuristic_loop/prepare_analysis.py heuristic_loop/logs/<timestamp>

# 3. Hand the bundle to an agent (see above) -> get findings + a proposed diff

# 4. Implement the change by hand, add/update tests in tests/test_heuristics_dragapult.py

# 5. Validate: does the working-tree change actually win more than the last commit?
uv run python heuristic_loop/eval_heuristic_change.py -g 20

# 6. Record the result in CHANGELOG.md (see its template) before moving on
```

`eval_heuristic_change.py --old-ref <ref>` compares against any commit, not
just the last one (e.g. `--old-ref main` to compare against a shared
baseline, or an older SHA to check whether a change from a few sessions ago
is still worth keeping).

## Files

| File | Purpose |
|---|---|
| `run_batch.py` | Play N games, save each as a Kaggle-format replay JSON (`env.toJSON()`), same shape `scripts/analyze_heuristic_logs.py` already reads. `--losses-only` skips saving wins/draws to keep batches small. |
| `prepare_analysis.py` | Run `scripts/analyze_heuristic_logs.py` over every loss in a batch dir, concatenate into one `analysis_bundle.md`. Does no judging — just assembly. |
| `eval_heuristic_change.py` | PKM-020's before/after harness. Materializes the "old" version via `git worktree` (not a file copy — a copy would break `catalog._DATA_DIR`'s path-relative-to-`__file__` lookup into `reverse-engineering/data/`, see AGENTS.md "Known issues"), runs both versions in isolated subprocesses (`_play_worker.py`) to avoid Python module-cache collisions, reports win-rate delta and a keep/revert verdict. Warns below `MIN_RECOMMENDED_GAMES` (20, per PKM-019's only real precedent so far — 0%→25% over 20 games). |
| `_play_worker.py` | Internal — not run directly. One version's game-playing logic, parameterized by which `src/` dir to import `pokemon` from. |
| `CHANGELOG.md` | The context page. One entry per heuristic change: trigger, cited finding, what changed, before/after win-rate, keep/revert verdict. Read this before proposing a new change so you don't re-introduce something already tried and reverted. |
| `logs/` | Batch output (gitignored — replay JSONs are large and regenerable). |
| `inbox/` | Drop zone for manually-collected loss replay JSONs (gitignored except `.gitkeep`) — the quick path above reads from here by default. |

## Open question carried over from PKM-020

How many games is actually enough to trust a win-rate delta over noise?
20 is the current working minimum (PKM-017's only real precedent), not a
statistically derived number — if a change's win-rate swings are close to
that variance, re-run rather than trusting one 20-game batch.
