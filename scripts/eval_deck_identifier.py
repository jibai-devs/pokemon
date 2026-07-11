"""PKM-023 offline eval harness: drive `pokemon.deck_id.DeckIdentifier` with
downloaded replays' reveal sequences (no engine/WSL needed) and report how
well it does *without* ever training on these games -- the library comes
from human tournament lists (PKM-022), not the replay pool.

For each replay and each of the two players' perspectives, replays every
decision-step observation through a fresh `DeckIdentifier`, tracking the
opponent, and records:

- the turn the belief first reaches level 2 (archetype-core match) and
  level 1 (exact list match), if ever
- the final level reached
- accuracy vs the opponent's actual submitted 60-card list: exact match at
  level 1, core-subset check at level 2

Per plan 010 Phase 2's note: the replay pool is today's low-elo bot meta,
which mostly *won't* exact-match tournament lists -- this measures level-2/3
fallback quality, not a level-1 hit rate.

Usage:
    uv run python scripts/eval_deck_identifier.py
    uv run python scripts/eval_deck_identifier.py --replays-dir data/replays/raw --limit 200
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pokemon.deck_id import DeckIdentifier, load_library

REPO_ROOT = Path(__file__).resolve().parents[1]


def _extract_ground_truth(data: dict) -> tuple[list[int], list[int]] | None:
    """Both players' submitted 60-card decks, per `analyze_meta.extract_decks`'s
    shape: `steps[0][0]["visualize"][0]["action"]` is `[deck_p0, deck_p1]`."""
    steps = data.get("steps") or []
    if not steps:
        return None
    vis = steps[0][0].get("visualize") or []
    if not vis:
        return None
    action = vis[0].get("action")
    if not action or len(action) != 2 or len(action[0]) != 60 or len(action[1]) != 60:
        return None
    return action[0], action[1]


def _run_perspective(steps: list, perspective: int, library: dict) -> dict | None:
    ident = DeckIdentifier(library=library)
    level1_turn = None
    level2_turn = None
    final_level = 3
    n_decisions = 0
    for step in steps:
        for frame in step:
            obs = frame.get("observation")
            if not obs:
                continue
            current = obs.get("current")
            if not current:
                continue
            my_idx = current.get("yourIndex")
            if my_idx != perspective:
                continue
            players = current.get("players") or []
            if len(players) != 2:
                continue
            opp = players[1 - my_idx]
            ident.update(opp)
            n_decisions += 1
            level = ident.level()
            final_level = level
            turn = current.get("turn")
            if level <= 2 and level2_turn is None:
                level2_turn = turn
            if level == 1 and level1_turn is None:
                level1_turn = turn
    if n_decisions == 0:
        return None
    return {
        "identifier": ident,
        "level1_turn": level1_turn,
        "level2_turn": level2_turn,
        "final_level": final_level,
    }


def _accuracy(result: dict, actual_deck: list[int]) -> str:
    ident: DeckIdentifier = result["identifier"]
    actual = Counter(actual_deck)
    level = result["final_level"]
    if level == 1:
        exact = ident.identified_list()
        return "exact_match" if exact == dict(actual) else "exact_miss"
    if level == 2:
        best = ident.best_archetype()
        if best is None:
            return "n/a"
        arch = ident.archetypes().get(best[0], {})
        core = arch.get("core", {})
        core_subset = all(actual.get(int(cid), 0) >= n for cid, n in core.items())
        return "core_subset" if core_subset else "core_miss"
    return "n/a"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--replays-dir", default="data/replays/raw")
    parser.add_argument("--library", default=None, help="path to library.json (default: data/meta_decks/library.json)")
    parser.add_argument("--limit", type=int, default=None, help="max replay files to process")
    parser.add_argument("--out", default="data/meta_decks/deck_id_eval_report.txt")
    args = parser.parse_args()

    library = load_library(args.library)
    replays_dir = REPO_ROOT / args.replays_dir
    files = sorted(replays_dir.glob("*.json"))
    if args.limit:
        files = files[: args.limit]

    final_level_counts: Counter[int] = Counter()
    accuracy_counts: Counter[str] = Counter()
    level1_turns: list[int] = []
    level2_turns: list[int] = []
    n_perspectives = 0
    n_skipped = 0

    for path in files:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            n_skipped += 1
            continue
        gt = _extract_ground_truth(data)
        if gt is None:
            n_skipped += 1
            continue
        deck_p0, deck_p1 = gt
        steps = data.get("steps") or []
        for perspective, actual_deck in ((0, deck_p1), (1, deck_p0)):
            result = _run_perspective(steps, perspective, library)
            if result is None:
                continue
            n_perspectives += 1
            final_level_counts[result["final_level"]] += 1
            if result["level1_turn"] is not None:
                level1_turns.append(result["level1_turn"])
            if result["level2_turn"] is not None:
                level2_turns.append(result["level2_turn"])
            accuracy_counts[_accuracy(result, actual_deck)] += 1

    lines: list[str] = []
    lines.append(f"=== Deck identifier offline eval: {len(files)} replays ({n_skipped} skipped/unparseable) ===")
    lines.append(f"Perspectives evaluated: {n_perspectives} (2 per parseable replay)")
    lines.append("")
    lines.append("Final level distribution:")
    for level in (1, 2, 3):
        n = final_level_counts.get(level, 0)
        pct = 100 * n / n_perspectives if n_perspectives else 0.0
        lines.append(f"  Level {level}: {n} ({pct:.0f}%)")
    lines.append("")
    if level2_turns:
        lines.append(f"Turn first reaching level 2: mean={sum(level2_turns) / len(level2_turns):.1f}, n={len(level2_turns)}")
    else:
        lines.append("Turn first reaching level 2: never (0 perspectives)")
    if level1_turns:
        lines.append(f"Turn first reaching level 1: mean={sum(level1_turns) / len(level1_turns):.1f}, n={len(level1_turns)}")
    else:
        lines.append("Turn first reaching level 1: never (0 perspectives)")
    lines.append("")
    lines.append("Accuracy vs actual submitted list (final level only):")
    for key, n in sorted(accuracy_counts.items()):
        pct = 100 * n / n_perspectives if n_perspectives else 0.0
        lines.append(f"  {key}: {n} ({pct:.0f}%)")

    report = "\n".join(lines)
    print(report)
    out_path = REPO_ROOT / args.out
    out_path.write_text(report + "\n", encoding="utf-8")
    print(f"\nWrote report to {out_path}")


if __name__ == "__main__":
    main()
