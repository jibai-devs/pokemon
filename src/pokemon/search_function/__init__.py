"""Engine-backed, decision-time search: an alternative decisionmaker to the
hand-written heuristic sets under ``pokemon.heuristics``.

``turn_search.py`` owns the whole stack: forking the live game state via the
native engine (``pokemon.native_search``), enumerating legal action
sequences to the end of the current turn, and scoring the resulting leaves.

``search(ctx, score_fn)`` is the generic entry point -- give it a decision
and a scorer, get back the chosen action (``list[int] | None``), same shape
any hand-written ``Heuristic`` returns. Call it directly from any
decisionmaking engine's own logic to make use of the search algorithm,
without needing to register anything in ``pokemon.heuristics.RULESETS``.

``turn_bfs_search`` -- a ``Heuristic``-shaped (single-``ctx``-argument)
wrapper around ``search`` with the built-in ``score_line`` objective -- is
what's registered as part of ``pokemon.heuristics.RULESETS["dragapult_search"]``.
Build your own via ``make_turn_bfs_search(score_fn=...)`` for a custom
objective plugged into a ``Ruleset``'s rule list instead of called inline.
"""

from pokemon.search_function.turn_search import (
    ScoreFn,
    TurnLine,
    make_turn_bfs_search,
    score_line,
    search,
    turn_bfs_search,
)

__all__ = [
    "ScoreFn",
    "TurnLine",
    "make_turn_bfs_search",
    "score_line",
    "search",
    "turn_bfs_search",
]
