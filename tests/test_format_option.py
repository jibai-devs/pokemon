"""format_option must label every option unambiguously — no bare OK / ?type."""

from pokemon.cabt_enums import SelectContext
from pokemon.catalog import format_option

# A minimal hand: index 0 = Gouging Fire ex (46), index 1 = Fire Energy (2).
HAND = [{"id": 46}, {"id": 2}]


def test_number_uses_context_not_bare_ok():
    # The headline fix: type-0 options read as their context, not "OK#n".
    opt = {"type": 0, "number": 2}
    assert format_option(opt, HAND, SelectContext.DRAW_COUNT) == "DRAW_COUNT=2"
    # Same option type, different context -> different, unambiguous label.
    assert format_option(opt, HAND, SelectContext.DAMAGE_COUNTER_COUNT) == "DAMAGE_COUNTER_COUNT=2"


def test_play_resolves_hand_card_name():
    # PLAY omits `area`; its index is implicitly into the hand.
    assert (
        format_option({"type": 7, "index": 0}, HAND, SelectContext.MAIN) == "PLAY Gouging Fire ex"
    )


def test_attach_shows_source_and_target():
    opt = {"type": 8, "area": 2, "index": 1, "inPlayArea": 4, "inPlayIndex": 0}
    assert format_option(opt, HAND, SelectContext.MAIN) == "ATTACH Fire Energy -> ACTIVE#0"


def test_yes_no_carry_context():
    assert format_option({"type": 1}, HAND, SelectContext.IS_FIRST) == "IS_FIRST=YES"
    assert format_option({"type": 2}, HAND, SelectContext.IS_FIRST) == "IS_FIRST=NO"


def test_card_setup_label():
    opt = {"type": 3, "area": 2, "index": 0, "playerIndex": 0}
    assert format_option(opt, HAND, SelectContext.SETUP_ACTIVE_POKEMON) == (
        "SETUP_ACTIVE_POKEMON Gouging Fire ex"
    )


def test_no_bare_ok_or_questiontype_for_unknown():
    # Even an unknown option type must never collapse to a bare "OK" or "?type".
    label = format_option({"type": 99}, HAND, SelectContext.MAIN)
    assert "OK" not in label
    assert "?type" not in label
    assert "99" in label
