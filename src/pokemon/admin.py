"""Central entry point.

``build_agent`` is what ``main.py`` (Kaggle submission) and ``cli.py``
(local WSL runs) both call to get an ``Agent`` callable. The returned
closure is the one thing that actually receives ``obs`` from the engine each
decision. Every decision goes through two explicit steps, in order:

1. **Select** -- ``select_ruleset(obs, ruleset_name)`` decides which
   registered ``Ruleset`` applies to *this* gamestate. Today that's a
   placeholder (there's only one ruleset registered, "dragapult", and one
   agent is built per game), but it's called fresh every decision so a
   future gamestate-dependent choice (e.g. a different tactics set once
   lethal is on the board) is a one-function change -- see its docstring.
2. **Run** -- ``run_ruleset(ctx, ruleset)`` submits that decision's ``Ctx``
   to the selected ``Ruleset`` and returns the chosen option indices,
   walking ``ruleset.rules`` in priority order (first-match-wins) and
   falling back to a random legal choice if nothing fires.

``build_agent``'s closure also owns each game's persistent-memory object's
lifecycle (create at deck-submission, replace at the next one) and builds
each decision's ``Ctx`` before handing it to the two steps above.

The actual heuristic sets ("rulesets") live under ``pokemon.heuristics`` --
see that package's ``__init__.py`` for how to register a new deck's rules.
This module doesn't need to change when one is added.
"""

import random

from pokemon.board import Ctx, _build_ctx, _log, set_verbose
from pokemon.catalog import format_option
from pokemon.decks import deck_summary
from pokemon.heuristics import RULESETS, Ruleset
from pokemon.types import Agent, Deck, Observation

_game_num = 0


def set_game_num(value: int) -> None:
    global _game_num
    _game_num = value


# --- Step 1: decide which ruleset applies to a gamestate ---------------------


def select_ruleset(obs: Observation, ruleset_name: str) -> Ruleset:
    """Decide which registered ``Ruleset`` applies to this decision's
    ``obs`` (gamestate).

    Called fresh on every decision -- not just once at ``build_agent``
    construction time -- so gamestate-dependent selection is a drop-in
    extension, not a refactor. Today it's a placeholder: it always returns
    ``RULESETS[ruleset_name]``, the name ``build_agent`` was constructed
    with, because there's only one ruleset registered ("dragapult") and
    nothing in ``obs`` to key off yet.

    To make ruleset choice actually vary by gamestate later (e.g. a
    different tactics set once a lethal line is on the board, or a future
    multi-deck agent that must first identify which deck it's playing),
    extend this function to inspect ``obs`` (turn number, board state, a
    detected archetype, ``ctx.state`` if you thread it through, ...) and
    look up a different key in ``RULESETS``. ``run_ruleset`` and everything
    upstream of it already accept whatever ``Ruleset`` this returns -- no
    other change required.

    Example -- swapping to a second ruleset on turn 1 only (requires a
    "ruleset2" entry registered in ``RULESETS``, see
    ``pokemon.heuristics.RULESETS``; left commented out since no such
    ruleset exists yet):

    ..  code-block:: python

        # IS_TURN_1 = obs["current"]["turn"] == 1
        # if IS_TURN_1:
        #     return RULESETS["ruleset2"]
        # return RULESETS[ruleset_name]

    Caveat if/when this gets uncommented: ``build_agent`` creates ``state``
    once, via the *initial* ``ruleset_name``'s ``init_state()``, and passes
    that same object to ``run_ruleset`` on every decision regardless of
    which ruleset ``select_ruleset`` picks. Swapping is only safe as-is if
    "ruleset2"'s rules can read/write that same state shape -- otherwise
    ``build_agent`` needs to hold one state object per registered ruleset
    (e.g. a ``dict[str, object]`` keyed by ruleset name, each initialized
    via that ruleset's own ``init_state()``) and ``run_ruleset`` needs the
    matching one for whichever ``Ruleset`` this function returns.
    """
    return RULESETS[ruleset_name]


# --- Step 2: submit a gamestate to the selected ruleset -----------------------


