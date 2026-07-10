"""Before/after win-rate validation for a heuristics change (PKM-020).

Runs N games of an "old" version of the heuristics code against the same
baseline opponent as an "new" version, and reports the win-rate delta — so
"this heuristic change helped" is a measured result, not an assumption,
before the change gets kept. This is the harness PKM-019's process calls for
("re-run a batch and compare win-rate before/after... before keeping it")
but that had, until now, been done manually and inconsistently.

The "old" version is materialized with `git worktree` (not a plain file
copy) specifically so `catalog._DATA_DIR`'s path-relative-to-`__file__`
lookup still resolves `reverse-engineering/data/*.json` correctly — a copy
of just `src/pokemon` elsewhere silently breaks every catalog-backed
heuristic (see AGENTS.md "Known issues", the same class of bug that once
shipped a submission.tar.gz missing that data).

Each version's games run in its own subprocess (`_play_worker.py`) to avoid
Python module-cache collisions between two different `pokemon.heuristics`
modules.

Usage (run under WSL — the engine, `libcg.so`, is Linux-only):
    uv run python heuristic_loop/eval_heuristic_change.py -g 20
    uv run python heuristic_loop/eval_heuristic_change.py -g 20 --old-ref HEAD~1
    uv run python heuristic_loop/eval_heuristic_change.py -g 20 --old-ref main
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKER = Path(__file__).resolve().parent / "_play_worker.py"

MIN_RECOMMENDED_GAMES = 20


def _git(args: list[str]) -> str:
    result = subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed:\n{result.stderr}")
    return result.stdout.strip()


def _play(src_dir: Path, games: int, deck: str, agent: str, opponent: str) -> dict:
    result = subprocess.run(
        [
            "uv",
            "run",
            "python",
            str(WORKER),
            "--src-dir",
            str(src_dir),
            "--games",
            str(games),
            "--deck",
            deck,
            "--agent",
            agent,
            "--opponent",
            opponent,
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"worker failed (src_dir={src_dir}):\n{result.stderr}")
    # last line of stdout is the JSON summary; earlier lines may be engine noise
    return json.loads(result.stdout.strip().splitlines()[-1])


def _summarize(label: str, raw: dict) -> dict:
    games = raw["games"]
    wins = raw["wins"]
    return {
        "label": label,
        "games": games,
        "wins": wins,
        "losses": raw["losses"],
        "draws": raw["draws"],
        "win_rate": wins / games if games else 0.0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--games", "-g", type=int, default=MIN_RECOMMENDED_GAMES)
    parser.add_argument(
        "--old-ref",
        default="HEAD",
        help="git ref for the 'old' version (default: HEAD, i.e. last commit)",
    )
    parser.add_argument("--deck", "-d", default="dragapult")
    parser.add_argument("--agent", "-a", default="heuristic", choices=["random", "heuristic"])
    parser.add_argument("--opponent", default="random", choices=["random"])
    args = parser.parse_args()

    if args.games < MIN_RECOMMENDED_GAMES:
        print(
            f"WARNING: {args.games} games is below the {MIN_RECOMMENDED_GAMES}-game minimum PKM-019/020 "
            "treat as a believable signal (see PKM-020 'open questions') — treat any delta here as noisy.",
            file=sys.stderr,
        )

    with tempfile.TemporaryDirectory(prefix="heuristic_loop_eval_") as tmp:
        worktree_path = Path(tmp) / "old_worktree"
        print(f"Materializing OLD version ({args.old_ref}) via git worktree at {worktree_path}...")
        _git(["worktree", "add", "--detach", str(worktree_path), args.old_ref])
        try:
            print(f"Playing {args.games} games with OLD version ({args.old_ref})...")
            old_raw = _play(worktree_path / "src", args.games, args.deck, args.agent, args.opponent)
        finally:
            _git(["worktree", "remove", "--force", str(worktree_path)])

        print(f"Playing {args.games} games with NEW version (working tree)...")
        new_raw = _play(REPO_ROOT / "src", args.games, args.deck, args.agent, args.opponent)

    old = _summarize(f"OLD ({args.old_ref})", old_raw)
    new = _summarize("NEW (working tree)", new_raw)
    delta = new["win_rate"] - old["win_rate"]

    print(f"\n{'=' * 60}")
    print(
        f"OLD ({args.old_ref}): {old['wins']}/{old['games']} ({old['win_rate'] * 100:.0f}%) "
        f"[L={old['losses']} D={old['draws']}]"
    )
    print(
        f"NEW (working tree): {new['wins']}/{new['games']} ({new['win_rate'] * 100:.0f}%) "
        f"[L={new['losses']} D={new['draws']}]"
    )
    print(f"Delta: {delta * 100:+.0f} percentage points")

    if new["games"] < MIN_RECOMMENDED_GAMES:
        verdict = "INCONCLUSIVE (n too small — re-run with -g 20 or more before deciding)"
    elif delta > 0:
        verdict = "KEEP — new version won more"
    elif delta < 0:
        verdict = "REVERT — new version won less"
    else:
        verdict = "NO SIGNAL — identical win rate, re-run with more games or treat as a wash"
    print(f"Verdict: {verdict}")
    print(f"{'=' * 60}")

    print(json.dumps({"old": old, "new": new, "delta": delta, "verdict": verdict}))


if __name__ == "__main__":
    main()
