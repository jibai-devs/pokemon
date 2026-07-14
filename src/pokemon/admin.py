"""Central entry point.

``build_agent`` is what ``main.py`` (Kaggle submission) and ``cli.py``
(local WSL runs) both call to get an ``Agent`` callable. The returned
closure is the one thing that actually receives ``obs`` from the engine each
decision. Every decision goes through two explicit steps, in order:

1. **Select** -- ``select_ruleset(obs, ruleset_name)`` decides which
   registered ``Ruleset`` applies to *this* gamestate. Four are registered
   (see ``pokemon.heuristics.RULESETS``): "dragapult", "dragapult_search",
   "dragapult_opening", and "dragapult_smarter_search"; today's actual
   switch is turn-based -- our own first turn (whichever side we're on)
   prefers "dragapult_opening", every turn after that prefers
   "dragapult_smarter_search" -- called fresh every decision so further
   gamestate-dependent choices (e.g. a different tactics set once lethal is
   on the board) are a one-function change -- see its docstring.
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


def _init_state(ruleset: Ruleset, deck: Deck) -> object:
    """Build ``ruleset``'s persistent-state object for a new game, then seed
    ``my_deck`` on it if its state type has that field -- ``DragapultState``
    does, for ``turn_bfs_search``'s own-deck composition need (see
    ``pokemon.search_function.turn_search``); a ruleset whose state has no
    such field is untouched. Generic across rulesets via ``hasattr`` rather
    than hardcoding one state type here, since ``deck`` is only in scope in
    this module (``init_state()`` itself takes no arguments)."""
    state = ruleset.init_state()
    if hasattr(state, "my_deck"):
        state.my_deck = list(deck)
    return state


# --- Step 1: decide which ruleset applies to a gamestate ---------------------


def _is_own_first_turn(obs: Observation) -> bool:
    """True on the earliest decision where *we* actually get to act.

    The engine's ``turn`` counter is global/shared across both players, not
    reset per player (that's exactly why ``board.Ctx`` tracks ``going_first``
    as its own separate field rather than inferring it from turn parity --
    see ``setup_pokemon``'s use of it for the same reason). So our own first
    turn is turn 1 if we went first, or turn 2 if we went second.

    Duplicates ``_build_ctx``'s ``going_first`` derivation exactly (rather
    than building a full ``Ctx`` here, since ``select_ruleset`` runs before
    ``ctx`` exists -- see ``build_agent``'s ``play()``), including its
    existing quirk: ``docs/CABT.md`` documents ``firstPlayer`` as ``-1``
    until the engine resolves it, not absent/``None`` -- ``_build_ctx``
    only treats an *absent* key as "unknown" (falling back to "assume
    going first"), so a literal ``-1`` would compare unequal to either
    player index and read as "going second" instead of "undetermined."
    Left as-is for consistency with ``_build_ctx``/``setup_pokemon``'s
    existing behavior rather than diverging in this one new function --
    worth fixing in both places together if it turns out to matter.
    """
    current = obs.get("current") or {}
    turn = current.get("turn")
    first_player = current.get("firstPlayer")
    your_index = current.get("yourIndex", 0)
    going_first = (first_player == your_index) if first_player is not None else None
    return (turn == 1 and going_first is not False) or (turn == 2 and going_first is False)


def _select_ruleset_name(obs: Observation, ruleset_name: str) -> str:
    """The ``RULESETS`` key ``select_ruleset`` resolves to for this
    decision -- factored out from the lookup itself so the chosen name can
    be logged (see ``select_ruleset``) before fetching the ``Ruleset``.

    To opt out of all switching (plain heuristics only, no search at all),
    uncomment the early return below.
    """
    # return ruleset_name  # prefer plain heuristics only instead, no search at all
    if _is_own_first_turn(obs):
        for candidate in ("dragapult_opening", "dragapult_smarter_search"):
            if candidate in RULESETS:
                return candidate
        return ruleset_name
    if "dragapult_smarter_search" in RULESETS:
        return "dragapult_smarter_search"
    return ruleset_name


def select_ruleset(obs: Observation, ruleset_name: str) -> Ruleset:
    """Decide which registered ``Ruleset`` applies to this decision's
    ``obs`` (gamestate). Prints the chosen ruleset's name every decision
    (unconditional ``print``, not routed through the ``-v`` verbose gate --
    same convention as ``dragapult.print_prize_check``).

    Called fresh on every decision -- not just once at ``build_agent``
    construction time -- so gamestate-dependent selection is a drop-in
    extension, not a refactor. Four rulesets are registered right now (see
    ``pokemon.heuristics.RULESETS``): ``"dragapult"`` (hand-written
    heuristics only), ``"dragapult_search"`` (engine-backed BFS search
    scored by the generic ``score_line``, falling back to the same
    hand-written heuristics), ``"dragapult_opening"`` (same, but scored by
    ``opening_score.opening_turn_score`` -- built from
    ``deck/guidelines_for_first turn.txt``), and ``"dragapult_smarter_search"``
    (same, but scored by ``smart_score.dragapult_smart_score`` -- built from
    ``deck/guidelines_for_phantom_dive.txt`` and
    ``deck/dragapult_deck_explanation.md``).

    Current behavior (see ``_select_ruleset_name`` for the actual logic,
    kept separate so the resolved name can be logged before the lookup): on
    our own first turn (``_is_own_first_turn``, whichever side we're on),
    prefer ``"dragapult_opening"``; every turn from then on, prefer
    ``"dragapult_smarter_search"``. ``"dragapult_search"`` (the
    generic-``score_line`` ruleset) is registered but not selected by this
    switch -- still directly reachable via
    ``build_agent(deck, "dragapult_search")`` for comparison. Falls back to
    ``RULESETS[ruleset_name]`` -- the name ``build_agent`` was constructed
    with -- if the preferred key isn't registered, rather than a
    ``KeyError``. See ``_select_ruleset_name``'s docstring for how to opt
    out of switching entirely.

    To extend this further, inspect more of ``obs`` (board state, a
    detected archetype, ``ctx.state`` if you thread it through, ...) and
    look up a different key in ``RULESETS``. ``run_ruleset`` and everything
    upstream of it already accept whatever ``Ruleset`` this returns -- no
    other change required.

    Caveat: all four registered rulesets share ``DragapultState`` as their
    state shape today, so swapping between them (including the turn-1
    switch above) is already safe as far as state goes. That won't
    automatically hold for a *future* ruleset with a different state shape
    -- ``build_agent`` creates ``state`` once (via the initial
    ``ruleset_name``'s ``init_state()``, through ``_init_state``) and passes
    that same object to ``run_ruleset`` on every decision regardless of
    which ruleset this function picks. A ruleset whose rules can't
    read/write that shape would need ``build_agent`` to hold one state
    object per registered ruleset instead (e.g. a ``dict[str, object]`` keyed
    by ruleset name) and this function's caller would need the matching one.
    """
    name = _select_ruleset_name(obs, ruleset_name)
    print(f"[ruleset] {name}")
    return RULESETS[name]


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

    ``ruleset_name`` seeds both the persistent-memory object (via
    ``_init_state`` -- there's no gamestate yet at deck-submission time for
    ``select_ruleset`` to work with) and every decision's default selection.

    Four decisionmakers are registered today (``pokemon.heuristics.RULESETS``)
    -- call any of them directly by name, e.g.:

    ..  code-block:: python

        build_agent(deck, "dragapult")                  # hand-written heuristics only
        build_agent(deck, "dragapult_search")            # BFS search scored by score_line, same fallback
        build_agent(deck, "dragapult_opening")           # BFS search scored for turn 1, same fallback
        build_agent(deck, "dragapult_smarter_search")    # BFS search scored by dragapult_smart_score, same fallback

    Note ``ruleset_name`` here only seeds initial state and the ultimate
    fallback -- ``select_ruleset`` (above) already runs every decision and
    currently switches to "dragapult_opening" on our own first turn, then
    "dragapult_smarter_search" every turn after, regardless of which of
    these four you pass, so calling ``build_agent(deck, "dragapult")``
    doesn't actually pin the agent to plain heuristics; see that function's
    docstring for how to change that.
    """
    # Named distinctly from `play()`'s own local `ruleset` below -- reusing
    # that name here would make Python treat `ruleset` as local throughout
    # `play()` (assigned anywhere in a function makes a name local
    # everywhere in it) and raise UnboundLocalError on the branch below.
    initial_ruleset = RULESETS[ruleset_name]
    state = _init_state(initial_ruleset, deck)

    def play(obs: Observation) -> list[int]:
        nonlocal state
        if obs["select"] is None:
            state = _init_state(initial_ruleset, deck)  # new game -- cross-turn memory doesn't carry over
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
    state = _init_state(ruleset, deck)

    def play(obs: Observation) -> list[int]:
        nonlocal state
        if obs["select"] is None:
            state = _init_state(ruleset, deck)  # new game starting -- cross-turn memory doesn't carry over
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
