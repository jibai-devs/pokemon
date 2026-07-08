"""Modular heuristic agent framework.

Each heuristic is a small, independent function: given the current decision
context, return the chosen option index/indices, or ``None`` if it doesn't
apply. ``make_heuristic_agent`` tries each heuristic in priority order and
falls back to a random legal choice if none fire — so a bug or gap in one
heuristic can never crash a game, only under-perform.

This module is deck-agnostic scaffolding. Deck-specific heuristics should be
added as functions below (or in a separate module) and registered in
``HEURISTIC_SETS`` keyed by deck name (see ``pokemon.decks.DECKS``).

Some heuristics may depend on ``select.deck`` / ``select.contextCard`` field
shapes that `docs/000_plan_engine_enum_extraction.md` hasn't empirically
verified yet (its Phase 2) — best-effort, and should degrade to "doesn't
apply" (returning ``None``) rather than guessing wrong.
"""

import random
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pokemon.cabt_enums import AreaType, OptionType
from pokemon.catalog import format_option
from pokemon.decks import deck_summary

_verbose = False
_game_num = 0


def set_verbose(value: bool) -> None:
    global _verbose
    _verbose = value


def set_game_num(value: int) -> None:
    global _game_num
    _game_num = value


def _log(msg: str) -> None:
    if _verbose:
        print(msg)


@dataclass
class Ctx:
    """Decision context passed to every heuristic.

    ``sel_type`` (the SelectType of the whole select block) is carried
    through for heuristics that need it, alongside ``sel_context`` (the
    actual disambiguator per the engine's enum reference).

    ``state`` is a mutable dict that persists across every decision within
    one game (owned by the agent's closure in ``make_heuristic_agent``, reset
    whenever a new deck-submission phase starts) — for heuristics that need
    to remember something across turns (e.g. "has this Munkidori's Darkness
    Energy already secured a KO", "has Meowth ex's search resolved yet").
    Heuristics that don't need memory can ignore it entirely.
    """

    obs: dict
    select: dict
    options: list[dict]
    sel_type: int | None
    sel_context: int | None
    hand: list[dict]
    me: dict
    opp: dict
    current: dict
    turn: int | None
    going_first: bool | None
    state: dict


def _build_ctx(obs: dict, state: dict) -> Ctx:
    select = obs["select"]
    current = obs.get("current", {})
    my_idx = current.get("yourIndex", 0)
    players = current.get("players", [])
    me = players[my_idx] if my_idx < len(players) else {}
    opp_idx = 1 - my_idx if len(players) > 1 else None
    opp = players[opp_idx] if opp_idx is not None and opp_idx < len(players) else {}
    first_player = current.get("firstPlayer")
    going_first = (first_player == my_idx) if first_player is not None else None
    return Ctx(
        obs=obs,
        select=select,
        options=select.get("option") or [],
        sel_type=select.get("type"),
        sel_context=select.get("context"),
        hand=me.get("hand") or [],
        me=me,
        opp=opp,
        current=current,
        turn=current.get("turn"),
        going_first=going_first,
        state=state,
    )


# --- Board-state helpers, deck-agnostic ------------------------------------
#
# Best-effort readers over the card-dict shapes observed in real Kaggle
# replays (see docs/001_training_pipeline.md and example_replay.json):
# a card is ``{id, name, hp, maxHp, energies, energyCards, tools, ...}``.
# These degrade to ``None``/``[]``/``False`` rather than raising if a field
# is missing, per the "fail safe, don't guess wrong" convention already used
# by ``_option_card_id``.


def remaining_hp(card: dict | None) -> int | None:
    if not card:
        return None
    return card.get("hp")


def max_hp(card: dict | None) -> int | None:
    if not card:
        return None
    return card.get("maxHp")


def energy_cards(card: dict | None) -> list[dict]:
    if not card:
        return []
    return card.get("energyCards") or []


def energy_count(card: dict | None) -> int:
    return len(energy_cards(card))


def bench_cards(player: dict) -> list[dict]:
    return player.get("bench") or []


def active_card(player: dict) -> dict | None:
    active = player.get("active") or []
    return active[0] if active else None


def all_pokemon(player: dict) -> list[dict]:
    """Every one of ``player``'s Pokemon currently in play (active + bench)."""
    a = active_card(player)
    return ([a] if a else []) + bench_cards(player)


def _hand_card(ctx: Ctx, idx: int | None) -> dict | None:
    if idx is None or not (0 <= idx < len(ctx.hand)):
        return None
    return ctx.hand[idx]


def _active_card(ctx: Ctx) -> dict | None:
    active = ctx.me.get("active") or []
    return active[0] if active else None


def _board_card(ctx: Ctx, area: int | None, idx: int | None) -> dict | None:
    if area is None or idx is None:
        return None
    if area == AreaType.ACTIVE:
        return _active_card(ctx)
    if area == AreaType.BENCH:
        bench = ctx.me.get("bench") or []
        return bench[idx] if 0 <= idx < len(bench) else None
    return None


