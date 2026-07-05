"""Unit tests for the Psychic deck heuristics, using synthetic ``obs`` dicts.

These test each heuristic in isolation against hand-built observations,
without needing the real engine (WSL/libcg.so) — see PKM-017.
"""

from pokemon.heuristics import (
    _build_ctx,
    attach_energy_to_attacker,
    evolve_into_slowking,
    play_setup_pieces,
    prefer_copy_fodder_targets,
    prefer_engine_targets_to_hand,
    prefer_seek_inspiration,
    retreat_when_slowking_endangered,
    setup_active_prefers_slowking_line,
    switch_to_backup_attacker,
)


def _obs(select: dict, hand: list | None = None, active: list | None = None, bench: list | None = None):
    return {
        "select": select,
        "current": {
            "yourIndex": 0,
            "players": [
                {"hand": hand or [], "active": active or [], "bench": bench or []},
                {"hand": None, "active": [], "bench": []},
            ],
        },
    }


def test_prefer_seek_inspiration_picks_seek_inspiration_over_other_attacks():
    select = {
        "type": 0,
        "context": 0,
        "maxCount": 1,
        "option": [
            {"type": 13, "attackId": 214},  # Super Psy Bolt
            {"type": 13, "attackId": 213},  # Seek Inspiration
        ],
    }
    ctx = _build_ctx(_obs(select))
    assert prefer_seek_inspiration(ctx) == [1]


def test_prefer_seek_inspiration_none_when_absent():
    select = {"type": 0, "context": 0, "maxCount": 1, "option": [{"type": 13, "attackId": 214}]}
    ctx = _build_ctx(_obs(select))
    assert prefer_seek_inspiration(ctx) is None


def test_evolve_into_slowking_from_hand():
    hand = [{"id": 1121}, {"id": 163}]  # Ultra Ball, Slowking
    select = {
        "type": 0,
        "context": 0,
        "maxCount": 1,
        "option": [
            {"type": 9, "area": 2, "index": 0, "inPlayArea": 5, "inPlayIndex": 0},
            {"type": 9, "area": 2, "index": 1, "inPlayArea": 4, "inPlayIndex": 0},
        ],
    }
    ctx = _build_ctx(_obs(select, hand=hand))
    assert evolve_into_slowking(ctx) == [1]


def test_attach_energy_to_attacker_prefers_undercharged_slowking_over_bench():
    active = [{"id": 163, "energies": []}]  # Slowking, no energy yet
    bench = [{"id": 756, "energies": [0, 0]}]  # Mega Kangaskhan ex, already charged
    select = {
        "type": 0,
        "context": 0,
        "maxCount": 1,
        "option": [
            {"type": 8, "inPlayArea": 5, "inPlayIndex": 0},  # attach to bench Mega Kangaskhan
            {"type": 8, "inPlayArea": 4, "inPlayIndex": 0},  # attach to active Slowking
        ],
    }
    ctx = _build_ctx(_obs(select, active=active, bench=bench))
    assert attach_energy_to_attacker(ctx) == [1]


def test_attach_energy_to_attacker_feeds_active_pokemon_when_slowking_charged_and_benched():
    """Regression test for the real-game bug found via PKM-019's
    ``recent_log.txt`` audit: a benched, already-loaded Slowking kept
    absorbing energy meant for whichever Pokemon was actually active,
    stranding it below its own attack cost. Once Slowking is at its
    threshold, further attaches should go to the active Pokemon instead."""
    active = [{"id": 756, "energies": [0]}]  # Mega Kangaskhan ex, 1/3 energy, active
    bench = [{"id": 163, "energies": [5, 0]}]  # Slowking, already at its 2-energy cap, benched
    select = {
        "type": 0,
        "context": 0,
        "maxCount": 1,
        "option": [
            {"type": 8, "inPlayArea": 5, "inPlayIndex": 0},  # attach to bench Slowking
            {"type": 8, "inPlayArea": 4, "inPlayIndex": 0},  # attach to active Mega Kangaskhan ex
        ],
    }
    ctx = _build_ctx(_obs(select, active=active, bench=bench))
    assert attach_energy_to_attacker(ctx) == [1]


def test_attach_energy_none_when_slowking_and_active_both_charged():
    active = [{"id": 163, "energies": [5, 0]}]
    select = {
        "type": 0,
        "context": 0,
        "maxCount": 1,
        "option": [{"type": 8, "inPlayArea": 4, "inPlayIndex": 0}],
    }
    ctx = _build_ctx(_obs(select, active=active))
    assert attach_energy_to_attacker(ctx) == [0]


