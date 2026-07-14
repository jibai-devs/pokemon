"""Structural types for CABT observations and agent actions.

The engine sends JSON-compatible dictionaries, and fields vary with the
current selection and card location.  These types describe the stable shared
shape without pretending every optional engine field is always present.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Required, TypeAlias, TypedDict

if TYPE_CHECKING:
    from pokemon.heuristics import Ctx

CardId: TypeAlias = int  # noqa: UP040 - Kaggle runs Python 3.11.
AttackId: TypeAlias = int  # noqa: UP040
PlayerIndex: TypeAlias = int  # noqa: UP040
OptionIndex: TypeAlias = int  # noqa: UP040
# Indices into the current ``select["option"]`` list — the legal choices the
# engine offered for this decision. Not card IDs.
Action: TypeAlias = list[OptionIndex]  # noqa: UP040
Deck: TypeAlias = list[CardId]  # noqa: UP040


class CardState(TypedDict, total=False):
    """A card in a live observation, not a static catalog record."""

    id: Required[CardId]
    name: str
    serial: int
    playerIndex: PlayerIndex
    hp: int
    maxHp: int
    appearThisTurn: bool
    energies: list[int]
    energyCards: list[CardState]
    tools: list[CardState]
    preEvolution: list[CardState]


class PlayerState(TypedDict, total=False):
    active: list[CardState | None]
    bench: list[CardState]
    benchMax: int
    deckCount: int
    discard: list[CardState]
    prize: list[CardState | None]
    handCount: int
    hand: list[CardState] | None
    poisoned: bool
    burned: bool
    asleep: bool
    paralyzed: bool
    confused: bool


class Option(TypedDict, total=False):
    """One legal choice; relevant fields depend on ``type``."""

    type: Required[int]
    number: int
    area: int
    index: int
    playerIndex: PlayerIndex
    inPlayArea: int
    inPlayIndex: int
    energyIndex: int
    toolIndex: int
    count: int
    attackId: AttackId
    cardId: CardId
    serial: int
    specialConditionType: int


class EffectRef(TypedDict, total=False):
    id: CardId
    playerIndex: PlayerIndex


class SelectData(TypedDict, total=False):
    type: int
    context: int
    minCount: int
    maxCount: Required[int]
    remainDamageCounter: int
    remainEnergyCost: int
    option: Required[list[Option]]
    deck: list[CardState] | None
    contextCard: CardState | None
    effect: EffectRef | None


class CurrentState(TypedDict, total=False):
    turn: int
    turnActionCount: int
    yourIndex: PlayerIndex
    firstPlayer: PlayerIndex
    supporterPlayed: bool
    stadiumPlayed: bool
    energyAttached: bool
    retreated: bool
    result: int
    stadium: list[CardState]
    looking: object | None
    players: list[PlayerState]


class Observation(TypedDict, total=False):
    remainingOverageTime: float
    step: int
    select: Required[SelectData | None]
    logs: list[object]
    current: CurrentState
    search_begin_input: str


class GameplayObservation(TypedDict):
    current: CurrentState


class SearchStartConfig(TypedDict):
    manualCoin: bool
    myDeck: list[CardId]
    myPrize: list[CardId]
    enemyDeck: list[CardId]
    enemyPrize: list[CardId]
    enemyHand: list[CardId]
    enemyActive: list[CardId]


Agent: TypeAlias = Callable[[Observation], Action]  # noqa: UP040
HeuristicState: TypeAlias = dict[str, object]  # noqa: UP040

# A single decision rule for the modular agent (see ``make_heuristic_agent``).
# Given a decision context, return an ``Action`` (indices into ``ctx.options``)
# to play, or ``None``/empty to defer to the next rule / random fallback.
# First non-empty return that satisfies ``minCount``/``maxCount`` wins.
# ``Ctx`` is quoted to avoid a runtime import cycle with ``pokemon.heuristics``.
DecisionRule: TypeAlias = Callable[["Ctx"], Action | None]  # noqa: UP040
