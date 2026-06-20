"""Engine enums for the CABT environment.

These are transcribed from the upstream ``cabt`` engine API docs (mirrored in
``docs/000_plan_engine_enum_extraction.md``) and verified empirically against
the live engine via ``reverse-engineering/scripts/verify_enums.py``.

The integer values are the ground truth: they are exactly what appears in the
JSON observations the engine serializes (``select.type``, ``select.context``,
``select.option[*].type``, ``option.area``, ``Log.type`` …). Everything is an
:class:`enum.IntEnum` so existing ``opt["type"] == 7`` style comparisons keep
working while we migrate to named members.

When the engine emits an int we don't have a member for (a build that diverges
from the docs), :func:`safe` returns a placeholder instead of raising, so a
single unknown value can't crash a whole game; the verifier flags it instead.
"""

from __future__ import annotations

from enum import IntEnum

__all__ = [
    "AreaType",
    "CardType",
    "EnergyType",
    "LogType",
    "OptionType",
    "SelectContext",
    "SelectType",
    "SpecialConditionType",
    "Unknown",
    "safe",
]


class SelectType(IntEnum):
    """``select.type`` — which family of OptionTypes the options belong to."""

    MAIN = 0
    CARD = 1
    ATTACHED_CARD = 2
    CARD_OR_ATTACHED_CARD = 3
    ENERGY = 4
    SKILL = 5
    ATTACK = 6
    EVOLVE = 7
    COUNT = 8
    YES_NO = 9
    SPECIAL_CONDITION = 10


class OptionType(IntEnum):
    """``select.option[*].type`` — the kind of a single choice.

    Fields carried alongside each value (in the option dict):

    - ``NUMBER``: ``number``
    - ``CARD``: ``area, index, playerIndex``
    - ``TOOL_CARD``: ``area, index, playerIndex, toolIndex``
    - ``ENERGY_CARD``: ``area, index, playerIndex, energyIndex``
    - ``ENERGY``: ``area, index, playerIndex, energyIndex, count``
    - ``PLAY``: ``index`` (hand)
    - ``ATTACH``: ``area, index, inPlayArea, inPlayIndex``
    - ``EVOLVE``: ``area, index, inPlayArea, inPlayIndex``
    - ``ABILITY``: ``area, index``
    - ``DISCARD``: ``area, index``
    - ``ATTACK``: ``attackId``
    - ``SKILL``: ``cardId, serial``
    - ``SPECIAL_CONDITION``: ``specialConditionType``
    """

    NUMBER = 0
    YES = 1
    NO = 2
    CARD = 3
    TOOL_CARD = 4
    ENERGY_CARD = 5
    ENERGY = 6
    PLAY = 7
    ATTACH = 8
    EVOLVE = 9
    ABILITY = 10
    DISCARD = 11
    RETREAT = 12
    ATTACK = 13
    END = 14
    SKILL = 15
    SPECIAL_CONDITION = 16


class SelectContext(IntEnum):
    """``select.context`` — disambiguates what a selection actually means.

    This is the field the old agent ignored: e.g. an ``OptionType.NUMBER`` option
    means ``DRAW_COUNT`` in one place and ``DAMAGE_COUNTER_COUNT`` in another.
    The ``SelectType`` each context belongs to is noted in the comments.
    """

    MAIN = 0  # MAIN
    SETUP_ACTIVE_POKEMON = 1  # CARD
    SETUP_BENCH_POKEMON = 2  # CARD
    SWITCH = 3  # CARD
    TO_ACTIVE = 4  # CARD
    TO_BENCH = 5  # CARD
    TO_FIELD = 6  # CARD
    TO_HAND = 7  # CARD
    DISCARD = 8  # CARD
    TO_DECK = 9  # CARD
    TO_DECK_BOTTOM = 10  # CARD
    TO_PRIZE = 11  # CARD
    NOT_MOVE = 12  # CARD
    DAMAGE_COUNTER = 13  # CARD
    DAMAGE_COUNTER_ANY = 14  # CARD
    DAMAGE = 15  # CARD
    REMOVE_DAMAGE_COUNTER = 16  # CARD
    HEAL = 17  # CARD
    EVOLVES_FROM = 18  # CARD
    EVOLVES_TO = 19  # CARD
    DEVOLVE = 20  # CARD
    ATTACH_FROM = 21  # CARD
    ATTACH_TO = 22  # CARD
    DETACH_FROM = 23  # CARD
    LOOK = 24  # CARD
    EFFECT_TARGET = 25  # CARD
    DISCARD_ENERGY_CARD = 26  # ATTACHED_CARD
    DISCARD_TOOL_CARD = 27  # ATTACHED_CARD
    SWITCH_ENERGY_CARD = 28  # ATTACHED_CARD
    DISCARD_CARD_OR_ATTACHED_CARD = 29  # CARD_OR_ATTACHED_CARD
    DISCARD_ENERGY = 30  # ENERGY
    TO_HAND_ENERGY = 31  # ENERGY
    TO_DECK_ENERGY = 32  # ENERGY
    SWITCH_ENERGY = 33  # ENERGY
    SKILL_ORDER = 34  # SKILL
    ATTACK = 35  # ATTACK
    DISABLE_ATTACK = 36  # ATTACK
    EVOLVE = 37  # EVOLVE
    DRAW_COUNT = 38  # COUNT
    DAMAGE_COUNTER_COUNT = 39  # COUNT
    REMOVE_DAMAGE_COUNTER_COUNT = 40  # COUNT
    IS_FIRST = 41  # YES_NO
    MULLIGAN = 42  # YES_NO
    ACTIVATE = 43  # YES_NO
    FIRST_EFFECT = 44  # YES_NO
    MORE_DEVOLVE = 45  # YES_NO
    COIN_HEAD = 46  # YES_NO
    AFFECT_SPECIAL_CONDITION = 47  # SPECIAL_CONDITION
    RECOVER_SPECIAL_CONDITION = 48  # SPECIAL_CONDITION


