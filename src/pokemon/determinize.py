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
  draw order). If a ruleset has already deduced *which specific* unseen
  cards are prized (e.g. `pokemon.heuristics.dragapult.prize_check`'s
  `deck_memory`), pass those ids as `known_prize_ids` to use them directly
  instead of an arbitrary split — turns "guess all 6 prizes" into "we know
  some of them, guess the rest," which also makes the `myDeck` guess more
  accurate (whatever's left over is unseen cards known to *not* be prized).
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
from collections.abc import Sequence

from pokemon.types import (
    CardId,
    CardState,
    GameplayObservation,
    PlayerState,
    SearchStartConfig,
)


def _card_ids(card: CardState) -> list[CardId]:
    """A visible card dict plus everything attached/underneath it: the card
    itself, any attached energy cards, attached tools, and pre-evolution
    cards stacked beneath it (each of those occupied its own deck slot)."""
    ids = [card["id"]]
    for zone in ("energyCards", "tools", "preEvolution"):
        ids.extend(c["id"] for c in (card.get(zone) or []))
    return ids


def _zone_ids(player: PlayerState) -> list[CardId]:
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


def _active_visible(player: PlayerState) -> bool:
    """Whether `player`'s active slot already holds a known Pokemon.
    `active` can be `[]` (setup not resolved) or `[None]` (KO'd, not yet
    replaced) — both count as hidden/empty, not "visible", so a guess is
    still needed to give the search a legal active Pokemon to work with."""
    return any(c is not None for c in (player.get("active") or []))


def _split_unseen(
    unseen: Counter[CardId], prize_count: int, rng: random.Random
) -> tuple[list[CardId], list[CardId]]:
    """Expand `unseen` into a flat list, shuffle, and split into
    (prize, deck) of sizes (prize_count, remainder)."""
    pool = list(unseen.elements())
    rng.shuffle(pool)
    prize_count = min(prize_count, len(pool))
    return pool[:prize_count], pool[prize_count:]


def _own_determinization(
    player: PlayerState,
    full_deck: Sequence[CardId],
    rng: random.Random,
    known_prize_ids: Sequence[CardId] | None = None,
) -> tuple[list[CardId], list[CardId]]:
    """(prize, deck) guess for a player whose full 60-card composition we
    know (ourselves). Clips at zero per-id so transient off-by-one noise in
    a mid-step `obs` snapshot (a card counted in two zones for one frame)
    degrades gracefully rather than raising.

    If `known_prize_ids` is given (a ruleset's own prize deduction), use
    those specific card identities as (part of) the prize guess instead of
    an arbitrary random split of the unseen pool. Never trusts more of it
    than the unseen pool can actually back up, and never returns more
    entries than `prize_count` -- a stale or partial deduction (fewer
    prizes deduced than remain, or a card no longer actually unseen)
    degrades to filling the rest randomly rather than raising or
    overcounting.
    """
    seen = Counter(_zone_ids(player))
    unseen = Counter(full_deck)
    unseen.subtract(seen)
    for cid in list(unseen):
        if unseen[cid] < 0:
            unseen[cid] = 0
    prize_count = len(player.get("prize") or [])

    if known_prize_ids:
        known = Counter(known_prize_ids)
        for cid in list(known):
            known[cid] = min(known[cid], unseen.get(cid, 0))
        confirmed_prize = list(known.elements())[:prize_count]
        remaining = Counter(unseen)
        remaining.subtract(Counter(confirmed_prize))
        for cid in list(remaining):
            if remaining[cid] < 0:
                remaining[cid] = 0
        extra_needed = max(0, prize_count - len(confirmed_prize))
        extra_prize, deck_order = _split_unseen(remaining, extra_needed, rng)
        return confirmed_prize + extra_prize, deck_order

    return _split_unseen(unseen, prize_count, rng)


_DEFAULT_FILLER: CardId = 2  # Fire Energy — always a legal, inert card id.
# SearchBegin rejects non-Pokémon enemyActive ids (Export/Search.h error 2).
_DEFAULT_ACTIVE_FILLER: CardId = 119  # Dreepy — Basic Pokémon always in CardTable.


def _opponent_determinization(
    player: PlayerState, rng: random.Random
) -> tuple[list[CardId], list[CardId], list[CardId], list[CardId]]:
    """(prize, deck, hand, active) guess for the opponent, whose true 60-card
    composition we don't know. Placeholder strategy: resample (with
    replacement) from cards we've actually seen them reveal (board +
    discard); falls back to a generic filler id before anything's been
    revealed. Not a real belief model — see module docstring."""
    revealed = _zone_ids(player)
    pool = revealed or [_DEFAULT_FILLER]
    # Prefer revealed board PEKEmon for a hidden active; never use Energy.
    board_ids = []
    for c in (player.get("active") or []) + (player.get("bench") or []):
        if c is not None:
            board_ids.append(c["id"])
    active_pool = board_ids or [_DEFAULT_ACTIVE_FILLER]

    def sample(n: int) -> list[CardId]:
        return [rng.choice(pool) for _ in range(n)]

    prize_count = len(player.get("prize") or [])
    deck_count = player.get("deckCount") or 0
    hand_count = player.get("handCount") or 0
    active_hidden = not _active_visible(player)

    prize = sample(prize_count)
    deck = sample(deck_count)
    hand = sample(hand_count) if player.get("hand") is None else []
    active = [rng.choice(active_pool)] if active_hidden else []
    return prize, deck, hand, active


def sample_determinization(
    obs: GameplayObservation,
    my_deck: Sequence[CardId],
    rng: random.Random | None = None,
    known_prize_ids: Sequence[CardId] | None = None,
) -> SearchStartConfig:
    """Build one `SearchStartConfig`-shaped dict (see `Search.h:19`) from a
    live `obs`, guessing every zone the native search API doesn't already
    know.

    `my_deck` is the 60-card list we submitted this game (`decks.DECKS[...]`)
    — required because it's the one piece of ground truth this function
    can't read off `obs` itself (our own prize/deck contents are hidden from
    us same as anyone else's, so composition has to come from the
    submission, not the observation).

    `known_prize_ids`, if given, are specific card ids a ruleset has already
    deduced are prized (see `_own_determinization`) -- passed straight
    through to make the *our own side* half of the guess more accurate than
    a fully random split; has no effect on the opponent-side guess, which
    remains a genuine unknown handled by `_opponent_determinization`.

    Returns keys matching `SearchStartConfig`'s fields:
    `manualCoin, myDeck, myPrize, enemyDeck, enemyPrize, enemyHand,
    enemyActive`. `myHand`/`myActive` aren't included — the engine already
    knows those from the serialized blob (they're always visible to us).
    """
    rng = rng or random.Random()
    current = obs["current"]
    my_idx = current.get("yourIndex", 0)
    players = current.get("players")
    if players is None:
        raise KeyError("players")
    me = players[my_idx]
    opp = players[1 - my_idx]

    my_prize, my_deck_order = _own_determinization(me, my_deck, rng, known_prize_ids=known_prize_ids)
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
