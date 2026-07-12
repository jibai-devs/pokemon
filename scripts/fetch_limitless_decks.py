"""Build data/meta_decks/library.json from a Limitless TCG tournament's decklists.

Fetches https://limitlesstcg.com/tournaments/<id>/decklists (caching raw HTML
under data/meta_decks/raw/ so re-parsing never re-hits the site), parses every
player's 60-card list, maps card names to competition card IDs, groups lists
into archetypes, and computes each archetype's core (cards in >=90% of its
lists) and flex slots.

Card ID resolution is barcode-style, not name-guessing: every decklist-card
div on the page carries the exact print (set code + collection number), which
we match directly against data/cards_processed.csv's Expansion/Collection No.
columns. That resolves the overwhelming majority of cards unambiguously. The
remainder falls back to an exact card-name lookup (after normalizing curly
apostrophes) plus a hardcoded basic-energy table, since our competition
catalog collapses per-print reprints into one card ID keyed by name. Anything
still unresolved is reported, not guessed — see Validation report below.

Usage:
    uv run python scripts/fetch_limitless_decks.py
    uv run python scripts/fetch_limitless_decks.py --tournament-id 550 --force-refetch
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import unicodedata
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CARDS_CSV = REPO_ROOT / "data" / "cards_processed.csv"
RAW_DIR = REPO_ROOT / "data" / "meta_decks" / "raw"
LIBRARY_PATH = REPO_ROOT / "data" / "meta_decks" / "library.json"

# Some decklist titles are tech variants of the same real archetype (the site
# buckets them separately, but they share the same headline Pokemon and game
# plan). Merge those into one family so the library's core/flex reflects the
# real archetype rather than fragmenting it across near-identical builds.
# Titles not listed here are used as their own archetype key verbatim.
ARCHETYPE_FAMILY = {
    "Dragapult Dusknoir": "Dragapult",
    "Dragapult Dudunsparce": "Dragapult",
    "Dragapult Blaziken": "Dragapult",
    "Ogerpon Box": "Ogerpon",
    "Ogerpon Meganium": "Ogerpon",
}

# Basic energies are named e.g. "Basic {R} Energy" in our catalog (see
# pokemon.catalog.CARD_NAMES) but "Fire Energy" on Limitless. {G/R/W/L/P/F/D/M}
# are fixed competition card IDs 1-8 in that order.
ENERGY_NAME_TO_ID = {
    "Grass Energy": "1",
    "Fire Energy": "2",
    "Water Energy": "3",
    "Lightning Energy": "4",
    "Psychic Energy": "5",
    "Fighting Energy": "6",
    "Darkness Energy": "7",
    "Metal Energy": "8",
}

DECKLIST_TOGGLE_RE = re.compile(r'data-toggle data-target="decklist-\d+">([^<]+)<')
DECKLIST_TITLE_RE = re.compile(r'class="decklist-title">\s*([^<\n]+?)\s*<')
CARD_RE = re.compile(
    r'class="decklist-card" data-set="([^"]*)" data-number="([^"]*)"[^>]*>\s*'
    r'<a class="card-link"[^>]*>\s*'
    r'<span class="card-count">(\d+)</span>\s*'
    r'<span class="card-name">([^<]+)</span>'
)


def _normalize_name(name: str) -> str:
    """Fold curly apostrophes and diacritics (Limitless "Pokémon" vs our catalog's
    ASCII "Pokemon") so both sides of the name match compare equal."""
    name = name.replace("’", "'").strip()  # noqa: RUF001
    folded = unicodedata.normalize("NFKD", name)
    return "".join(c for c in folded if not unicodedata.combining(c))


def fetch_html(tournament_id: int, *, force_refetch: bool) -> str:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = RAW_DIR / f"tournament_{tournament_id}_decklists.html"
    if cache_path.exists() and not force_refetch:
        return cache_path.read_text(encoding="utf-8")
    url = f"https://limitlesstcg.com/tournaments/{tournament_id}/decklists"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        html = resp.read().decode("utf-8")
    cache_path.write_text(html, encoding="utf-8")
    return html


def parse_decklists(html: str, source_url: str) -> list[dict]:
    """Return one dict per player: {placing, player, title, cards: [(set, number, count, name), ...]}."""
    chunks = html.split('<div class="tournament-decklist">')[1:]
    entries = []
    for chunk in chunks:
        toggle_m = DECKLIST_TOGGLE_RE.search(chunk)
        title_m = DECKLIST_TITLE_RE.search(chunk)
        if not toggle_m or not title_m:
            raise ValueError(f"Could not find toggle/title in a decklist chunk from {source_url}")
        placing_player = toggle_m.group(1).strip()
        placing, player = placing_player.split(" ", 1)
        title = title_m.group(1).strip()
        cards = [
            (setc, num, int(count), _normalize_name(name))
            for setc, num, count, name in CARD_RE.findall(chunk)
        ]
        entries.append({"placing": placing, "player": player, "title": title, "cards": cards})
    return entries


class CardResolver:
    def __init__(self, cards_csv: Path):
        self.by_setnum: dict[tuple[str, str], str] = {}
        self.by_name: dict[str, set[str]] = defaultdict(set)
        with cards_csv.open(encoding="utf-8") as f:
            for row in csv.DictReader(f):
                self.by_setnum[(row["Expansion"], row["Collection No."])] = row["Card ID"]
                self.by_name[_normalize_name(row["Card Name"])].add(row["Card ID"])
        self.unresolved: Counter[tuple[str, str]] = Counter()
        self.ambiguous: Counter[tuple[str, tuple[str, ...]]] = Counter()
        self.short_lists: list[tuple[str, str, str, int]] = []

    def resolve(self, setc: str, num: str, name: str) -> str | None:
        card_id = self.by_setnum.get((setc, num))
        if card_id is not None:
            return card_id
        if name in ENERGY_NAME_TO_ID:
            return ENERGY_NAME_TO_ID[name]
        ids = self.by_name.get(name)
        if not ids:
            self.unresolved[(setc, name)] += 1
            return None
        if len(ids) > 1:
            self.ambiguous[(name, tuple(sorted(ids)))] += 1
            return None
        return next(iter(ids))


def build_library(entries: list[dict], resolver: CardResolver, source_url: str) -> dict:
    total_lists = len(entries)
    families: dict[str, list[dict]] = defaultdict(list)

    for entry in entries:
        family = ARCHETYPE_FAMILY.get(entry["title"], entry["title"])
        card_counts: dict[str, int] = defaultdict(int)
        for setc, num, count, name in entry["cards"]:
            card_id = resolver.resolve(setc, num, name)
            if card_id is None:
                continue
            card_counts[card_id] += count
        total = sum(card_counts.values())
        if total != 60:
            resolver.short_lists.append((entry["placing"], entry["player"], entry["title"], total))
        families[family].append(
            {
                "placing": entry["placing"],
                "player": entry["player"],
                "title": entry["title"],
                "cards": dict(card_counts),
            }
        )

    archetypes = {}
    for family, lists in families.items():
        n = len(lists)
        presence: Counter[str] = Counter()
        min_count: dict[str, int] = {}
        max_count: dict[str, int] = {}
        for lst in lists:
            for card_id, count in lst["cards"].items():
                presence[card_id] += 1
                min_count[card_id] = min(min_count.get(card_id, count), count)
                max_count[card_id] = max(max_count.get(card_id, count), count)

        core = {}
        flex = {}
        for card_id, seen_in in presence.items():
            if seen_in / n >= 0.9:
                core[card_id] = min_count[card_id]
            else:
                flex[card_id] = {
                    "lists_with": seen_in,
                    "count_range": [min_count[card_id], max_count[card_id]],
                }

        archetypes[family] = {
            "meta_share": n / total_lists,
            "lists": lists,
            "core": core,
            "flex": flex,
        }

    return {
        "source_url": source_url,
        "total_lists": total_lists,
        "archetypes": archetypes,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tournament-id", type=int, default=550)
    parser.add_argument("--force-refetch", action="store_true")
    parser.add_argument("--out", type=Path, default=LIBRARY_PATH)
    args = parser.parse_args()

    source_url = f"https://limitlesstcg.com/tournaments/{args.tournament_id}/decklists"
    html = fetch_html(args.tournament_id, force_refetch=args.force_refetch)
    entries = parse_decklists(html, source_url)

    resolver = CardResolver(CARDS_CSV)
    library = build_library(entries, resolver, source_url)

    if resolver.unresolved or resolver.ambiguous or resolver.short_lists:
        print("=== Validation report: unresolved cards ===", file=sys.stderr)
        for (setc, name), count in resolver.unresolved.most_common():
            print(f"  UNMAPPED  set={setc!r} name={name!r}  ({count} occurrences)", file=sys.stderr)
        for (name, ids), count in resolver.ambiguous.most_common():
            print(f"  AMBIGUOUS name={name!r} ids={ids}  ({count} occurrences)", file=sys.stderr)
        for placing, player, title, total in resolver.short_lists:
            print(
                f"  SHORT LIST  {placing} {player} ({title}) resolved to {total}/60 cards",
                file=sys.stderr,
            )
        print(
            "Resolve these by adding to ENERGY_NAME_TO_ID / a name override, "
            "or confirm the (set, number) pair belongs in data/cards_processed.csv.",
            file=sys.stderr,
        )
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(library, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Wrote {len(library['archetypes'])} archetypes from {library['total_lists']} lists to {args.out}")
    for family, data in sorted(library["archetypes"].items(), key=lambda kv: -kv[1]["meta_share"]):
        print(f"  {family:30s} meta_share={data['meta_share']:.1%}  core={len(data['core'])} cards")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
