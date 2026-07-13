"""Registry of pluggable heuristic sets ("rulesets"), one per deck.

Add a new deck's heuristics by creating a sibling module here -- see
``dragapult.py`` for the pattern: a priority-ordered rule list plus a
persistent-state module (``dragapult_state.py``: a small dataclass + an
``init_state()`` factory) -- then register one ``Ruleset`` entry in
``RULESETS`` below. ``admin.py`` is the only consumer of this registry and
doesn't need to change when a new deck is added here.
"""

from collections.abc import Callable
from dataclasses import dataclass

from pokemon.board import Heuristic
from pokemon.heuristics.dragapult import DRAGAPULT_HEURISTICS
from pokemon.heuristics.dragapult_state import init_state as _dragapult_init_state


@dataclass
class Ruleset:
    """One registered heuristic set: its priority-ordered rule list
    (first-match-wins, per ``admin.build_agent``'s dispatch loop) plus the
    factory for its own typed persistent-state object."""

    rules: list[Heuristic]
    init_state: Callable[[], object]


RULESETS: dict[str, Ruleset] = {
    "dragapult": Ruleset(rules=DRAGAPULT_HEURISTICS, init_state=_dragapult_init_state),
}
