"""PKM-024 (plan 011 Phase 1): build the replay-extracted opponent deck
library and merge it into `data/meta_decks/library.json` alongside the
human-tournament (Limitless) archetypes.

Why: offline eval (`eval_deck_identifier.py`, 2026-07-11) showed the
human-tournament library identifies almost nothing in the current Kaggle
pool (89% level-3, and wrong whenever it commits) — our opponents are other
competitors' fixed bot submissions, not tournament players. But the pool is
a lookup table: every replay exposes both players' exact 60-card lists, and
only ~137 unique lists exist across 1,500 replays. This script extracts
them, clusters them into archetypes by unique-Pokemon-set fingerprint (same
scheme as `analyze_meta.py`), computes core/flex per archetype (same math as
`fetch_limitless_decks.py`), and merges them into the library under
`source: "replays"` tags so `pokemon.deck_id.DeckIdentifier` can match
against them.

Merge semantics (re-runnable / idempotent):
- Archetypes are tagged with a `source`; previously-merged `"replays"`
  archetypes are dropped and rebuilt from the current replay set each run.
- Non-replay archetypes are kept as-is (tagged `"limitless_550"` on first
  migration) with their within-source share preserved in `source_share`.
- `meta_share` (the identifier's prior) = `source_share` x the source's
  weight: `--replay-weight` (default 0.85) to replays — today's actual
  opponents — and the remainder to the human lists (relevant again if the
  meta netdecks toward the deadline; re-run with a lower weight then).
- Replay `source_share` is by *game-instance frequency* (a list seen in 400
  games gets a proportionally larger prior), not unique-list count.

NOTE: `fetch_limitless_decks.py` overwrites library.json with a
limitless-only library; re-run this script afterwards to re-merge.

Usage:
    python scripts/extract_replay_decks.py
    python scripts/extract_replay_decks.py --replays-dir data/replays/raw --replay-weight 0.85
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pokemon.catalog import card_name as _catalog_card_name

REPO_ROOT = Path(__file__).resolve().parents[1]
LIBRARY_PATH = REPO_ROOT / "data" / "meta_decks" / "library.json"

REPLAY_SOURCE = "replays"
LEGACY_SOURCE = "limitless_550"  # what untagged (pre-merge) archetypes are


def load_card_names(csv_path: Path) -> dict[int, str]:
    names: dict[int, str] = {}
    with csv_path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            names[int(row["Card ID"])] = row["Card Name"]
    return names


def load_pokemon_ids(csv_path: Path) -> set[int]:
    with csv_path.open(encoding="utf-8") as f:
        return {int(row["Card ID"]) for row in csv.DictReader(f)}


def extract_decks(data: dict) -> tuple[list[int], list[int]] | None:
    """Both players' submitted 60-card lists from a replay
    (`steps[0][0]["visualize"][0]["action"]`, per `analyze_meta.extract_decks`)."""
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


DeckKey = tuple[tuple[int, int], ...]  # sorted ((card_id, count), ...) — a 60-card multiset


def collect_unique_lists(replays_dir: Path) -> tuple[Counter[DeckKey], int, int]:
    """Every unique 60-card list in the replay pool, keyed by multiset, with
    game-instance frequency counts. Returns (unique, n_replays, n_skipped)."""
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


def _label(cards: dict[int, int], pokemon_ids: set[int], names: dict[int, str]) -> str:
    """Human-readable archetype label from the top-2 Pokemon (by copy count,
    name as tiebreak so labels are deterministic across runs)."""
    counts = [(cid, n) for cid, n in cards.items() if cid in pokemon_ids]
    ranked = sorted(counts, key=lambda kv: (-kv[1], names.get(kv[0]) or _catalog_card_name(kv[0])))
    top = [names.get(cid) or _catalog_card_name(cid) for cid, _ in ranked[:2]]
    return " / ".join(top) if top else "No Pokemon"


def build_replay_archetypes(
    unique: Counter[DeckKey], pokemon_ids: set[int], names: dict[int, str]
) -> dict[str, dict]:
    """Cluster unique lists by unique-Pokemon-set fingerprint and compute
    core/flex per cluster (same 90%-presence rule as `fetch_limitless_decks
    .build_library`, over the cluster's unique lists)."""
    total_instances = sum(unique.values())
    families: dict[tuple[int, ...], list[tuple[dict[int, int], int]]] = defaultdict(list)
    for key, freq in unique.items():
        cards = dict(key)
        fp = tuple(sorted(cid for cid in cards if cid in pokemon_ids))
        families[fp].append((cards, freq))

    archetypes: dict[str, dict] = {}
    # Most-played families first so label collisions number deterministically.
    ordered = sorted(families.items(), key=lambda kv: (-sum(f for _, f in kv[1]), kv[0]))
    for fp, lists in ordered:
        lists.sort(key=lambda cf: (-cf[1], sorted(cf[0].items())))
        family_freq = sum(f for _, f in lists)
        base_label = f"{_label(lists[0][0], pokemon_ids, names)} [bot]"
        label = base_label
        n_dup = 2
        while label in archetypes:
            label = f"{base_label} #{n_dup}"
            n_dup += 1

        n = len(lists)
        presence: Counter[int] = Counter()
        min_count: dict[int, int] = {}
        max_count: dict[int, int] = {}
        for cards, _ in lists:
            for cid, count in cards.items():
                presence[cid] += 1
                min_count[cid] = min(min_count.get(cid, count), count)
                max_count[cid] = max(max_count.get(cid, count), count)
        core: dict[str, int] = {}
        flex: dict[str, dict] = {}
        for cid, seen_in in presence.items():
            if seen_in / n >= 0.9:
                core[str(cid)] = min_count[cid]
            else:
                flex[str(cid)] = {
                    "lists_with": seen_in,
                    "count_range": [min_count[cid], max_count[cid]],
                }

        archetypes[label] = {
            "source": REPLAY_SOURCE,
            "source_share": family_freq / total_instances,
            "lists": [
                {
                    "player": f"replay pool ({freq} games)",
                    "title": label,
                    "frequency": freq,
                    "cards": {str(cid): count for cid, count in sorted(cards.items())},
                }
                for cards, freq in lists
            ],
            "core": core,
            "flex": flex,
        }
    return archetypes


def merge_into_library(
    base: dict | None, replay_archetypes: dict[str, dict], replay_weight: float, replays_meta: dict
) -> dict:
    """Drop any previously-merged replay archetypes from ``base``, migrate
    untagged (pre-merge limitless) archetypes, and recompute every
    ``meta_share`` from ``source_share`` x source weight."""
    kept: dict[str, dict] = {}
    kept_sources: dict[str, dict] = {}
    if base:
        base_sources = base.get("sources", {})
        base_total = base.get("total_lists", 0) or 1
        for name, arch in base.get("archetypes", {}).items():
            src = arch.get("source", LEGACY_SOURCE)
            if src == REPLAY_SOURCE:
                continue
            arch = dict(arch)
            arch["source"] = src
            # Migration: pre-merge libraries carry the within-source share as
            # meta_share itself (fetch_limitless: len(lists)/total_lists).
            arch.setdefault("source_share", len(arch.get("lists", [])) / base_total)
            kept[name] = arch
            kept_sources.setdefault(
                src,
                base_sources.get(src)
                or {"url": base.get("source_url"), "total_lists": base_total},
            )

    non_replay_weight = (1.0 - replay_weight) / (len(kept_sources) or 1)
    sources = {src: {**meta, "weight": non_replay_weight} for src, meta in kept_sources.items()}
    sources[REPLAY_SOURCE] = {**replays_meta, "weight": replay_weight}

    archetypes: dict[str, dict] = {}
    for name, arch in list(kept.items()) + list(replay_archetypes.items()):
        arch = dict(arch)
        arch["meta_share"] = arch["source_share"] * sources[arch["source"]]["weight"]
        archetypes[name] = arch

    merged = {
        "sources": sources,
        "total_lists": sum(len(a.get("lists", [])) for a in archetypes.values()),
        "archetypes": archetypes,
    }
    if base and base.get("source_url"):
        merged["source_url"] = base["source_url"]
    return merged


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--replays-dir", default="data/replays/raw")
    parser.add_argument("--cards-csv", default="data/cards_processed.csv")
    parser.add_argument("--pokemon-csv", default="data/cards_pokemon.csv")
    parser.add_argument("--library", type=Path, default=LIBRARY_PATH, help="base library to merge into")
    parser.add_argument("--out", type=Path, default=None, help="output path (default: overwrite --library)")
    parser.add_argument(
        "--replay-weight",
        type=float,
        default=0.85,
        help="share of the identifier's prior given to replay-source archetypes (rest to human lists)",
    )
    args = parser.parse_args()

    names = load_card_names(REPO_ROOT / args.cards_csv)
    pokemon_ids = load_pokemon_ids(REPO_ROOT / args.pokemon_csv)
    replays_dir = REPO_ROOT / args.replays_dir

    unique, n_replays, n_skipped = collect_unique_lists(replays_dir)
    if not unique:
        print(f"No decks extracted from {replays_dir}", file=sys.stderr)
        return 1
    total_instances = sum(unique.values())
    top20 = sum(f for _, f in unique.most_common(20))

    replay_archetypes = build_replay_archetypes(unique, pokemon_ids, names)

    base = json.loads(args.library.read_text(encoding="utf-8")) if args.library.exists() else None
    replays_meta = {
        "replays_dir": str(args.replays_dir),
        "n_replays": n_replays,
        "total_instances": total_instances,
        "total_lists": len(unique),
    }
    merged = merge_into_library(base, replay_archetypes, args.replay_weight, replays_meta)

    out_path = args.out or args.library
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(merged, indent=2, sort_keys=True), encoding="utf-8")

    print(f"=== Replay deck extraction: {n_replays} replays ({n_skipped} skipped), {total_instances} deck instances ===")
    print(f"Unique 60-card lists: {len(unique)}")
    print(f"Top-20 lists cover {100 * top20 / total_instances:.0f}% of instances")
    print(f"Replay archetypes (Pokemon-set clusters): {len(replay_archetypes)}")
    print(f"Merged library -> {out_path}: {len(merged['archetypes'])} archetypes, {merged['total_lists']} lists")
    print()
    ranked = sorted(merged["archetypes"].items(), key=lambda kv: -kv[1]["meta_share"])
    for name, arch in ranked[:15]:
        n_lists = len(arch["lists"])
        print(
            f"  {name:45s} source={arch['source']:<14s} meta_share={arch['meta_share']:.1%}"
            f"  lists={n_lists}  core={len(arch['core'])} cards"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
