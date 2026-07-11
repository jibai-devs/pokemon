"""Determinization sampler for `docs/plans/009_native_search_plan.md` Phase 1.

`SearchBegin` (the native engine's forward-simulation entry point, see
`ptcgProgram 22/Export.cpp:96`) only fills a hidden zone from its
`SearchStartConfig` argument when the serialized state doesn't already know
that zone's contents. Real captured `obs` snapshots (see
`_zone_ids`/`sample_determinization` below, validated against
`heuristic_loop/logs/**/*.json`) confirm this includes zones we'd naively
assume we already know: our own deck order and our own prize contents are
*not* visible to us either (`prize` entries are always `None` until taken,
`hand`/`discard`/`active`/`bench` are the only fully-visible zones) — this
matches real Pokemon TCG rules (you don't know your own prizes until you take
them), not an engine quirk.

This module builds a single legal, composition-consistent guess for every
hidden zone `SearchStartConfig` needs:

- **Our own deck/prize**: exact composition is known (we submitted the
  60-card list) — just need a random split of the *unseen* cards (full deck
  minus everything currently visible in our hand/board/discard) into "prize"
  (fixed size = current prize-array length) and "deck" (the rest, in random
  draw order).
- **Opponent's deck/hand/prize/active**: composition is genuinely unknown.
  Absent archetype/meta modeling (see `tickets/PKM-015.md`, a separate,
  heavier ISMCTS-belief-modeling project this does *not* attempt to
  replace), the best available signal is an empirical resample from cards
  the opponent has actually revealed (board + discard) — a placeholder, not
  a real belief model. Good enough for near-term consumers like a
  single-turn Lethal Line Finder, where the opponent's hidden identities
  mostly don't get exercised before the search terminates (see docs/plans/009's
  "still unknown" section).
"""

import random
from collections import Counter

CardId = int


def _card_ids(card: dict) -> list[CardId]:
    """A visible card dict plus everything attached/underneath it: the card
    itself, any attached energy cards, attached tools, and pre-evolution
    cards stacked beneath it (each of those occupied its own deck slot)."""
    ids = [card["id"]]
    for zone in ("energyCards", "tools", "preEvolution"):
        ids.extend(c["id"] for c in (card.get(zone) or []))
    return ids


def _zone_ids(player: dict) -> list[CardId]:
    """Every card id currently visible for `player`: hand, discard, and
    active/bench including attachments and pre-evolutions. Deliberately
    excludes `prize` (always hidden, even for the prize owner) and `deck`
    (only a count, never contents)."""
    ids: list[CardId] = []
    for c in player.get("discard") or []:
        ids.append(c["id"])
    for c in player.get("hand") or []:
        ids.append(c["id"])
    for c in (player.get("active") or []) + (player.get("bench") or []):
        if c is not None:  # active can be `[None]` — slot exists, no Pokemon there yet
            ids.extend(_card_ids(c))
    return ids


def _active_visible(player: dict) -> bool:
    """Whether `player`'s active slot already holds a known Pokemon.
    `active` can be `[]` (setup not resolved) or `[None]` (KO'd, not yet
    replaced) — both count as hidden/empty, not "visible", so a guess is
    still needed to give the search a legal active Pokemon to work with."""
    return any(c is not None for c in (player.get("active") or []))


def _split_unseen(
    unseen: Counter, prize_count: int, rng: random.Random
) -> tuple[list[CardId], list[CardId]]:
    """Expand `unseen` into a flat list, shuffle, and split into
    (prize, deck) of sizes (prize_count, remainder)."""
    pool = list(unseen.elements())
    rng.shuffle(pool)
    prize_count = min(prize_count, len(pool))
    return pool[:prize_count], pool[prize_count:]


def _own_determinization(
    player: dict, full_deck: list[CardId], rng: random.Random
) -> tuple[list[CardId], list[CardId]]:
    """(prize, deck) guess for a player whose full 60-card composition we
    know (ourselves). Clips at zero per-id so transient off-by-one noise in
    a mid-step `obs` snapshot (a card counted in two zones for one frame)
    degrades gracefully rather than raising."""
    seen = Counter(_zone_ids(player))
    unseen = Counter(full_deck)
    unseen.subtract(seen)
    for cid in list(unseen):
        if unseen[cid] < 0:
            unseen[cid] = 0
    prize_count = len(player.get("prize") or [])
    return _split_unseen(unseen, prize_count, rng)


_DEFAULT_FILLER: CardId = 2  # Fire Energy — always a legal, inert card id.


def _opponent_determinization(
    player: dict, rng: random.Random
) -> tuple[list[CardId], list[CardId], list[CardId], list[CardId]]:
    """(prize, deck, hand, active) guess for the opponent, whose true 60-card
    composition we don't know. Placeholder strategy: resample (with
    replacement) from cards we've actually seen them reveal (board +
    discard); falls back to a generic filler id before anything's been
    revealed. Not a real belief model — see module docstring."""
    revealed = _zone_ids(player)
    pool = revealed or [_DEFAULT_FILLER]

    def sample(n: int) -> list[CardId]:
        return [rng.choice(pool) for _ in range(n)]

    prize_count = len(player.get("prize") or [])
    deck_count = player.get("deckCount") or 0
    hand_count = player.get("handCount") or 0
    active_hidden = not _active_visible(player)

    prize = sample(prize_count)
    deck = sample(deck_count)
    hand = sample(hand_count) if player.get("hand") is None else []
    active = sample(1) if active_hidden else []
    return prize, deck, hand, active


def sample_determinization(
    obs: dict, my_deck: list[CardId], rng: random.Random | None = None
) -> dict:
    """Build one `SearchStartConfig`-shaped dict (see `Search.h:19`) from a
    live `obs`, guessing every zone the native search API doesn't already
    know.

    `my_deck` is the 60-card list we submitted this game (`decks.DECKS[...]`)
    — required because it's the one piece of ground truth this function
    can't read off `obs` itself (our own prize/deck contents are hidden from
    us same as anyone else's, so composition has to come from the
    submission, not the observation).

    Returns keys matching `SearchStartConfig`'s fields:
    `manualCoin, myDeck, myPrize, enemyDeck, enemyPrize, enemyHand,
    enemyActive`. `myHand`/`myActive` aren't included — the engine already
    knows those from the serialized blob (they're always visible to us).
    """
    rng = rng or random.Random()
    current = obs["current"]
    my_idx = current.get("yourIndex", 0)
    players = current["players"]
    me = players[my_idx]
    opp = players[1 - my_idx]

    my_prize, my_deck_order = _own_determinization(me, my_deck, rng)
    enemy_prize, enemy_deck, enemy_hand, enemy_active = _opponent_determinization(opp, rng)

    return {
        "manualCoin": False,
        "myDeck": my_deck_order,
        "myPrize": my_prize,
        "enemyDeck": enemy_deck,
        "enemyPrize": enemy_prize,
        "enemyHand": enemy_hand,
        "enemyActive": enemy_active,
    }
