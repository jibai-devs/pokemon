"""
PKM-013: Process EN_Card_Data.csv into a clean, one-card-per-row dataset.

Input:  data/EN_Card_Data.csv        (one row per move)
Output: data/cards_processed.csv     (one row per card, moves as JSON arrays)
        data/cards.duckdb            (DuckDB with `cards` and `moves` tables)

Usage:
    python scripts/process_cards.py
    python scripts/process_cards.py --no-duckdb
"""

import argparse
import csv
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).parent.parent
INPUT = ROOT / "data" / "EN_Card_Data.csv"
OUTPUT_CSV = ROOT / "data" / "cards_processed.csv"
OUTPUT_DB = ROOT / "data" / "cards.duckdb"

POKEMON_STAGES = {"Basic Pokemon", "Stage 1 Pokemon", "Stage 2 Pokemon"}
TRAINER_TYPES = {"Item", "Supporter", "Pokemon Tool", "Stadium"}
ENERGY_TYPES = {"Basic Energy", "Special Energy"}

# Column rename map applied after loading (original -> clean)
COL_RENAME = {
    "Stage (Pokémon)/Type (Energy and Trainer)": "Stage/Type",
}

def normalize_text(s: str) -> str:
    return s.replace("Pokémon", "Pokemon").replace("Pokémon", "Pokemon")


CARD_COLS = [
    "Card ID",
    "Card Name",
    "Expansion",
    "Collection No.",
    "Stage/Type",
    "Rule",
    "Category",
    "Previous stage",
    "HP",
    "Type",
    "Weakness",
    "Resistance (Type)",
    "Retreat",
]
MOVE_COLS = ["Move Name", "Cost", "Damage", "Effect Explanation"]


def clean(v: str) -> str:
    v = v.strip()
    return "" if v in ("n/a", "N/A") else v


def parse_hp(v: str) -> int | None:
    m = re.match(r"(\d+)", v)
    return int(m.group(1)) if m else None


def parse_retreat(v: str) -> int | None:
    m = re.match(r"(\d+)", v)
    return int(m.group(1)) if m else None


def parse_damage(v: str) -> int | None:
    m = re.match(r"(\d+)", v)
    return int(m.group(1)) if m else None


def load_raw() -> list[dict]:
    with open(INPUT, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    # Rename columns and normalize text in all values
    renamed = []
    for row in rows:
        new_row = {}
        for k, v in row.items():
            new_key = COL_RENAME.get(k, k)
            new_row[new_key] = normalize_text(v) if v else v
        renamed.append(new_row)
    return renamed


def process(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    """Return (cards, moves) where cards is one-row-per-card."""
    # Group by Card ID preserving order
    by_id: dict[str, list[dict]] = defaultdict(list)
    id_order: list[str] = []
    for row in rows:
        cid = row["Card ID"].strip()
        if cid not in by_id:
            id_order.append(cid)
        by_id[cid].append(row)

    cards, moves = [], []

    for cid in id_order:
        group = by_id[cid]
        first = group[0]

        card: dict = {col: clean(first.get(col, "")) for col in CARD_COLS}
        card["hp_int"] = parse_hp(card["HP"])
        card["retreat_int"] = parse_retreat(card["Retreat"])

        card_moves = []
        for r in group:
            name = clean(r.get("Move Name", ""))
            cost = clean(r.get("Cost", ""))
            dmg = clean(r.get("Damage", ""))
            effect = clean(r.get("Effect Explanation", ""))
            if not name and not cost and not dmg and not effect:
                continue
            mv = {
                "card_id": cid,
                "move_name": name,
                "cost": cost,
                "damage": dmg,
                "damage_int": parse_damage(dmg),
                "effect": effect,
            }
            card_moves.append(mv)
            moves.append(mv)

        card["moves_json"] = json.dumps(card_moves, ensure_ascii=False)
        card["move_count"] = len(card_moves)
        cards.append(card)

    return cards, moves


def write_csv(cards: list[dict], path: Path | None = None) -> None:
    if not cards:
        return
    out = path or OUTPUT_CSV
    fieldnames = list(cards[0].keys())
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(cards)
    print(f"Wrote {len(cards):4d} cards -> {out.name}")


def split_and_write(cards: list[dict]) -> None:
    buckets = {
        "pokemon": [c for c in cards if c.get("Stage/Type") in POKEMON_STAGES],
        "trainer": [c for c in cards if c.get("Stage/Type") in TRAINER_TYPES],
        "energy":  [c for c in cards if c.get("Stage/Type") in ENERGY_TYPES],
        "other":   [c for c in cards if c.get("Stage/Type") not in POKEMON_STAGES | TRAINER_TYPES | ENERGY_TYPES],
    }
    for name, subset in buckets.items():
        if subset:
            write_csv(subset, ROOT / "data" / f"cards_{name}.csv")


def write_duckdb(cards: list[dict], moves: list[dict]) -> None:
    try:
        import duckdb
    except ImportError:
        print("duckdb not installed — skipping DB output (pip install duckdb)")
        return

    con = duckdb.connect(str(OUTPUT_DB))

    # cards table
    con.execute("DROP TABLE IF EXISTS cards")
    con.execute("""
        CREATE TABLE cards AS
        SELECT * FROM read_csv_auto(?)
    """, [str(OUTPUT_CSV)])

    # moves table (normalised)
    con.execute("DROP TABLE IF EXISTS moves")
    con.execute("""
        CREATE TABLE moves (
            card_id     INTEGER,
            move_name   VARCHAR,
            cost        VARCHAR,
            damage      VARCHAR,
            damage_int  INTEGER,
            effect      VARCHAR
        )
    """)
    con.executemany(
        "INSERT INTO moves VALUES (?, ?, ?, ?, ?, ?)",
        [
            (
                int(m["card_id"]) if m["card_id"].isdigit() else None,
                m["move_name"],
                m["cost"],
                m["damage"],
                m["damage_int"],
                m["effect"],
            )
            for m in moves
        ],
    )
    con.close()
    print(f"Wrote cards + moves tables -> {OUTPUT_DB}")


def print_summary(cards: list[dict], moves: list[dict]) -> None:
    total = len(cards)
    pokemon = sum(1 for c in cards if "Pokemon" in c.get("Stage/Type", ""))
    ex_rule = sum(1 for c in cards if c.get("Rule") == "Pokémon ex")
    no_hp = sum(1 for c in cards if not c.get("HP"))
    print(f"\n--- Summary ---")
    print(f"Total cards  : {total}")
    print(f"Pokémon      : {pokemon}")
    print(f"ex Pokémon   : {ex_rule}")
    print(f"Non-Pokémon  : {total - pokemon}")
    print(f"No HP (E/T)  : {no_hp}")
    print(f"Total moves  : {len(moves)}")
    if moves:
        dmg_vals = [m["damage_int"] for m in moves if m["damage_int"] is not None]
        if dmg_vals:
            print(f"Damage range : {min(dmg_vals)} - {max(dmg_vals)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-duckdb", action="store_true")
    args = parser.parse_args()

    rows = load_raw()
    print(f"Loaded {len(rows)} raw rows from {INPUT}")

    cards, moves = process(rows)

    write_csv(cards)
    split_and_write(cards)
    if not args.no_duckdb:
        write_duckdb(cards, moves)

    print_summary(cards, moves)


if __name__ == "__main__":
    main()