def test_play_setup_pieces_prefers_codebreaking_over_other_plays():
    hand = [{"id": 1121}, {"id": 1188}]  # Ultra Ball, Ciphermaniac's Codebreaking
    select = {
        "type": 0,
        "context": 0,
        "maxCount": 1,
        "option": [
            {"type": 7, "index": 0},
            {"type": 7, "index": 1},
        ],
    }
    ctx = _build_ctx(_obs(select, hand=hand))
    assert play_setup_pieces(ctx) == [1]


def test_setup_active_prefers_slowking_line():
    # Setting the opening active Pokemon chooses among your own hand.
    hand = [{"id": 756}, {"id": 162}]  # Mega Kangaskhan ex, Slowpoke
    select = {
        "type": 1,
        "context": 1,  # SETUP_ACTIVE_POKEMON
        "maxCount": 1,
        "option": [
            {"type": 3, "area": 2, "index": 0},
            {"type": 3, "area": 2, "index": 1},
        ],
    }
    ctx = _build_ctx(_obs(select, hand=hand))
    assert setup_active_prefers_slowking_line(ctx) == [1]


def test_switch_to_backup_attacker_prefers_mega_kangaskhan_when_slowking_not_ready():
    # Switching active chooses among the bench. Slowpoke isn't Slowking, so
    # there's no charged-Slowking option to prefer.
    bench = [{"id": 162}, {"id": 756}]  # Slowpoke, Mega Kangaskhan ex
    select = {
        "type": 1,
        "context": 3,  # SWITCH
        "maxCount": 1,
        "option": [
            {"type": 3, "area": 5, "index": 0},
            {"type": 3, "area": 5, "index": 1},
        ],
    }
    ctx = _build_ctx(_obs(select, bench=bench))
    assert switch_to_backup_attacker(ctx) == [1]


def test_switch_to_backup_attacker_prefers_charged_slowking_over_backup():
    """Regression test for the real-game bug found via PKM-019's
    ``recent_log.txt`` audit: Slowking accumulated enough energy to attack
    but was never switched back into active because this heuristic
    unconditionally preferred the backup attackers on every switch."""
    bench = [
        {"id": 756, "energies": [0, 0, 0]},  # Mega Kangaskhan ex, charged
        {"id": 163, "energies": [5, 0]},  # Slowking, at its 2-energy attack cost
    ]
    select = {
        "type": 1,
        "context": 3,  # SWITCH
        "maxCount": 1,
        "option": [
            {"type": 3, "area": 5, "index": 0},
            {"type": 3, "area": 5, "index": 1},
        ],
    }
    ctx = _build_ctx(_obs(select, bench=bench))
    assert switch_to_backup_attacker(ctx) == [1]


def test_switch_to_backup_attacker_ignores_undercharged_slowking():
    bench = [
        {"id": 163, "energies": []},  # Slowking, not ready
        {"id": 756, "energies": [0, 0]},  # Mega Kangaskhan ex
    ]
    select = {
        "type": 1,
        "context": 3,  # SWITCH
        "maxCount": 1,
        "option": [
            {"type": 3, "area": 5, "index": 0},
            {"type": 3, "area": 5, "index": 1},
        ],
    }
    ctx = _build_ctx(_obs(select, bench=bench))
    assert switch_to_backup_attacker(ctx) == [1]


def test_retreat_when_slowking_low_hp():
    active = [{"id": 163, "hp": 20, "maxHp": 120}]
    select = {
        "type": 0,
        "context": 0,
        "maxCount": 1,
        "option": [{"type": 14}, {"type": 12}],  # END, RETREAT
    }
    ctx = _build_ctx(_obs(select, active=active))
    assert retreat_when_slowking_endangered(ctx) == [1]


def test_retreat_none_when_slowking_healthy():
    active = [{"id": 163, "hp": 100, "maxHp": 120}]
    select = {"type": 0, "context": 0, "maxCount": 1, "option": [{"type": 12}]}
    ctx = _build_ctx(_obs(select, active=active))
    assert retreat_when_slowking_endangered(ctx) is None


