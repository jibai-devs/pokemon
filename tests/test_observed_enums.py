"""Integration: every int the live engine emits maps to a known enum member.

This is the empirical backstop for the enum tables — if the vendored ``libcg.so``
ever emits a value the docs don't cover, this test fails with the offender.
``reverse-engineering/scripts/verify_enums.py`` is the wider, multi-deck version.
"""

import kaggle_environments as kaggle
from kaggle_environments.envs.cabt.cabt import random_agent

from pokemon.agent import fire_agent
from pokemon.cabt_enums import (
    AreaType,
    LogType,
    OptionType,
    SelectContext,
    SelectType,
    Unknown,
    safe,
)


def _unknowns(obs, found):
    sel = obs.get("select")
    if sel:
        for enum, val in ((SelectType, sel.get("type")), (SelectContext, sel.get("context"))):
            if isinstance(safe(enum, val), Unknown):
                found.append((enum.__name__, val))
        for opt in sel.get("option") or []:
            for key in ("type", "area", "inPlayArea"):
                enum = OptionType if key == "type" else AreaType
                if isinstance(safe(enum, opt.get(key)), Unknown):
                    found.append((enum.__name__, opt.get(key)))
    for log in obs.get("logs") or []:
        if isinstance(safe(LogType, log.get("type")), Unknown):
            found.append(("LogType", log.get("type")))


def test_no_unknown_enum_ints_in_a_real_game():
    env = kaggle.make("cabt", debug=True)
    env.reset()
    env.run([fire_agent, random_agent])

    found: list = []
    for step in env.steps:
        for state in step:
            _unknowns(state.get("observation", {}), found)

    assert not found, f"engine emitted ints with no enum member: {sorted(set(found))}"