def run_ruleset(ctx: Ctx, ruleset: Ruleset) -> list[int]:
    """Submit one decision (``ctx``, already built from that decision's
    ``obs``) to ``ruleset`` and return the chosen option indices.

    Walks ``ruleset.rules`` in priority order -- the first rule that
    returns a non-empty, sufficiently-sized selection wins. A rule that
    raises is treated as "doesn't apply" and logged, never fatal, so a bug
    or gap in one rule can never crash a game, only under-perform. Falls
    back to a uniformly random legal choice if no rule fires.
    """
    options = ctx.options
    max_count = ctx.select["maxCount"]
    min_count = ctx.select.get("minCount") or 0

    for rule in ruleset.rules:
        try:
            chosen = rule(ctx)
        except Exception as exc:  # a bad heuristic must never crash a game
            _log(f"  [heuristic {rule.__name__} raised {exc!r}, skipping]")
            continue
        if not chosen:
            continue
        chosen = [i for i in chosen if 0 <= i < len(options)][:max_count]
        # A selection with fewer than minCount indices is invalid -- a
        # real playtest showed the engine silently ending the episode as
        # a draw (no exception) the first time a heuristic under-counted
        # a multi-select. Treat that as "this heuristic doesn't apply"
        # rather than submit it.
        if len(chosen) >= min_count and chosen:
            picked = [format_option(options[i], ctx.hand) for i in chosen]
            _log(f"  -> {rule.__name__}: {', '.join(picked)}")
            return chosen

    chosen = random.sample(range(len(options)), min(max_count, len(options)))
    picked = [format_option(options[i], ctx.hand) for i in chosen]
    _log(f"  -> fallback random: {', '.join(picked)}")
    return chosen


# --- Agent construction --------------------------------------------------------


def build_agent(deck: Deck, ruleset_name: str) -> Agent:
    """Build an agent bound to ``deck`` that, for every decision, runs the
    two steps above in order: ``select_ruleset`` to decide, then
    ``run_ruleset`` to submit the gamestate and get a decision back. Falls
    back to a random legal choice when no rule in the selected ruleset
    applies -- so a bug or gap in one rule can never crash a game, only
    under-perform.

    ``ruleset_name`` seeds both the persistent-memory object (created via
    ``RULESETS[ruleset_name].init_state()`` -- there's no gamestate yet at
    deck-submission time for ``select_ruleset`` to work with) and every
    decision's default selection.
    """
    state = RULESETS[ruleset_name].init_state()

    def play(obs: Observation) -> list[int]:
        nonlocal state
        if obs["select"] is None:
            state = RULESETS[ruleset_name].init_state()  # new game -- cross-turn memory doesn't carry over
            lines, checksum = deck_summary(deck)
            _log(f"\n{'=' * 60}")
            _log(f"GAME {_game_num}: Submitting deck ({len(deck)} cards, sha256:{checksum}) [heuristic]")
            _log(f"{'=' * 60}")
            if _game_num <= 1:
                for line in lines:
                    _log(line)
            return deck

        ruleset = select_ruleset(obs, ruleset_name)  # 1. decide
        ctx: Ctx[object] = _build_ctx(obs, state)
        return run_ruleset(ctx, ruleset)  # 2. submit gamestate, get a decision

    return play


def _build_agent_for_ruleset(deck: Deck, ruleset: Ruleset) -> Agent:
    """Build an agent permanently bound to one already-resolved ``Ruleset``
    object -- no per-decision selection. Used directly by tests that want a
    fixed rule list without registering it in ``RULESETS``; ``build_agent``
    above is the selection-aware entry point everything else should use."""
    state = ruleset.init_state()

    def play(obs: Observation) -> list[int]:
        nonlocal state
        if obs["select"] is None:
            state = ruleset.init_state()  # new game starting -- cross-turn memory doesn't carry over
            lines, checksum = deck_summary(deck)
            _log(f"\n{'=' * 60}")
            _log(f"GAME {_game_num}: Submitting deck ({len(deck)} cards, sha256:{checksum}) [heuristic]")
            _log(f"{'=' * 60}")
            if _game_num <= 1:
                for line in lines:
                    _log(line)
            return deck

        ctx: Ctx[object] = _build_ctx(obs, state)
        return run_ruleset(ctx, ruleset)

    return play
