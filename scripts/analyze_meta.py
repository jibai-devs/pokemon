"""Extract deck archetypes from downloaded replays and report meta win-rates.

Reads every replay in data/replays/raw/, pulls the 60-card deck each player
submitted (frame 0's action field), fingerprints it by its unique Pokemon IDs,
and clusters replays into archetypes by that fingerprint. Reports count,
win-rate, and key Pokemon per archetype, plus a switch/stay recommendation
for our own fire deck.

Usage:
    uv run python scripts/analyze_meta.py
    uv run python scripts/analyze_meta.py --replays-dir data/replays/raw --top 15
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
FIRE_DECK_CORE = frozenset({46, 76, 30})  # Gouging Fire ex, Slugma, Magcargo ex

TRAINER_STAGES = {"Item", "Supporter", "Pokemon Tool", "Stadium"}


def load_card_names(csv_path: Path) -> dict[int, str]:
    names: dict[int, str] = {}
    with csv_path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            names[int(row["Card ID"])] = row["Card Name"]
    return names


def load_pokemon_ids(csv_path: Path) -> set[int]:
    with csv_path.open(encoding="utf-8") as f:
        return {int(row["Card ID"]) for row in csv.DictReader(f)}


def load_trainer_ids(csv_path: Path) -> set[int]:
    with csv_path.open(encoding="utf-8") as f:
        return {int(row["Card ID"]) for row in csv.DictReader(f)}


def card_display_name(card_id: int, names: dict[int, str]) -> str:
    return names.get(card_id) or _catalog_card_name(card_id)


def extract_decks(replay_path: Path) -> tuple[list[int], list[int], list[int]] | None:
    """Return (deck_p0, deck_p1, rewards) for a replay, or None if unparseable."""
    data = json.loads(replay_path.read_text(encoding="utf-8"))
    steps = data.get("steps") or []
    rewards = data.get("rewards") or []
    if not steps or len(rewards) != 2:
        return None
    frame0 = steps[0][0]
    vis = frame0.get("visualize") or []
    if not vis:
        return None
    action = vis[0].get("action")
    if not action or len(action) != 2:
        return None
    deck_p0, deck_p1 = action
    if len(deck_p0) != 60 or len(deck_p1) != 60:
        return None
    return deck_p0, deck_p1, rewards


def fingerprint(deck: list[int], pokemon_ids: set[int]) -> tuple[int, ...]:
    return tuple(sorted({c for c in deck if c in pokemon_ids}))


def key_pokemon_names(deck: list[int], pokemon_ids: set[int], names: dict[int, str], limit: int = 5) -> list[str]:
    counts = Counter(c for c in deck if c in pokemon_ids)
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], card_display_name(kv[0], names)))
    return [card_display_name(cid, names) for cid, _ in ranked[:limit]]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--replays-dir", default="data/replays/raw")
    parser.add_argument("--cards-csv", default="data/cards_processed.csv")
    parser.add_argument("--pokemon-csv", default="data/cards_pokemon.csv")
    parser.add_argument("--trainer-csv", default="data/cards_trainer.csv")
    parser.add_argument("--top", type=int, default=10, help="Number of archetypes to show")
    parser.add_argument("--out", default="data/meta_report.txt")
    args = parser.parse_args()

    replays_dir = REPO_ROOT / args.replays_dir
    names = load_card_names(REPO_ROOT / args.cards_csv)
    pokemon_ids = load_pokemon_ids(REPO_ROOT / args.pokemon_csv)
    trainer_ids = load_trainer_ids(REPO_ROOT / args.trainer_csv)

    files = sorted(replays_dir.glob("*.json"))

    archetype_wins: Counter[tuple[int, ...]] = Counter()
    archetype_games: Counter[tuple[int, ...]] = Counter()
    archetype_deck_sample: dict[tuple[int, ...], list[int]] = {}
    archetype_trainers: dict[tuple[int, ...], Counter[int]] = defaultdict(Counter)

    n_replays = 0
    n_skipped = 0
    for path in files:
        try:
            result = extract_decks(path)
        except (json.JSONDecodeError, KeyError, IndexError, TypeError):
            result = None
        if result is None:
            n_skipped += 1
            continue
        n_replays += 1
        deck_p0, deck_p1, rewards = result
        for deck, reward in ((deck_p0, rewards[0]), (deck_p1, rewards[1])):
            fp = fingerprint(deck, pokemon_ids)
            archetype_games[fp] += 1
            if reward == 1:
                archetype_wins[fp] += 1
            archetype_deck_sample.setdefault(fp, deck)
            archetype_trainers[fp].update(c for c in deck if c in trainer_ids)

    total_games = sum(archetype_games.values())
    lines: list[str] = []
    lines.append(f"=== Meta report: {n_replays} replays ({n_skipped} skipped/unparseable), {total_games} deck instances ===")
    lines.append("")
    header = f"{'Archetype':<25} | {'Count':>5} | {'Win%':>5} | Key Pokemon"
    lines.append(header)
    lines.append("-" * len(header))

    ranked = sorted(archetype_games.items(), key=lambda kv: -kv[1])
    for fp, count in ranked[: args.top]:
        wins = archetype_wins[fp]
        win_pct = 100 * wins / count if count else 0.0
        deck = archetype_deck_sample[fp]
        key_names = key_pokemon_names(deck, pokemon_ids, names)
        label = key_names[0] if key_names else "Unknown"
        lines.append(f"{label:<25} | {count:>5} | {win_pct:>4.0f}% | {', '.join(key_names)}")

    lines.append("")

    # Our fire deck
    fire_fp = next((fp for fp in archetype_games if set(fp) >= FIRE_DECK_CORE), None)
    if fire_fp is not None:
        fire_count = archetype_games[fire_fp]
        fire_wins = archetype_wins[fire_fp]
        fire_pct = 100 * fire_wins / fire_count if fire_count else 0.0
        fire_share = 100 * fire_count / total_games if total_games else 0.0
        lines.append(f"Your deck (Fire): {fire_pct:.0f}% win-rate over {fire_count} games. Meta share: {fire_share:.0f}%.")
    else:
        fire_pct = None
        lines.append("Your deck (Fire): not found in replay dataset.")

    if ranked:
        dom_fp, dom_count = ranked[0]
        dom_pct = 100 * archetype_wins[dom_fp] / dom_count if dom_count else 0.0
        dom_share = 100 * dom_count / total_games if total_games else 0.0
        dom_name = key_pokemon_names(archetype_deck_sample[dom_fp], pokemon_ids, names)
        dom_label = dom_name[0] if dom_name else "Unknown"
        lines.append(f"Dominant archetype: {dom_label} ({dom_share:.0f}% of games, {dom_pct:.0f}% win-rate).")

        switch = (
            fire_pct is not None
            and fire_pct < 45
            and dom_pct > 55
            and dom_share > 30
        )
        recommendation = "switch" if switch else "stay"
        fire_pct_str = f"{fire_pct:.0f}%" if fire_pct is not None else "n/a"
        lines.append(f"Recommendation: {recommendation} (fire={fire_pct_str} dominant={dom_pct:.0f}%/{dom_share:.0f}% share).")

    # Notable trainers in top archetypes
    lines.append("")
    lines.append("Notable trainers in top archetypes:")
    for fp, count in ranked[:5]:
        deck = archetype_deck_sample[fp]
        key_names = key_pokemon_names(deck, pokemon_ids, names)
        label = key_names[0] if key_names else "Unknown"
        top_trainers = archetype_trainers[fp].most_common(5)
        trainer_names = ", ".join(f"{card_display_name(cid, names)}x{cnt / count:.1f}" for cid, cnt in top_trainers)
        lines.append(f"  {label}: {trainer_names}")

    report = "\n".join(lines)
    print(report)

    out_path = REPO_ROOT / args.out
    out_path.write_text(report + "\n", encoding="utf-8")
    print(f"\nWrote report to {out_path}")


if __name__ == "__main__":
    main()
