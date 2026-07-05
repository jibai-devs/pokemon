# 001 Psychic Deck

Psychic-type deck built around **Slowking's Seek Inspiration** as the primary
win condition — see Strategy below. Mega Kangaskhan ex and Latias ex are the
backup attacker/mobility plan.

## Deck List

| Count | Card ID | Name | Type |
|-------|---------|------|------|
| 4 | 162 | Slowpoke | Pokemon (Basic) |
| 3 | 163 | Slowking | Pokemon (Stage 1) |
| 3 | 756 | Mega Kangaskhan ex | Pokemon (Basic) |
| 2 | 184 | Latias ex | Pokemon (Basic) |
| 2 | 144 | Kyurem | Pokemon (Basic) |
| 2 | 276 | Metagross | Pokemon (Stage 2) |
| 1 | 1071 | Meowth ex | Pokemon (Basic) |
| 1 | 956 | Zeraora | Pokemon (Basic) |
| 1 | 272 | Lillie's Clefairy ex | Pokemon (Basic) |
| 1 | 140 | Fezandipiti ex | Pokemon (Basic) |
| 4 | 1227 | Lillie's Determination | Supporter |
| 4 | 1188 | Ciphermaniac's Codebreaking | Supporter |
| 4 | 1152 | Poke Pad | Item |
| 4 | 1121 | Ultra Ball | Item |
| 3 | 1146 | Wondrous Patch | Item |
| 2 | 1097 | Night Stretcher | Item |
| 1 | 1092 | Secret Box | Item (ACE SPEC) |
| 1 | 1123 | Switch | Item |
| 1 | 1175 | Brave Bangle | Pokemon Tool |
| 1 | 1156 | Lucky Helmet | Pokemon Tool |
| 4 | 1248 | Academy at Night | Stadium |
| 4 | 19 | Telepath Psychic Energy | Special Energy |
| 4 | 5 | Basic Psychic Energy | Energy |
| 3 | 9 | Boomerang Energy | Special Energy |

**Total: 60 cards**

## Card IDs (for agent use)

The canonical, importable definition lives in `pokemon.decks.PSYCHIC_DECK`.

```python
deck = (
    [162]*4 +   # Slowpoke
    [163]*3 +   # Slowking
    [756]*3 +   # Mega Kangaskhan ex
    [184]*2 +   # Latias ex
    [144]*2 +   # Kyurem
    [276]*2 +   # Metagross
    [1071] +    # Meowth ex
    [956] +     # Zeraora
    [272] +     # Lillie's Clefairy ex
    [140] +     # Fezandipiti ex
    [1227]*4 +  # Lillie's Determination
    [1188]*4 +  # Ciphermaniac's Codebreaking
    [1152]*4 +  # Poke Pad
    [1121]*4 +  # Ultra Ball
    [1146]*3 +  # Wondrous Patch
    [1097]*2 +  # Night Stretcher
    [1092] +    # Secret Box
    [1123] +    # Switch
    [1175] +    # Brave Bangle
    [1156] +    # Lucky Helmet
    [1248]*4 +  # Academy at Night
    [19]*4 +    # Telepath Psychic Energy
    [5]*4 +     # Basic Psychic Energy
    [9]*3       # Boomerang Energy
)
```

## Strategy

Full card-by-card breakdown: `deck/001_psychic_deck_reference.md`.

**Primary win condition — Slowking's Seek Inspiration (#163, cost `{P}{C}`):**
discard the top card of your deck; if it's a Pokemon *without a Rule Box*,
use one of its attacks as this attack, for free (Seek Inspiration's cost is
already paid — the copied attack's own cost is irrelevant). "Rule Box" =
ex / Mega ex / V etc., per the card's own reminder text — so only the
**non-ex** Pokemon in this list are legal copy targets:

| Copy target | Attack | Cost (irrelevant when copied) | Effect |
|---|---|---|---|
| Metagross (#276) | Conjoined Beams | `{P}{P}` | 130 dmg |
| Kyurem (#144) | Trifrost | `{W}{W}{M}{M}{C}` | 110 dmg to 3 of opponent's Pokemon |
| Zeraora (#956) | Combat Thunder | `{L}{C}` | 20 + 20/opponent benched Pokemon |
| Slowpoke (#162) | Tackle | `{P}{C}` | 30 dmg |

Mega Kangaskhan ex, Latias ex, Meowth ex, Fezandipiti ex, and Lillie's
Clefairy ex are **all ex — none are legal Seek Inspiration targets** (or
Poke Pad search targets; see below). Metagross and Kyurem never need to
hit the field — they exist purely as high-value discard fodder for this
attack. Metagross's missing evolution line (no Beldum/Metang in this
list) and Kyurem's uncastable `{W}{W}{M}{M}{C}` cost are both irrelevant
for the same reason: Slowking never pays them.

**Everyone else's job is making the "random" discard non-random:**

- **Ciphermaniac's Codebreaking** (#1188, search 2 cards → place on top of
  deck in chosen order) and **Academy at Night** (#1248, stadium, once per
  turn put a card from hand on top of deck) are the real enablers — they
  let you stack Metagross/Kyurem/Zeraora on top before attacking, turning
  Seek Inspiration's discard into a deliberate choice.
- **Wondrous Patch** (#1146) and **Telepath Psychic Energy** (#19) —
  energy acceleration so Slowking hits `{P}{C}` early and keeps firing
  every turn.
- **Ultra Ball** (#1121) / **Poke Pad** (#1152) — search, but Poke Pad's
  text explicitly excludes Rule Box Pokemon too, so it's for fetching
  Slowpoke/Slowking/Metagross/Kyurem/Zeraora, never the ex's.
- **Lillie's Determination** (#1227) — hand refill to keep finding
  Codebreaking/Academy/energy.
- **Lucky Helmet** (#1156) — draws 2 cards when its holder (likely
  Slowking, since it's the one tanking hits while it copy-attacks) is hit.

**Backup plan:** Mega Kangaskhan ex (Run Errand: draw 2/turn while
active, 300 HP tank, Rapid-Fire Combo for `{C}{C}{C}`) and Latias ex
(Skyliner: Basics retreat free) cover board mobility and a fallback
attacker if Slowking gets disrupted or KO'd early.

**To verify in play:** whether Kyurem's copied Trifrost ("discard all
Energy from this Pokemon") resolves against Slowking — if so, Boomerang
Energy (#9) would auto-reattach itself afterward per its own text, which
would make it worth prioritizing as Slowking's attached energy.

Not yet validated against the random-agent baseline or real games — this
is a card-text-level read, not a benchmarked one.

## Performance

Not yet benchmarked. Run:

```bash
~/.local/bin/uv run python -m pokemon play -d psychic -g 10
```
