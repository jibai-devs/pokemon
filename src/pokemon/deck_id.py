"""In-game opponent-deck identification over the PKM-022 meta library.

PKM-023 / `docs/plans/010_meta_deck_library_plan.md` Phase 2: a Bayesian-
elimination belief over `data/meta_decks/library.json`, updated from the
opponent's cumulative revealed cards, degrading gracefully through three
levels as the plan describes:

- **Level 1 — exact list match**: reveals are consistent with exactly one
  known 60-card list. ``opp_remaining``/``p_in_hand`` are exact.
- **Level 2 — archetype core match**: reveals are consistent with an
  archetype's core+flex (no single list survives), and that archetype holds
  a majority of the belief mass. Counts become ranges.
- **Level 3 — true fringe**: nothing concentrates. ``identified_list`` and
  ``opp_remaining``/``p_in_hand`` all return ``None`` — callers should fall
  back to archetype-agnostic defaults (this module deliberately doesn't ship
  a per-Pokemon threat table; that's out of scope per the plan doc).

One mechanism (elimination + meta-share-weighted survivors) produces all
three levels; consumers just read the belief's concentration.
"""

from __future__ import annotations

import functools
import json
import math
from collections import Counter
from pathlib import Path
from typing import Required, TypedDict, cast

from pokemon.cabt_enums import CardType
from pokemon.catalog import card_info
from pokemon.types import CardId, CardState, PlayerState


class FlexEntry(TypedDict):
    count_range: list[int]
    lists_with: int


class DeckListEntry(TypedDict, total=False):
    cards: Required[dict[str, int]]
    player: str
    placing: str
    title: str


class ArchetypeEntry(TypedDict, total=False):
    meta_share: float
    core: dict[str, int]
    flex: dict[str, FlexEntry]
    lists: list[DeckListEntry]


class MetaDeckLibrary(TypedDict, total=False):
    archetypes: Required[dict[str, ArchetypeEntry]]
    total_lists: int

LIBRARY_PATH = Path(__file__).resolve().parents[2] / "data" / "meta_decks" / "library.json"

# Level 2 requires the top archetype to hold a clear majority of belief mass
# before its core/flex ranges are trusted as "the" match (below this, reveals
# are still consistent with too many archetypes to call it — level 3).
_LEVEL2_CONCENTRATION = 0.5

# Archetype-core consistency weighs a reveal that contradicts the core/flex
# table by how identity-revealing that card is: a Pokemon showing up beyond
# what the archetype's list ever runs is a real break (evolution lines and
# draw engines are exactly what the plan doc calls "most identity-revealing"
# -- Dudunsparce line, Starmie shell, etc. recur as a deck's actual identity)
# and eliminates the archetype outright; a Trainer/Energy overage is common
# scrape/tech noise (count ranges here come from ~2026-07 tournament lists,
# not the current game) and is tolerated up to a small budget rather than
# nuking the archetype over one extra Ultra Ball. This is a coarse
# Pokemon-vs-everything-else split, not per-card "is this an engine piece"
# tagging -- the catalog has no such flag, and Pokemon dominate the
# identity-revealing signal regardless.
_POKEMON_OVERAGE_WEIGHT = 3.0
_OTHER_OVERAGE_WEIGHT = 1.0
_CORE_PENALTY_BUDGET = 2.0


def _card_weight(card_id: CardId) -> float:
    info = card_info(card_id)
    if info and info.get("cardType") == CardType.POKEMON:
        return _POKEMON_OVERAGE_WEIGHT
    return _OTHER_OVERAGE_WEIGHT


@functools.lru_cache(maxsize=4)
def _load_library_cached(path: str) -> MetaDeckLibrary:
    return cast(MetaDeckLibrary, json.loads(Path(path).read_text(encoding="utf-8")))


