"""Central entry point.

``build_agent`` is what ``main.py`` (Kaggle submission) and ``cli.py``
(local WSL runs) both call to get an ``Agent`` callable. The returned
closure is the one thing that actually receives ``obs`` from the engine each
decision; it owns each game's persistent-memory object's lifecycle (create
at deck-submission, replace at the next one), builds that decision's
``Ctx``, and dispatches to whichever ``Ruleset`` is registered for the deck
being played.

The actual heuristic sets ("rulesets") live under ``pokemon.heuristics`` --
see that package's ``__init__.py`` for how to register a new deck's rules.
This module doesn't need to change when one is added. Swapping which ruleset
is *active* mid-game (rather than once, at ``build_agent`` construction
time) would only require changing how ``play`` looks up ``ruleset`` below --
e.g. keying off something in ``obs`` instead of the closed-over
``ruleset_name`` -- everything else here already supports it.
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


def build_agent(deck: Deck, ruleset_name: str) -> Agent:
    """Build an agent bound to ``deck`` that dispatches every decision to
    ``RULESETS[ruleset_name]``'s rules in priority order, falling back to a
    random legal choice when none of them apply -- so a bug or gap in one
    rule can never crash a game, only under-perform."""
    return _build_agent_for_ruleset(deck, RULESETS[ruleset_name])


def _build_agent_for_ruleset(deck: Deck, ruleset: Ruleset) -> Agent:
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

    return play
