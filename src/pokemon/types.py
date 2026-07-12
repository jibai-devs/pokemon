"""Structural types for CABT observations and agent actions.

The engine sends JSON-compatible dictionaries, and fields vary with the
current selection and card location.  These types describe the stable shared
shape without pretending every optional engine field is always present.
"""

from collections.abc import Callable
from typing import Required, TypedDict

type CardId = int
type AttackId = int
type PlayerIndex = int
type OptionIndex = int
type Action = list[OptionIndex]
type Deck = list[CardId]


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


type Agent = Callable[[Observation], Action]
type HeuristicState = dict[str, object]