def load_library(path: Path | str | None = None) -> MetaDeckLibrary:
    """Load (and cache) `library.json`. Pass an explicit path in tests to
    avoid the module-level default and its cache colliding with fixtures."""
    return _load_library_cached(str(path or LIBRARY_PATH))


def _card_ids(card: CardState) -> list[CardId]:
    """A visible opponent card plus its attachments/pre-evolutions -- each
    occupied its own deck slot, mirroring `determinize._card_ids`."""
    ids = [card["id"]]
    for zone in ("energyCards", "tools", "preEvolution"):
        ids.extend(c["id"] for c in (card.get(zone) or []))
    return ids


def _visible_ids(opp: PlayerState) -> list[CardId]:
    """Every opponent card id currently visible to us: discard, hand (only
    populated by the engine when actually revealed), and active/bench
    including attachments/pre-evolutions."""
    ids: list[CardId] = []
    for c in opp.get("discard") or []:
        ids.append(c["id"])
    for c in opp.get("hand") or []:
        ids.append(c["id"])
    for c in (opp.get("active") or []) + (opp.get("bench") or []):
        if c is not None:
            ids.extend(_card_ids(c))
    return ids


class DeckIdentifier:
    """Bayesian-elimination belief over a meta library, updated from one
    opponent's cumulative revealed cards across a single game.

    Instantiate once per game (stored on the ruleset's persistent-state
    object, e.g. ``DragapultState.deck_id`` -- itself replaced each game by
    ``admin.build_agent``) and call ``update`` every decision.
    """

    def __init__(self, library: MetaDeckLibrary | None = None):
        self._library = library if library is not None else load_library()
        self.reveals: Counter[CardId] = Counter()
        self._opp_hand_count = 0
        self._opp_deck_count = 0

    def update(self, opp: PlayerState) -> None:
        """Fold in this decision's opponent state. Reveal counts are the
        running max of "how many copies of card X have we simultaneously
        seen" -- a card moving between zones (discard -> hand via Night
        Stretcher, etc.) doesn't un-reveal it, and duplicates seen at once
        (3 Dreepy on board) are stronger evidence than a single sighting."""
        current = Counter(_visible_ids(opp))
        for cid, n in current.items():
            if n > self.reveals[cid]:
                self.reveals[cid] = n
        self._opp_hand_count = opp.get("handCount") or 0
        self._opp_deck_count = opp.get("deckCount") or 0

    def archetypes(self) -> dict[str, ArchetypeEntry]:
        return self._library.get("archetypes", {})

    def _list_consistent(self, cards: dict[str, int]) -> bool:
        return all(cards.get(str(cid), 0) >= n for cid, n in self.reveals.items())

    def _core_consistent(self, archetype: ArchetypeEntry) -> bool:
        """Weighted-penalty consistency (see module-level weight constants):
        accumulates ``excess * weight`` for every reveal beyond the
        archetype's core/flex cap, and survives while that total stays under
        budget -- a single Pokemon overage already blows the budget, several
        Trainer/Energy overages don't."""
        core = archetype.get("core", {})
        flex = archetype.get("flex", {})
        penalty = 0.0
        for cid, n in self.reveals.items():
            key = str(cid)
            if key in core:
                cap = core[key]
            elif key in flex:
                cap = flex[key]["count_range"][1]
            else:
                cap = 0
            excess = n - cap
            if excess > 0:
                penalty += excess * _card_weight(cid)
                if penalty > _CORE_PENALTY_BUDGET:
                    return False
        return True

    def _surviving_lists(self) -> list[tuple[str, DeckListEntry]]:
        return [
            (name, lst)
            for name, arch in self.archetypes().items()
            for lst in arch.get("lists", [])
            if self._list_consistent(lst["cards"])
        ]

    def archetype_belief(self) -> dict[str, float]:
        """Meta-share-weighted posterior over archetypes still consistent
        with the reveals; falls back to the flat meta-share prior over every
        archetype when reveals eliminate nothing yet (early game) or
        everything (a genuinely novel decklist -- true fringe)."""
        archetypes = self.archetypes()
        weights = {name: arch.get("meta_share", 0.0) for name, arch in archetypes.items() if self._core_consistent(arch)}
        if not weights:
            weights = {name: arch.get("meta_share", 0.0) for name, arch in archetypes.items()}
        total = sum(weights.values())
        if total <= 0:
            n = len(weights) or 1
            return dict.fromkeys(weights, 1.0 / n)
        return {name: w / total for name, w in weights.items()}

    def identified_list(self) -> dict[CardId, int] | None:
        """The single surviving exact 60-card list, or ``None`` if zero or
        more than one list is still consistent with the reveals."""
        survivors = self._surviving_lists()
        if len(survivors) != 1:
            return None
        _, lst = survivors[0]
        return {int(cid): n for cid, n in lst["cards"].items()}

    def best_archetype(self) -> tuple[str, float] | None:
        """The single archetype a level-2 read should trust, or ``None`` if
        reveals haven't genuinely narrowed anything yet (zero reveals) or
        have eliminated every archetype (full contradiction -- true fringe)
        -- both cases fall back to the flat meta-share prior in
        ``archetype_belief``, which isn't real evidence and shouldn't be
        read as concentration just because one archetype has a large meta
        share."""
        archetypes = self.archetypes()
        survivors = [name for name, arch in archetypes.items() if self._core_consistent(arch)]
        if not survivors or len(survivors) == len(archetypes):
            return None
        belief = self.archetype_belief()
        if not belief:
            return None
        name = max(belief, key=lambda candidate: belief[candidate])
        if belief[name] < _LEVEL2_CONCENTRATION:
            return None
        return name, belief[name]

    def level(self) -> int:
        if self.identified_list() is not None:
            return 1
        return 2 if self.best_archetype() is not None else 3

    def opp_remaining(self, card_id: CardId) -> tuple[int, int, float] | None:
        """(lo, hi, expected) copies of ``card_id`` still unseen in the
        opponent's deck+hand. Exact at level 1; a range from the best
        archetype's core/flex at level 2; ``None`` at level 3 (no signal)."""
        seen = self.reveals.get(card_id, 0)
        exact = self.identified_list()
        if exact is not None:
            remaining = max(exact.get(card_id, 0) - seen, 0)
            return (remaining, remaining, float(remaining))

        best = self.best_archetype()
        if best is None:
            return None
        arch = self.archetypes().get(best[0], {})
        key = str(card_id)
        core, flex = arch.get("core", {}), arch.get("flex", {})
        if key in core:
            total_lo = total_hi = core[key]
        elif key in flex:
            total_lo, total_hi = flex[key]["count_range"]
        else:
            total_lo = total_hi = 0
        lo, hi = max(total_lo - seen, 0), max(total_hi - seen, 0)
        return (lo, hi, (lo + hi) / 2)

    def p_in_hand(self, card_id: CardId) -> float | None:
        """Hypergeometric P(>=1 copy of ``card_id`` in the opponent's current
        hand), treating hand+deck as one unseen pool of known size with an
        expected count of the card among it. Levels 1-2 only."""
        remaining = self.opp_remaining(card_id)
        if remaining is None:
            return None
        _, _, expected = remaining
        pool = self._opp_hand_count + self._opp_deck_count
        hand = self._opp_hand_count
        if pool <= 0 or hand <= 0 or expected <= 0:
            return 0.0
        k = min(round(expected), pool)
        if k <= 0:
            return 0.0
        hand = min(hand, pool)
        # P(0 in hand) = C(pool-k, hand) / C(pool, hand); P(>=1) = 1 - that.
        if pool - k < hand:
            return 1.0  # more copies than could possibly miss the hand
        p_zero = math.comb(pool - k, hand) / math.comb(pool, hand)
        return 1.0 - p_zero
