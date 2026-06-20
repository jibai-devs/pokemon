"""Phase 2 — empirically verify the CABT enum tables against the live engine.

Drives many games with varied agents and asserts that every integer the engine
emits for ``select.type``, ``select.context``, ``select.option[*].type``,
``option.area`` / ``inPlayArea``, and ``Log.type`` is a known member of the
corresponding :mod:`pokemon.cabt_enums` enum. Anything unknown is the signal the
vendored ``libcg.so`` diverges from the docs (escalate to Phase 3 for that value).

Also prints a coverage report: which enum members were actually observed, so we
know which contexts (devolve, special conditions, prize picks, …) still need
decks that trigger them before we can claim full coverage.

Usage::

    uv run python reverse-engineering/scripts/verify_enums.py [games]

Exit code is non-zero if any unknown integer was seen (suitable as a CI gate).
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict

import kaggle_environments as kaggle
from kaggle_environments.envs.cabt.cabt import first_agent, random_agent

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

# (enum, observed-values set). Populated as we walk every observation.
_TRACKED = {
    "SelectType": SelectType,
    "SelectContext": SelectContext,
    "OptionType": OptionType,
    "AreaType": AreaType,
    "LogType": LogType,
}


def _record(seen: dict[str, set[int]], unknowns: list, enum_name: str, value, sample) -> None:
    """Note one observed int; stash a sample observation for unknowns."""
    if value is None:
        return
    seen[enum_name].add(value)
    if isinstance(safe(_TRACKED[enum_name], value), Unknown):
        unknowns.append((enum_name, value, sample))


def _walk(obs: dict, seen: dict[str, set[int]], unknowns: list) -> None:
    select = obs.get("select")
    if select:
        _record(seen, unknowns, "SelectType", select.get("type"), select)
        _record(seen, unknowns, "SelectContext", select.get("context"), select)
        for opt in select.get("option") or []:
            _record(seen, unknowns, "OptionType", opt.get("type"), opt)
            _record(seen, unknowns, "AreaType", opt.get("area"), opt)
            _record(seen, unknowns, "AreaType", opt.get("inPlayArea"), opt)
    for log in obs.get("logs") or []:
        _record(seen, unknowns, "LogType", log.get("type"), log)
        _record(seen, unknowns, "AreaType", log.get("fromArea"), log)
        _record(seen, unknowns, "AreaType", log.get("toArea"), log)


def run(games: int) -> int:
    seen: dict[str, set[int]] = defaultdict(set)
    unknowns: list = []

    # Mix agents so we exercise more game states than a single matchup would:
    # our scored agent (real decisions) plus random/first (chaotic, surfaces
    # damage counters, retreats, odd sequences).
    pairings: list[list] = [
        [fire_agent, random_agent],
        [random_agent, fire_agent],
        [random_agent, random_agent],
        [random_agent, first_agent],
    ]

    for g in range(games):
        env = kaggle.make("cabt", debug=True)
        env.reset()
        env.run(pairings[g % len(pairings)])
        for step in env.steps:
            for p in range(len(step)):
                _walk(step[p].get("observation", {}), seen, unknowns)

    print("=" * 64)
    print(f"CABT enum verification — {games} games")
    print("=" * 64)

    for name, enum in _TRACKED.items():
        members = {m.value: m.name for m in enum}
        observed = seen[name]
        known = sorted(v for v in observed if v in members)
        missing = sorted(v for v in members if v not in observed)
        print(f"\n{name}: {len(known)}/{len(members)} members observed")
        print("  seen:    " + ", ".join(f"{members[v]}({v})" for v in known) or "  seen: -")
        if missing:
            print("  missing: " + ", ".join(f"{members[v]}({v})" for v in missing))

    print("\n" + "=" * 64)
    if unknowns:
        print(f"FAIL — {len(unknowns)} observation(s) with UNKNOWN enum ints:")
        # De-dup by (enum, value); show one sample each.
        shown: set[tuple[str, int]] = set()
        for enum_name, value, sample in unknowns:
            key = (enum_name, value)
            if key in shown:
                continue
            shown.add(key)
            print(f"  {enum_name}={value}  sample={json.dumps(sample)[:200]}")
        return 1

    print("PASS — every observed select.type / context / option.type / area / log")
    print("       int maps to a known enum member. (Coverage gaps listed above")
    print("       are unobserved members, not unknown ints — need decks to trigger.)")
    return 0


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    raise SystemExit(run(n))