def _option_card_id(ctx: Ctx, opt: dict) -> int | None:
    """Best-effort lookup of the card a CARD-shaped option refers to.

    Always resolves hand-area options directly (``area``/``index`` on the
    option itself are well-specified) *before* touching the speculative
    ``select.deck`` list — a stale or unrelated ``deck`` entry keyed by list
    position can otherwise override a perfectly resolvable hand option. For
    deck/looking-area options (search reveals), ``select.deck`` is indexed
    by the option's own ``index`` field, not its list position — still
    speculative (Phase 2 of the enum extraction plan hasn't confirmed this),
    so it's only attempted when the option's own ``area`` says DECK/LOOKING.
    """
    if opt.get("type") not in (OptionType.CARD, OptionType.TOOL_CARD, OptionType.ENERGY_CARD):
        return None
    area = opt.get("area")
    opt_idx = opt.get("index")
    if area == AreaType.HAND:
        card = _hand_card(ctx, opt_idx)
        return card.get("id") if card else None
    if area in (AreaType.ACTIVE, AreaType.BENCH):
        card = _board_card(ctx, area, opt_idx)
        return card.get("id") if card else None
    if area in (AreaType.DECK, AreaType.LOOKING):
        deck = ctx.select.get("deck")
        if isinstance(deck, list) and opt_idx is not None and 0 <= opt_idx < len(deck):
            entry = deck[opt_idx]
            if isinstance(entry, dict):
                return entry.get("id")
        context_card = ctx.select.get("contextCard")
        if isinstance(context_card, dict):
            return context_card.get("id")
    return None


Heuristic = Callable[[Ctx], list[int] | None]


def _rank_and_pick(ctx: Ctx, targets: list[int]) -> list[int] | None:
    """Rank options whose resolved card is in ``targets`` (best-first, by
    position in ``targets``) and return the top ``maxCount`` of them, or
    ``None`` if there aren't enough confident picks to fill the required
    count.

    Must return exactly ``select["maxCount"]`` indices — returning fewer than
    required is an invalid action; a real playtest showed the engine silently
    ending the episode as a draw (no exception) the first time this returned
    only 1 index for a 2-card select. If there aren't enough confident picks
    to fill the required count, defer to random entirely rather than submit a
    partial selection.
    """
    need = ctx.select.get("maxCount") or 1
    ranked: list[tuple[int, int]] = []
    for i, opt in enumerate(ctx.options):
        cid = _option_card_id(ctx, opt)
        if cid in targets:
            ranked.append((targets.index(cid), i))
    if len(ranked) < need:
        return None
    ranked.sort()
    return [i for _, i in ranked[:need]]


# --- Deck-specific heuristic sets -------------------------------------------
#
# Add heuristic functions above (or in their own module) and register a
# priority-ordered list per deck name here, mirroring pokemon.decks.DECKS.
# An empty list is a valid, safe default — the agent just falls back to
# random legal moves for every decision.

DEFAULT_HEURISTICS: list[Heuristic] = []
HEURISTIC_SETS: dict[str, list[Heuristic]] = {}

# Registered here (rather than at import time in each deck module) to avoid a
# circular import — heuristics_dragapult imports Ctx/helpers from this module.
from pokemon.heuristics_dragapult import DRAGAPULT_HEURISTICS  # noqa: E402

HEURISTIC_SETS["dragapult"] = DRAGAPULT_HEURISTICS


def make_heuristic_agent(
    deck: list[int], heuristics: list[Heuristic] | None = None
) -> Callable[[dict], list[int]]:
    """Build an agent that applies ``heuristics`` in order, falling back to a
    random legal choice when none of them apply to the current decision."""
    rules = heuristics if heuristics is not None else DEFAULT_HEURISTICS
    state: dict = {}

    def play(obs: dict) -> list[int]:
        if obs["select"] is None:
            state.clear()  # new game starting — cross-turn memory doesn't carry over
            lines, checksum = deck_summary(deck)
            _log(f"\n{'=' * 60}")
            _log(f"GAME {_game_num}: Submitting deck ({len(deck)} cards, sha256:{checksum}) [heuristic]")
            _log(f"{'=' * 60}")
            if _game_num <= 1:
                for line in lines:
                    _log(line)
            return deck

        ctx = _build_ctx(obs, state)
        options = ctx.options
        max_count = ctx.select["maxCount"]
        min_count = ctx.select.get("minCount") or 0

        for rule in rules:
            try:
                chosen: Any = rule(ctx)
            except Exception as exc:  # a bad heuristic must never crash a game
                _log(f"  [heuristic {rule.__name__} raised {exc!r}, skipping]")
                continue
            if not chosen:
                continue
            chosen = [i for i in chosen if 0 <= i < len(options)][:max_count]
            # A selection with fewer than minCount indices is invalid — a real
            # playtest showed the engine silently ending the episode as a draw
            # (no exception) the first time a heuristic under-counted a
            # multi-select. Treat that as "this heuristic doesn't apply"
            # rather than submit it.
            if len(chosen) >= min_count and chosen:
                if _verbose:
                    picked = [format_option(options[i], ctx.hand) for i in chosen]
                    _log(f"  -> {rule.__name__}: {', '.join(picked)}")
                return chosen

        chosen = random.sample(range(len(options)), min(max_count, len(options)))
        if _verbose:
            picked = [format_option(options[i], ctx.hand) for i in chosen]
            _log(f"  -> fallback random: {', '.join(picked)}")
        return chosen

    return play