def test_prefer_copy_fodder_targets_ranks_metagross_first():
    # A search-reveal option references select.deck by its own `index`, not
    # by its position in the option list.
    select = {
        "type": 1,
        "context": 9,  # TO_DECK — stacking fodder on top ahead of Seek Inspiration
        "maxCount": 1,
        "option": [
            {"type": 3, "area": 1, "index": 0},
            {"type": 3, "area": 1, "index": 1},
        ],
        "deck": [{"id": 956}, {"id": 276}],  # Zeraora, Metagross
    }
    ctx = _build_ctx(_obs(select))
    assert prefer_copy_fodder_targets(ctx) == [1]


def test_prefer_copy_fodder_targets_does_not_fire_during_bench_setup():
    """Regression test: an earlier version of this heuristic fired on any
    CARD-type select, including SETUP_BENCH_POKEMON — which benched Kyurem
    instead of leaving it in the deck as Seek Inspiration fodder, its whole
    point. It must only fire for TO_DECK."""
    select = {
        "type": 1,
        "context": 2,  # SETUP_BENCH_POKEMON
        "maxCount": 1,
        "option": [
            {"type": 3, "area": 1, "index": 0},
            {"type": 3, "area": 1, "index": 1},
        ],
        "deck": [{"id": 956}, {"id": 276}],
    }
    ctx = _build_ctx(_obs(select))
    assert prefer_copy_fodder_targets(ctx) is None


def test_prefer_copy_fodder_targets_does_not_fire_for_to_hand():
    """Regression test for the actual Seek Inspiration bug: pulling Metagross/
    Kyurem into HAND (Ultra Ball, Poke Pad) removes them from the deck, so
    Seek Inspiration can never discard-and-copy them again. Fodder targeting
    must be restricted to TO_DECK; TO_HAND search should go to
    prefer_engine_targets_to_hand instead."""
    select = {
        "type": 1,
        "context": 7,  # TO_HAND
        "maxCount": 1,
        "option": [
            {"type": 3, "area": 1, "index": 0},
            {"type": 3, "area": 1, "index": 1},
        ],
        "deck": [{"id": 956}, {"id": 276}],  # Zeraora, Metagross
    }
    ctx = _build_ctx(_obs(select))
    assert prefer_copy_fodder_targets(ctx) is None


def test_prefer_engine_targets_to_hand_ranks_slowking_first():
    select = {
        "type": 1,
        "context": 7,  # TO_HAND
        "maxCount": 1,
        "option": [
            {"type": 3, "area": 1, "index": 0},
            {"type": 3, "area": 1, "index": 1},
        ],
        "deck": [{"id": 162}, {"id": 163}],  # Slowpoke, Slowking
    }
    ctx = _build_ctx(_obs(select))
    assert prefer_engine_targets_to_hand(ctx) == [1]


def test_prefer_engine_targets_to_hand_ignores_fodder():
    """Metagross/Kyurem/Zeraora must never be picked for TO_HAND — their
    value is being left in the deck for Seek Inspiration to discard."""
    select = {
        "type": 1,
        "context": 7,  # TO_HAND
        "maxCount": 1,
        "option": [{"type": 3, "area": 1, "index": 0}],
        "deck": [{"id": 276}],  # Metagross
    }
    ctx = _build_ctx(_obs(select))
    assert prefer_engine_targets_to_hand(ctx) is None


def test_option_card_id_prefers_hand_resolution_over_stale_deck_list():
    """Regression test: a real playtest showed a legitimate "play Latias ex
    from hand" option (area=HAND) getting overridden by an unrelated
    select.deck entry, because the old code checked select.deck first keyed
    by list position. Hand-area options must resolve via their own
    area/index and ignore select.deck entirely."""
    from pokemon.heuristics import _option_card_id

    hand = [{"id": 184}]  # Latias ex
    select = {
        "type": 1,
        "context": 7,
        "maxCount": 1,
        "option": [{"type": 3, "area": 2, "index": 0}],
        "deck": [{"id": 276}],  # unrelated Metagross entry at the same position
    }
    ctx = _build_ctx(_obs(select, hand=hand))
    assert _option_card_id(ctx, ctx.options[0]) == 184


def test_option_card_id_ignores_non_card_shaped_options():
    """Regression test: a PLAY option (type 7) was previously misread as a
    CARD option via a stale `select.deck`, producing an out-of-range/illegal
    move that ended a real game early."""
    from pokemon.heuristics import _option_card_id

    select = {
        "type": 1,
        "context": 7,
        "maxCount": 1,
        "option": [{"type": 7, "index": 24}],
        "deck": [{"id": 276}],
    }
    ctx = _build_ctx(_obs(select))
    assert _option_card_id(ctx, ctx.options[0]) is None
