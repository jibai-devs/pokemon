"""Post-hoc core-Pokemon classification of the replay pool against
docs/tournament_archetype_cores.md.

Unlike `eval_deck_identifier.py` (which replays turn-by-turn hidden-info
reveals through the live `DeckIdentifier` belief), this works from full
information: each replay already exposes both players' complete 60-card
submitted lists (`steps[0][0]["visualize"][0]["action"]`). For each deck we
just check, per archetype in tournament_archetype_cores.md, whether every
core Pokemon (matched by name, any printing) is present in the deck. No
partial-reveal/turn-order modeling involved.

Usage:
    uv run python scripts/classify_replay_decks.py
    uv run python scripts/classify_replay_decks.py --replays-dir data/replays/raw
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CORES_MD = REPO_ROOT / "docs" / "tournament_archetype_cores.md"
CARDS_CSV = REPO_ROOT / "data" / "cards_processed.csv"
POKEMON_CSV = REPO_ROOT / "data" / "cards_pokemon.csv"
REPLAYS_DIR = REPO_ROOT / "data" / "replays" / "raw"
OUT_PATH = REPO_ROOT / "data" / "meta_decks" / "archetype_core_match_report.txt"

DeckKey = tuple[tuple[int, int], ...]


def load_cores(path: Path) -> dict[str, list[str]]:
    """Parse the `| Archetype | Core Pokemon |` table into
    {archetype: [pokemon name, ...]}."""
    cores: dict[str, list[str]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line.startswith("|") or "Archetype" in line or set(line) <= set("|-"):
            continue
        parts = [p.strip() for p in line.strip("|").split("|")]
        if len(parts) != 2:
            continue
        archetype, pokemon_field = parts
        names = [n.strip() for n in pokemon_field.split(",") if n.strip()]
        cores[archetype] = names
    return cores


def _normalize_apostrophe(name: str) -> str:
    return name.replace("’", "'")


def load_name_to_ids(path: Path) -> dict[str, set[int]]:
    """Keyed by apostrophe-normalized name -- the catalog uses curly
    apostrophes (U+2019), hand-written docs like tournament_archetype_cores.md
    use straight ones."""
    name_to_ids: dict[str, set[int]] = defaultdict(set)
    with path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            name_to_ids[_normalize_apostrophe(row["Card Name"])].add(int(row["Card ID"]))
    return name_to_ids


def resolve_cores(
    cores: dict[str, list[str]], name_to_ids: dict[str, set[int]]
) -> tuple[dict[str, list[set[int]]], list[tuple[str, str]]]:
    """Resolve each archetype's core Pokemon names to id-sets (one id-set per
    named Pokemon, since a name may span multiple printings). Returns
    (resolved, unresolved) where unresolved is [(archetype, name), ...] for
    names with zero catalog matches."""
    resolved: dict[str, list[set[int]]] = {}
    unresolved: list[tuple[str, str]] = []
    for archetype, names in cores.items():
        id_sets = []
        for name in names:
            ids = name_to_ids.get(_normalize_apostrophe(name), set())
            if not ids:
                unresolved.append((archetype, name))
            else:
                id_sets.append(ids)
        resolved[archetype] = id_sets
    return resolved, unresolved


def extract_decks(data: dict) -> tuple[list[int], list[int]] | None:
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


def collect_unique_lists(replays_dir: Path) -> tuple[Counter[DeckKey], int, int]:
    unique: Counter[DeckKey] = Counter()
    n_replays = 0
    n_skipped = 0
    for path in sorted(replays_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            decks = extract_decks(data)
        except (json.JSONDecodeError, OSError, KeyError, IndexError, TypeError):
            decks = None
        if decks is None:
            n_skipped += 1
            continue
        n_replays += 1
        for deck in decks:
            unique[tuple(sorted(Counter(deck).items()))] += 1
    return unique, n_replays, n_skipped


def matching_archetypes(deck_ids: set[int], resolved: dict[str, list[set[int]]]) -> list[str]:
    matches = []
    for archetype, id_sets in resolved.items():
        if id_sets and all(deck_ids & core_ids for core_ids in id_sets):
            matches.append(archetype)
    return matches


def load_pokemon_ids(path: Path) -> set[int]:
    with path.open(encoding="utf-8") as f:
        return {int(row["Card ID"]) for row in csv.DictReader(f)}


def top_pokemon_label(
    deck: dict[int, int], name_by_id: dict[int, str], pokemon_ids: set[int], n: int = 3
) -> str:
    ranked = sorted(
        ((cid, c) for cid, c in deck.items() if cid in pokemon_ids),
        key=lambda kv: (-kv[1], name_by_id.get(kv[0], str(kv[0]))),
    )
    return " / ".join(f"{name_by_id.get(cid, cid)}x{c}" for cid, c in ranked[:n])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--replays-dir", type=Path, default=REPLAYS_DIR)
    parser.add_argument("--cores", type=Path, default=CORES_MD)
    parser.add_argument("--cards-csv", type=Path, default=CARDS_CSV)
    parser.add_argument("--pokemon-csv", type=Path, default=POKEMON_CSV)
    parser.add_argument("--out", type=Path, default=OUT_PATH)
    args = parser.parse_args()

    cores = load_cores(args.cores)
    name_to_ids = load_name_to_ids(args.cards_csv)
    id_to_name = {cid: name for name, ids in name_to_ids.items() for cid in ids}
    pokemon_ids = load_pokemon_ids(args.pokemon_csv)
    resolved, unresolved = resolve_cores(cores, name_to_ids)

    if unresolved:
        print("WARNING: unresolved core Pokemon names (0 catalog matches):", file=sys.stderr)
        for archetype, name in unresolved:
            print(f"  {archetype}: {name!r}", file=sys.stderr)

    unique, n_replays, n_skipped = collect_unique_lists(args.replays_dir)
    total_instances = sum(unique.values())

    # Per-unique-list and per-game-instance (frequency-weighted) tallies.
    match_counts_lists: Counter[str] = Counter()  # "unmatched" or archetype name or "ambiguous(N)"
    match_counts_instances: Counter[str] = Counter()
    unmatched_examples: list[tuple[int, dict[int, int]]] = []  # (freq, deck)
    ambiguous_examples: list[tuple[int, dict[int, int], list[str]]] = []

    for key, freq in unique.items():
        deck = dict(key)
        deck_ids = set(deck.keys())
        matches = matching_archetypes(deck_ids, resolved)
        if not matches:
            label = "unmatched"
            unmatched_examples.append((freq, deck))
        elif len(matches) == 1:
            label = matches[0]
        else:
            label = f"ambiguous({'/'.join(sorted(matches))})"
            ambiguous_examples.append((freq, deck, matches))
        match_counts_lists[label] += 1
        match_counts_instances[label] += freq

    unmatched_examples.sort(key=lambda t: -t[0])
    ambiguous_examples.sort(key=lambda t: -t[0])

    lines: list[str] = []
    lines.append(
        f"=== Core-Pokemon archetype classification (full-info, post-hoc): "
        f"{n_replays} replays ({n_skipped} skipped), {len(unique)} unique lists, "
        f"{total_instances} deck instances ==="
    )
    lines.append(f"Archetypes in {args.cores.name}: {len(cores)}")
    if unresolved:
        lines.append(f"WARNING: {len(unresolved)} core Pokemon name(s) had zero catalog matches (see stderr)")
    lines.append("")

    n_matched_lists = sum(v for k, v in match_counts_lists.items() if k not in ("unmatched",) and not k.startswith("ambiguous"))
    n_unmatched_lists = match_counts_lists.get("unmatched", 0)
    n_ambiguous_lists = sum(v for k, v in match_counts_lists.items() if k.startswith("ambiguous"))
    n_matched_inst = sum(v for k, v in match_counts_instances.items() if k not in ("unmatched",) and not k.startswith("ambiguous"))
    n_unmatched_inst = match_counts_instances.get("unmatched", 0)
    n_ambiguous_inst = sum(v for k, v in match_counts_instances.items() if k.startswith("ambiguous"))

    lines.append("By unique 60-card list:")
    lines.append(f"  matched (exactly one archetype): {n_matched_lists} ({100*n_matched_lists/len(unique):.0f}%)")
    lines.append(f"  ambiguous (multiple archetype cores present): {n_ambiguous_lists} ({100*n_ambiguous_lists/len(unique):.0f}%)")
    lines.append(f"  unmatched (no archetype core present): {n_unmatched_lists} ({100*n_unmatched_lists/len(unique):.0f}%)")
    lines.append("")
    lines.append("By game-instance (frequency-weighted, i.e. how much of the ladder this covers):")
    lines.append(f"  matched: {n_matched_inst} ({100*n_matched_inst/total_instances:.0f}%)")
    lines.append(f"  ambiguous: {n_ambiguous_inst} ({100*n_ambiguous_inst/total_instances:.0f}%)")
    lines.append(f"  unmatched: {n_unmatched_inst} ({100*n_unmatched_inst/total_instances:.0f}%)")
    lines.append("")

    lines.append("Per-archetype hit counts (unique lists / game instances):")
    per_arch = sorted(
        ((k, v, match_counts_instances[k]) for k, v in match_counts_lists.items() if k not in ("unmatched",) and not k.startswith("ambiguous")),
        key=lambda t: -t[2],
    )
    for name, n_lists, n_inst in per_arch:
        lines.append(f"  {name:30s} lists={n_lists:4d}  instances={n_inst:5d} ({100*n_inst/total_instances:.1f}%)")
    if not per_arch:
        lines.append("  (none)")
    lines.append("")

    if ambiguous_examples:
        lines.append(f"Ambiguous examples (top {min(10, len(ambiguous_examples))} by frequency):")
        for freq, deck, matches in ambiguous_examples[:10]:
            lines.append(f"  x{freq:4d}  matches={matches}  top_pokemon={top_pokemon_label(deck, id_to_name, pokemon_ids)}")
        lines.append("")

    lines.append(f"Unmatched examples (top {min(20, len(unmatched_examples))} by frequency):")
    for freq, deck in unmatched_examples[:20]:
        lines.append(f"  x{freq:4d}  top_pokemon={top_pokemon_label(deck, id_to_name, pokemon_ids)}")

    report = "\n".join(lines)
    print(report)
    args.out.write_text(report + "\n", encoding="utf-8")
    print(f"\nWrote report to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