class AreaType(IntEnum):
    """``option.area``, ``option.inPlayArea``, ``Log.fromArea`` …"""

    DECK = 1
    HAND = 2
    DISCARD = 3
    ACTIVE = 4
    BENCH = 5
    PRIZE = 6
    STADIUM = 7
    ENERGY = 8
    TOOL = 9
    PRE_EVOLUTION = 10
    PLAYER = 11
    LOOKING = 12


class EnergyType(IntEnum):
    COLORLESS = 0
    GRASS = 1
    FIRE = 2
    WATER = 3
    LIGHTNING = 4
    PSYCHIC = 5
    FIGHTING = 6
    DARKNESS = 7
    METAL = 8
    DRAGON = 9
    RAINBOW = 10
    TEAM_ROCKET = 11


class CardType(IntEnum):
    POKEMON = 0
    ITEM = 1
    TOOL = 2
    SUPPORTER = 3
    STADIUM = 4
    BASIC_ENERGY = 5
    SPECIAL_ENERGY = 6


class SpecialConditionType(IntEnum):
    POISON = 0
    BURN = 1
    SLEEP = 2
    PARALYZE = 3
    CONFUSE = 4


class LogType(IntEnum):
    """``Log.type`` — events since the previous selection (``obs.logs``).

    ``RESULT`` carries ``result`` (0=p0 win, 1=p1 win, 2=draw) and ``reason``
    (1=no prizes, 2=no deck, 3=no active, 4=card effect).
    """

    SHUFFLE = 0
    HAS_BASIC_POKEMON = 1
    TURN_START = 2
    TURN_END = 3
    DRAW = 4
    DRAW_REVERSE = 5
    MOVE_CARD = 6
    MOVE_CARD_REVERSE = 7
    SWITCH = 8
    CHANGE = 9
    PLAY = 10
    ATTACH = 11
    EVOLVE = 12
    DEVOLVE = 13
    MOVE_ATTACHED = 14
    ATTACK = 15
    HP_CHANGE = 16
    POISONED = 17
    BURNED = 18
    ASLEEP = 19
    PARALYZED = 20
    CONFUSED = 21
    COIN = 22
    RESULT = 23


class Unknown:
    """Placeholder returned by :func:`safe` for an int with no enum member.

    Behaves enough like an enum member for logging: ``.name`` reads e.g.
    ``OptionType.UNKNOWN(99)`` and ``int(x)`` recovers the raw value.
    """

    __slots__ = ("enum", "value")

    def __init__(self, enum: type[IntEnum], value: int) -> None:
        self.enum = enum
        self.value = value

    @property
    def name(self) -> str:
        return f"{self.enum.__name__}.UNKNOWN({self.value})"

    def __int__(self) -> int:
        return self.value

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Unknown):
            return self.enum is other.enum and self.value == other.value
        if isinstance(other, int):
            return self.value == other
        return NotImplemented

    def __hash__(self) -> int:
        return hash((self.enum, self.value))

    def __repr__(self) -> str:
        return self.name


def safe[E: IntEnum](cls: type[E], value: int | None) -> E | Unknown | None:
    """Return the member of ``cls`` for ``value``, or a forward-compatible stub.

    ``None`` passes through (the engine sends ``null`` for absent selections).
    Unknown ints yield an :class:`Unknown` so callers can ``.name`` them in logs
    without crashing; the verifier treats those as findings.
    """
    if value is None:
        return None
    try:
        return cls(value)
    except ValueError:
        return Unknown(cls, value)
