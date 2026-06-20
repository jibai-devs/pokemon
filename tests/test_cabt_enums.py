"""Lock the CABT enum contract: integer values are the engine's ground truth."""

from pokemon.cabt_enums import (
    AreaType,
    OptionType,
    SelectContext,
    SelectType,
    Unknown,
    safe,
)


def test_optiontype_action_values_match_engine():
    # The values the old reverse-engineered map got wrong (7=PLAY, 8=ATTACH …).
    assert OptionType.NUMBER == 0
    assert OptionType.CARD == 3
    assert OptionType.PLAY == 7
    assert OptionType.ATTACH == 8
    assert OptionType.EVOLVE == 9
    assert OptionType.ABILITY == 10
    assert OptionType.RETREAT == 12
    assert OptionType.ATTACK == 13
    assert OptionType.END == 14


def test_select_type_and_context_values():
    assert SelectType.COUNT == 8
    assert SelectType.YES_NO == 9
    assert SelectContext.DRAW_COUNT == 38
    assert SelectContext.IS_FIRST == 41
    # The disambiguation the old agent ignored: same NUMBER, different meaning.
    assert SelectContext.DAMAGE_COUNTER_COUNT == 39


def test_area_type_values():
    assert AreaType.HAND == 2
    assert AreaType.ACTIVE == 4
    assert AreaType.BENCH == 5


def test_intenum_compares_as_int():
    # IntEnum keeps existing `opt["type"] == 7` style comparisons working.
    assert OptionType.PLAY == 7
    assert 7 == OptionType.PLAY


def test_safe_known_unknown_and_none():
    assert safe(OptionType, 7) is OptionType.PLAY
    assert safe(SelectContext, None) is None

    unknown = safe(OptionType, 999)
    assert isinstance(unknown, Unknown)
    assert int(unknown) == 999
    assert unknown == 999
    assert "UNKNOWN(999)" in unknown.name
