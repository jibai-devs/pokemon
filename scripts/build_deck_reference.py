"""Generate a card/attack/ability reference sheet for a deck.

Pulls exact stats (HP, type, weakness/resistance, retreat cost, attack
cost/damage/text, ability text) straight from the reverse-engineered
catalogs (`reverse-engineering/data/`) rather than relying on memorized
Pokemon knowledge, which isn't reliable for newer or unfamiliar card pools.

Usage:
    python scripts/build_deck_reference.py --deck psychic > deck/001_psychic_deck_reference.md
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "reverse-engineering" / "data"

ENERGY_TYPE = {
    0: "Colorless",
    1: "Grass",
    2: "Fire",
    3: "Water",
    4: "Lightning",
    5: "Psychic",
    6: "Fighting",
    7: "Darkness",
    8: "Metal",
    9: "Dragon",
}


def _clean(text: str) -> str:
    """Fix mojibake in the raw catalog JSON (apostrophes/e-acute got mangled)."""
    return text.replace("Pok�mon", "Pokemon").replace("�", "'")


def _energy_label(code: int) -> str:
    return ENERGY_TYPE.get(code, f"?{code}")


def main() -> None:
    sys.path.insert(0, str(REPO_ROOT / "src"))
    from pokemon.decks import DECKS

    parser = argparse.ArgumentParser()
    parser.add_argument("--deck", required=True, choices=sorted(DECKS))
    parser.add_argument("--out", help="Write to this file (UTF-8) instead of stdout")
    args = parser.parse_args()

    if args.out:
        sys.stdout = open(args.out, "w", encoding="utf-8", newline="\n")

    deck = DECKS[args.deck]
    counts = Counter(deck)

    cards = {
        c["cardId"]: c
        for c in json.loads((DATA_DIR / "all_cards.json").read_text(encoding="utf-8"))
    }
    attacks = {
        a["attackId"]: a
        for a in json.loads((DATA_DIR / "all_attacks.json").read_text(encoding="utf-8"))
    }

    print(f"# {args.deck.title()} Deck — Card Reference\n")
    print(
        f'Generated from `reverse-engineering/data/` for `pokemon.decks.DECKS["{args.deck}"]` '
        f"({len(deck)} cards, {len(counts)} unique). Regenerate with:\n"
    )
    print(f"```bash\npython scripts/build_deck_reference.py --deck {args.deck}\n```\n")

    for cid, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
        c = cards.get(cid)
        if not c:
            print(f"## {n}x Card#{cid} — MISSING FROM CATALOG\n")
            continue

        name = _clean(c["name"])
        print(f"## {n}x {name} (#{cid})\n")

        if c["hp"]:
            wk = _energy_label(c["weakness"]) if c["weakness"] is not None else "-"
            rs = _energy_label(c["resistance"]) if c["resistance"] is not None else "-"
            ty = _energy_label(c["energyType"])
            stage = "Basic" if c["basic"] else "Stage 1" if c["stage1"] else "Stage 2" if c["stage2"] else "?"
            tags = []
            if c["ex"]:
                tags.append("ex")
            if c["megaEx"]:
                tags.append("Mega ex")
            if c["aceSpec"]:
                tags.append("ACE SPEC")
            tagstr = f" ({', '.join(tags)})" if tags else ""
            evolves = f" | Evolves from {c['evolvesFrom']}" if c.get("evolvesFrom") else ""
            print(
                f"- **{stage}{tagstr} | {ty} | HP {c['hp']} | Weakness {wk} | "
                f"Resistance {rs} | Retreat {c['retreatCost']}**{evolves}\n"
            )

        for skill in c["skills"]:
            print(f"- **Ability — {_clean(skill['name'].strip())}:** {_clean(skill['text'])}\n")

        for aid in c["attacks"]:
            a = attacks.get(aid)
            if not a:
                print(f"- **Attack — #{aid} — MISSING FROM CATALOG**\n")
                continue
            cost = "".join(_energy_label(e)[0] for e in a["energies"])
            dmg = f" ({a['damage']})" if a["damage"] else ""
            text = f" — {_clean(a['text'])}" if a["text"] else ""
            print(f"- **Attack — {_clean(a['name'])}{dmg}** [{cost}]{text}\n")


if __name__ == "__main__":
    main()
