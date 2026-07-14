"""Persistent, per-game memory for the ``dragapult`` ruleset.

Every field here is written and read by ``dragapult.py`` /
``dragapult_matchups.py`` across many separate decisions within one game --
see ``admin.py`` for the lifecycle (created once per game via
``init_state()``, replaced whenever a new deck-submission phase starts).
Kept in its own module, rather than inline in either ruleset file, so the
persistent-memory shape is declared in exactly one place regardless of which
of the two files ends up reading or writing a given field.
"""

from dataclasses import dataclass, field

from pokemon.deck_id import DeckIdentifier
from pokemon.decks import DRAGAPULT_DECK


@dataclass
class DeckMemoryEntry:
    """One physical copy of a card in our own 60-card deck. Fungible within
    a card id -- ``prize_check`` marks however many entries of a given id
    are unaccounted for, not a specific physical copy (there's no way to
    distinguish two copies of the same card anyway)."""

    id: int
    prized: bool = False


def _build_deck_memory() -> list[DeckMemoryEntry]:
    return [DeckMemoryEntry(id=cid) for cid in DRAGAPULT_DECK]


@dataclass
class DragapultState:
    """``archetype``: the opponent's matchup bucket once a signature
    Pokemon/Stadium has been physically seen (``archetype_latch``) -- a
    one-shot latch, never cleared once set.

    ``deck_id``: the running Bayesian belief over the opponent's decklist
    (``deck_belief_update``), mutated in place every decision.

    ``matchup_bucket_cache``: memoizes ``_matchup_bucket``'s classification
    of a believed archetype's card list, keyed by archetype name, so it's
    computed once rather than every decision.

    ``recon_used``: turn+serial keys marking a Drakloak's recon use --
    declared here for ``_own_board_tier``, but nothing currently writes to
    it (carried over as-is from the prior untyped-dict version; see
    AGENTS.md's Known issues before relying on this gating a real decision).

    ``deck_memory``: one entry per physical copy of our own decklist,
    initialized from ``DRAGAPULT_DECK`` at the start of every game, with
    ``prized`` flipped on by ``prize_check`` once it deduces that copy must
    be in one of our 6 prizes.

    ``prize_check_done``: guards ``prize_check`` to run its deduction only
    once per game (the first deck-search reveal), not every one.

    ``last_prize_count``/``last_hand_counts``: the previous decision's
    ``prizes_remaining`` count and hand-card-id multiset, both maintained by
    ``track_prize_takes`` so it can notice a prize being taken (the count
    drops) and figure out which newly-visible hand card is the one that was
    just taken.

    ``decision_count``: how many decisions ``play()`` has handled so far
    this game -- i.e. how many times the agent has submitted an action to
    Kaggle. Incremented by ``print_prize_check`` for its own log line, and
    tagged onto every one of them (it prints every decision, not once per
    turn).
    """

    archetype: str | None = None
    deck_id: DeckIdentifier | None = None
    matchup_bucket_cache: dict[str, str | None] = field(default_factory=dict)
    recon_used: set[str] = field(default_factory=set)
    deck_memory: list[DeckMemoryEntry] = field(default_factory=_build_deck_memory)
    prize_check_done: bool = False
    last_prize_count: int | None = None
    last_hand_counts: dict[int, int] = field(default_factory=dict)
    decision_count: int = 0


def init_state() -> DragapultState:
    return DragapultState()
