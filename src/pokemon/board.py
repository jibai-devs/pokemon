"""Deck-agnostic board-reading helpers and the per-decision ``Ctx`` builder.

``Ctx`` is the read-only view of one decision handed to every heuristic. It's
generic over its ``state`` field's type so each ruleset module can declare
its own alias (e.g. ``DragapultCtx = Ctx[DragapultState]``, see
``dragapult_state.py``) and get real attribute-level typing on ``ctx.state``
instead of a stringly-keyed dict. Building/owning that state's lifecycle
across a whole game is ``admin.py``'s job, not this module's -- this module
only knows how to build one decision's ``Ctx`` from ``obs``.

Some rules may depend on ``select.deck`` / ``select.contextCard`` field
shapes that `docs/plans/000_plan_engine_enum_extraction.md` hasn't empirically
verified yet (its Phase 2) — best-effort, and should degrade to "doesn't
apply" (returning ``None``) rather than guessing wrong.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Generic, TypeAlias, TypeVar

from pokemon.cabt_enums import AreaType, OptionType
from pokemon.types import (
    CardState,
    CurrentState,
    Observation,
    Option,
    PlayerState,
    SelectData,
)

S = TypeVar("S")

# Shared verbosity flag: lives here (rather than in admin.py) so any rule
# module can log through it too -- e.g. a ruleset's own hook wants to print
# a running readout to stdout -- without creating a cycle back through
# admin.py (which itself depends on the heuristics package).
_verbose = False


def set_verbose(value: bool) -> None:
    global _verbose
    _verbose = value


def _log(msg: str) -> None:
    if _verbose:
        print(msg)


@dataclass
class Ctx(Generic[S]):
    """Decision context passed to every heuristic.

    ``sel_type`` (the SelectType of the whole select block) is carried
    through for heuristics that need it, alongside ``sel_context`` (the
    actual disambiguator per the engine's enum reference).

    ``state`` is the active ruleset's persistent-state object -- its shape is
    declared by whichever ruleset module built it via that module's own
    ``init_state`` factory (see ``admin.py``). It persists across every
    decision within one game, reset whenever a new deck-submission phase
    starts. Rulesets that don't need memory can ignore it entirely.
    """

    obs: Observation
    select: SelectData
    options: list[Option]
    sel_type: int | None
    sel_context: int | None
    hand: list[CardState]
    me: PlayerState
    opp: PlayerState
    current: CurrentState
    turn: int | None
    going_first: bool | None
    state: S


def _build_ctx(obs: Observation, state: S) -> Ctx[S]:
    select = obs["select"]
    assert select is not None
    current = obs.get("current", {})
    my_idx = current.get("yourIndex", 0)
    players = current.get("players", [])
    me: PlayerState = players[my_idx] if my_idx < len(players) else {}
    opp_idx = 1 - my_idx if len(players) > 1 else None
    opp: PlayerState = players[opp_idx] if opp_idx is not None and opp_idx < len(players) else {}
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


# A ruleset's rule function: given a decision, return the chosen option
# index/indices, or ``None`` if it doesn't apply. Parameterized over
# ``Ctx[Any]`` (rather than a specific ruleset's ``Ctx[SomeState]``) so a
# single ruleset's list of rules -- each actually typed against its own
# state, e.g. ``DragapultCtx = Ctx[DragapultState]`` -- can be declared as
# ``list[Heuristic]`` without a variance error: ``Any`` is what makes a
# ``Callable[[DragapultCtx], ...]`` assignable here.
Heuristic: TypeAlias = Callable[["Ctx[Any]"], list[int] | None]


# --- Board-state helpers, deck-agnostic ------------------------------------
#
# Best-effort readers over the card-dict shapes observed in real Kaggle
# replays (see docs/plans/001_training_pipeline.md and example_replay.json):
# a card is ``{id, name, hp, maxHp, energies, energyCards, tools, ...}``.
# These degrade to ``None``/``[]``/``False`` rather than raising if a field
# is missing, per the "fail safe, don't guess wrong" convention already used
# by ``_option_card_id``. None of these touch ``ctx.state``, so they accept
# any ruleset's ``Ctx`` specialization (``Ctx[Any]``).


def remaining_hp(card: CardState | None) -> int | None:
    if not card:
        return None
    return card.get("hp")


def max_hp(card: CardState | None) -> int | None:
    if not card:
        return None
    return card.get("maxHp")


def energy_cards(card: CardState | None) -> list[CardState]:
    if not card:
        return []
    return card.get("energyCards") or []


def energy_count(card: CardState | None) -> int:
    return len(energy_cards(card))


def bench_cards(player: PlayerState) -> list[CardState]:
    return player.get("bench") or []


def active_card(player: PlayerState) -> CardState | None:
    active = player.get("active") or []
    return active[0] if active else None


def all_pokemon(player: PlayerState) -> list[CardState]:
    """Every one of ``player``'s Pokemon currently in play (active + bench)."""
    a = active_card(player)
    return ([a] if a else []) + bench_cards(player)


def prizes_remaining(player: PlayerState) -> int:
    """How many of ``player``'s 6 prize cards are still untaken. Prize
    contents are hidden (every entry is ``None`` even for the owner, until
    taken) -- the array *shrinks* as prizes are taken, so its length is the
    remaining count (PKM-021; contradicts docs/CABT.md's "None = taken")."""
    return len(player.get("prize") or [])


def _hand_card(ctx: "Ctx[Any]", idx: int | None) -> CardState | None:
    if idx is None or not (0 <= idx < len(ctx.hand)):
        return None
    return ctx.hand[idx]


def _active_card(ctx: "Ctx[Any]") -> CardState | None:
    active = ctx.me.get("active") or []
    return active[0] if active else None


def _board_card(ctx: "Ctx[Any]", area: int | None, idx: int | None) -> CardState | None:
    if area is None or idx is None:
        return None
    if area == AreaType.ACTIVE:
        return _active_card(ctx)
    if area == AreaType.BENCH:
        bench = ctx.me.get("bench") or []
        return bench[idx] if 0 <= idx < len(bench) else None
    return None


def _option_card_id(ctx: "Ctx[Any]", opt: Option) -> int | None:
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


def _rank_and_pick(ctx: "Ctx[Any]", targets: list[int]) -> list[int] | None:
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
