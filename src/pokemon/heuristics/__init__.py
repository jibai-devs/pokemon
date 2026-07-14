"""Registry of pluggable heuristic sets ("rulesets"), one per deck --
i.e. the set of available "decisionmakers" ``admin.py`` can choose between.

Add a new deck's heuristics by creating a sibling module here -- see
``dragapult.py`` for the pattern: a priority-ordered rule list plus a
persistent-state module (``dragapult_state.py``: a small dataclass + an
``init_state()`` factory) -- then register one ``Ruleset`` entry in
``RULESETS`` below. ``admin.py`` is the only consumer of this registry and
doesn't need to change when a new deck is added here.

A ruleset doesn't have to be purely hand-written rules, either --
``"dragapult_search"`` below is the same ``DragapultState``/hand-written
rules with an engine-backed search rule (``pokemon.search_function``)
given first refusal every decision.
"""

from collections.abc import Callable
from dataclasses import dataclass

from pokemon.board import Heuristic
from pokemon.heuristics.dragapult import DRAGAPULT_HEURISTICS
from pokemon.heuristics.dragapult_state import init_state as _dragapult_init_state
from pokemon.heuristics.opening_score import opening_turn_score
from pokemon.heuristics.smart_score import dragapult_smart_score
from pokemon.search_function import make_turn_bfs_search, turn_bfs_search


@dataclass
class Ruleset:
    """One registered heuristic set: its priority-ordered rule list
    (first-match-wins, per ``admin.build_agent``'s dispatch loop) plus the
    factory for its own typed persistent-state object."""

    rules: list[Heuristic]
    init_state: Callable[[], object]


RULESETS: dict[str, Ruleset] = {
    # Hand-written heuristics only -- see admin.build_agent's docstring for
    # how to invoke this one by name.
    "dragapult": Ruleset(rules=DRAGAPULT_HEURISTICS, init_state=_dragapult_init_state),
    # Same rules and state shape as "dragapult", but ``turn_bfs_search`` gets
    # first refusal every decision -- it returns None (deferring to the rest
    # of DRAGAPULT_HEURISTICS, unchanged) whenever it's not Main phase, the
    # engine/search_begin_input isn't available, or overage time is tight.
    # admin.select_ruleset's runtime switch doesn't select this one anymore
    # (it prefers "dragapult_opening" turn 1, "dragapult_smarter_search"
    # after) -- still directly reachable via
    # build_agent(deck, "dragapult_search") for comparison against the
    # smarter-scored one.
    "dragapult_search": Ruleset(
        rules=[turn_bfs_search, *DRAGAPULT_HEURISTICS],
        init_state=_dragapult_init_state,
    ),
    # Turn-1-only ruleset (whichever side we're on): search scored by
    # opening_turn_score (pokemon.heuristics.opening_score) instead of the
    # default score_line -- built from deck/guidelines_for_first turn.txt's
    # stated priorities (Dreepy count, a good turn 2, Budew-Itchy-Pollen when
    # going second, ...). Same DRAGAPULT_HEURISTICS fallback as
    # "dragapult_search". See admin.select_ruleset for the turn-1 detection
    # that actually switches to this ruleset.
    "dragapult_opening": Ruleset(
        rules=[make_turn_bfs_search(score_fn=opening_turn_score), *DRAGAPULT_HEURISTICS],
        init_state=_dragapult_init_state,
    ),
    # General-purpose (not turn-1-specific) search ruleset, scored by
    # dragapult_smart_score (pokemon.heuristics.smart_score) instead of the
    # default score_line -- built from deck/guidelines_for_phantom_dive.txt's
    # attack-or-hold-back decision tree plus dragapult_deck_explanation.md's
    # prize-mapping/overextension/discard-sequencing guidance. Same
    # DRAGAPULT_HEURISTICS fallback and DragapultState shape as the other
    # search rulesets. This is what admin.select_ruleset's runtime switch
    # actually prefers from turn 2 onward (turn 1 prefers "dragapult_opening"
    # instead).
    "dragapult_smarter_search": Ruleset(
        rules=[make_turn_bfs_search(score_fn=dragapult_smart_score), *DRAGAPULT_HEURISTICS],
        init_state=_dragapult_init_state,
    ),
}
