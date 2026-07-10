"""Bundle a batch of loss replays into one file for an agent to read (PKM-019).

`scripts/analyze_heuristic_logs.py` already turns one raw Kaggle-format replay
into a condensed, correctly-labeled decision trace — this script doesn't
duplicate that. It just runs it over every loss in a `run_batch.py` output
directory and concatenates the results into a single markdown bundle, small
enough for an agent to read in one shot and look for *recurring* mistakes
across games rather than one-off variance (the distinction PKM-019's process
calls for).

This script does not judge anything — no "was this a mistake" logic lives
here. That judgment is the agent step: hand the bundle this produces, plus
`src/pokemon/heuristics_dragapult.py` and `docs/007_heuristics_logic_plan.md`,
to an agent (see heuristic_loop/README.md) and ask it to find recurring
patterns with cited evidence, same evidence bar as PKM-017/PKM-019.

Works on any directory of replay JSON files, not just `run_batch.py`
output — e.g. `heuristic_loop/inbox/`, a plain folder you drop downloaded
Kaggle loss replays into by hand. `--pattern` defaults to `*.json` (minus
`summary.json`, which isn't a replay) so that works out of the box; narrow
it with `--pattern "game_*_loss.json"` if pointed at a mixed win/loss
`run_batch.py` directory and you only want the losses.

Usage:
    uv run python heuristic_loop/prepare_analysis.py heuristic_loop/inbox
    uv run python heuristic_loop/prepare_analysis.py heuristic_loop/logs/20260709_120000 --pattern "game_*_loss.json"
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ANALYZER = REPO_ROOT / "scripts" / "analyze_heuristic_logs.py"
OUR_AGENT_NAME = "NaqibL"


def find_our_player_index(replay_path: Path, agent_name: str) -> int | None:
    """Match `agent_name` against `info.Agents` to find our seat in this replay.

    Kaggle replay downloads don't guarantee our agent is always player 0 — a
    batch can include games we're not even in, or games where we're seated
    at index 1. Returns None if `agent_name` isn't one of the two agents.
    """
    data = json.loads(replay_path.read_text(encoding="utf-8"))
    agents = data.get("info", {}).get("Agents", [])
    for i, agent in enumerate(agents):
        if agent.get("Name") == agent_name:
            return i
    return None


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "batch_dir",
        help="Directory of replay JSON files (e.g. heuristic_loop/inbox, or a run_batch.py output dir)",
    )
    parser.add_argument(
        "--player",
        type=int,
        default=None,
        help="Force a player index for every replay, instead of auto-detecting "
        f"'{OUR_AGENT_NAME}' from info.Agents in each file",
    )
    parser.add_argument(
        "--agent-name",
        default=OUR_AGENT_NAME,
        help=f"Agent name to look for when auto-detecting our seat (default: {OUR_AGENT_NAME})",
    )
    parser.add_argument(
        "--pattern",
        default="*.json",
        help="Glob for which files count as replays (default: *.json, excluding summary.json)",
    )
    parser.add_argument(
        "--out", default=None, help="Output bundle path (default: <batch_dir>/analysis_bundle.md)"
    )
    args = parser.parse_args()

    batch_dir = Path(args.batch_dir)
    loss_files = sorted(p for p in batch_dir.glob(args.pattern) if p.name != "summary.json")
    if not loss_files:
        print(
            f"No replay JSON files found in {batch_dir} matching '{args.pattern}' "
            f"(excluding summary.json). Drop loss replay JSONs in there, or point "
            f"--pattern at the right files.",
            file=sys.stderr,
        )
        sys.exit(1)

    out_path = Path(args.out) if args.out else batch_dir / "analysis_bundle.md"
    sections = [
        f"# Loss analysis bundle — {batch_dir.name}\n",
        f"{len(loss_files)} losses out of the batch. Each section below is one game's "
        "condensed decision trace (our player's decisions only), produced by "
        "`scripts/analyze_heuristic_logs.py` (off-by-one `selected` bug and area-blind "
        "option labeling already fixed — see PKM-019).\n",
        "Read for *recurring* patterns across games, not single-game variance. For each "
        "recurring mistake found: cite the specific game file, turn, and option id(s) — "
        "same evidence bar as the PKM-017 Seek Inspiration fix.\n",
    ]

    skipped = []
    for loss_file in loss_files:
        if args.player is not None:
            player_idx = args.player
        else:
            player_idx = find_our_player_index(loss_file, args.agent_name)
            if player_idx is None:
                skipped.append(loss_file.name)
                sections.append(
                    f"\n---\n\n## {loss_file.name}\n\n"
                    f"SKIPPED: '{args.agent_name}' not found in this replay's "
                    "info.Agents — not one of our games, or the agent name has "
                    "changed. Pass --agent-name or --player to override.\n"
                )
                continue

        result = subprocess.run(
            [sys.executable, str(ANALYZER), str(loss_file), "--player", str(player_idx)],
            capture_output=True,
            text=True,
        )
        sections.append(f"\n---\n\n## {loss_file.name}\n\n```\n{result.stdout.strip()}\n```\n")
        if result.returncode != 0:
            sections.append(f"\n(analyzer stderr: {result.stderr.strip()})\n")

    out_path.write_text("\n".join(sections), encoding="utf-8")
    print(f"Wrote {len(loss_files)}-game analysis bundle to {out_path}")
    if skipped:
        print(
            f"Skipped {len(skipped)} file(s) where '{args.agent_name}' wasn't found: "
            f"{', '.join(skipped)}",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
