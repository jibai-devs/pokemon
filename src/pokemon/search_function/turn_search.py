"""Budgeted end-of-turn BFS over the native search API (plan 009 Phase 3).

Owns the full turn-search stack used by the agent:

- ``expand_end_of_turn`` — engine-backed BFS under node/depth/beam caps
- ``score_line`` / ``first_action_of_best_line`` — rank leaves
- ``search`` — the generic entry point: given a decision (``ctx``) and a
  scorer (``score_fn``), runs the budgeted BFS and returns the chosen
  action. Callable directly by any decisionmaking engine, not just as a
  registered rule.
- ``make_turn_bfs_search`` — wraps ``search`` as a plain ``Heuristic``
  (``Callable[[Ctx], list[int] | None]``) for registering in a
  ``Ruleset``'s rule list (``play -v`` dumps ranked end states either way)

Given a live ``obs`` (must include ``search_begin_input``), fork the state via
``SearchBegin``, walk legal option sequences, and collect terminal nodes where
either the game ends or control has left the root player (end of their turn).

Not a free exhaustive enumerator — branching is gated by ``policy``,
``max_nodes``, ``max_depth``, and optional ``beam``.
"""

from __future__ import annotations

import itertools
import random
from collections import deque
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

from pokemon.board import Ctx, _log
from pokemon.cabt_enums import OptionType, SelectType
from pokemon.catalog import format_option
from pokemon.determinize import sample_determinization
from pokemon.native_search import SearchResult, SearchSession
from pokemon.types import CardId, Observation, Option, SearchStartConfig

TerminalKind = Literal["eot", "win", "loss", "draw", "budget", "opp_choice", "error", "depth"]

# Main-phase options a tactical search keeps. Non-Main contexts keep everything
# (damage allocate, discards from Ultra Ball mid-effect, etc. once already on
# a tactical path).
_TACTICAL_MAIN_TYPES = {
    OptionType.ATTACK,
    OptionType.END,
    OptionType.ABILITY,
    OptionType.RETREAT,
    OptionType.PLAY,  # filtered further by card id when known
    OptionType.ATTACH,
}

# Dragapult tactical card ids (kept here so turn_search stays usable without
# importing the full heuristics module).
_BOSS_ORDERS = 1182
_TACTICAL_PLAY_IDS = {_BOSS_ORDERS}


@dataclass
class TurnLine:
    actions: list[list[int]]
    end_obs: Observation | None
    terminal: TerminalKind
    search_id: int | None = None
    nodes: int = 0


# A custom objective: given a leaf and which player is "us", return
# anything comparable (a tuple for lexicographic tie-breaking like
# ``score_line``, or just a float) -- higher is always better. Passed to
# ``first_action_of_best_line``/``format_turn_lines``/``search``/
# ``make_turn_bfs_search`` to rank BFS leaves by something other than the
# built-in ``score_line``.
ScoreFn = Callable[["TurnLine", int], Any]


@dataclass
class _Node:
    search_id: int
    obs: Observation
    actions: list[list[int]] = field(default_factory=list)
    depth: int = 0


CandidatePolicy = Literal["all", "tactical"]
ActionFilter = Callable[[Observation, list[Option], int, int], list[list[int]]]


def root_player_index(obs: Observation) -> int:
    current = obs.get("current") or {}
    return int(current.get("yourIndex", 0))


def classify_terminal(root_player: int, obs: Observation) -> TerminalKind | None:
    """Return a terminal kind if this observation ends *our* controllable line.

    Empirically (live SearchStep traces): after Attack/End fully resolves into
    the opponent's next free decision, ``current.yourIndex`` becomes the
    opponent. Mid-turn constrained picks (damage counters, Ultra Ball discards)
    keep ``yourIndex`` as the root player.
    """
    current = obs.get("current") or {}
    result = current.get("result", -1)
    if result is not None and int(result) >= 0:
        r = int(result)
        if r == 2:
            return "draw"
        if r == root_player:
            return "win"
        return "loss"
    if int(current.get("yourIndex", root_player)) != root_player:
        return "eot"
    # No remaining decision and not finished — treat as EOT (defensive).
    sel = obs.get("select")
    if not sel or not sel.get("option"):
        return "eot"
    return None


def _option_card_id_from_obs(obs: Observation, opt: Option) -> int | None:
    """Best-effort card id for a PLAY/ATTACH/etc. option (hand area)."""
    card_id = opt.get("cardId")
    if card_id is not None:
        return int(card_id)
    idx = opt.get("index")
    area = opt.get("area")
    current = obs.get("current") or {}
    players = current.get("players") or []
    me_idx = int(current.get("yourIndex", 0))
    if not players or me_idx >= len(players):
        return None
    me = players[me_idx]
    hand = me.get("hand") or []
    if area in (None, 2) and idx is not None and 0 <= idx < len(hand):
        card = hand[idx]
        if card:
            return card.get("id")
    # Ability/attack on board: inPlayArea/index
    in_area = opt.get("inPlayArea")
    in_idx = opt.get("inPlayIndex")
    if in_area is not None and in_idx is not None:
        if in_area == 1:  # Active-ish — engine AreaType values vary; try active first
            active = me.get("active") or []
            if active and active[0]:
                return active[0].get("id")
        bench = me.get("bench") or []
        if 0 <= int(in_idx) < len(bench) and bench[int(in_idx)]:
            return bench[int(in_idx)].get("id")
    if opt.get("area") == 5 and idx is not None:  # bench
        bench = me.get("bench") or []
        if 0 <= idx < len(bench) and bench[idx]:
            return bench[idx].get("id")
    return None


def _enumerate_selections(
    n_options: int, min_count: int, max_count: int, allowed: Sequence[int] | None = None
) -> list[list[int]]:
    pool = list(allowed) if allowed is not None else list(range(n_options))
    if not pool:
        return []
    min_count = max(0, min_count)
    max_count = min(max_count, len(pool))
    if max_count < min_count:
        return []
    out: list[list[int]] = []
    for r in range(min_count, max_count + 1):
        if r == 0:
            out.append([])
            continue
        # Cap combinatorial blow-up per decision point.
        for combo in itertools.combinations(pool, r):
            out.append(list(combo))
            if len(out) >= 256:
                return out
    return out


def candidate_actions(
    obs: Observation,
    policy: CandidatePolicy = "tactical",
) -> list[list[int]]:
    sel = obs.get("select")
    if not sel:
        return []
    options: list[Option] = list(sel.get("option") or [])
    n = len(options)
    if n == 0:
        return []
    min_c = int(sel.get("minCount", 1) or 1)
    max_c = int(sel.get("maxCount", 1) or 1)
    select_type = sel.get("type")

    if policy == "all":
        return _enumerate_selections(n, min_c, max_c)

    # tactical
    if select_type == SelectType.MAIN or select_type == 0:
        allowed: list[int] = []
        for i, opt in enumerate(options):
            t = opt.get("type")
            if t in (OptionType.ATTACK, OptionType.END, OptionType.RETREAT):
                allowed.append(i)
            elif t == OptionType.ABILITY:
                # Keep all abilities (Adrena-Brain is the main tactical one; others are rare).
                allowed.append(i)
            elif t == OptionType.PLAY:
                cid = _option_card_id_from_obs(obs, opt)
                if cid in _TACTICAL_PLAY_IDS or cid is None:
                    allowed.append(i)
            elif t == OptionType.ATTACH:
                # Only if an attack is also legal — attach may enable attack.
                # Keep one attach option max later; for now include all attaches.
                allowed.append(i)
        if not allowed:
            # Fall back to End if present else first option so the tree can terminate.
            for i, opt in enumerate(options):
                if opt.get("type") == OptionType.END:
                    return [[i]]
            return [[0]] if n else []
        return _enumerate_selections(n, min_c, max_c, allowed)

    # Forced non-Main picks on a tactical path: expand fully (capped).
    return _enumerate_selections(n, min_c, max_c)


def expand_end_of_turn(
    obs: Observation,
    my_deck: Sequence[CardId],
    *,
    policy: CandidatePolicy = "tactical",
    max_nodes: int = 2_000,
    max_depth: int = 24,
    beam: int | None = 64,
    config: SearchStartConfig | None = None,
    rng: random.Random | None = None,
    action_filter: ActionFilter | None = None,
) -> list[TurnLine]:
    """Collect end-of-turn (or game-over) leaves reachable from ``obs``.

    Requires ``obs["search_begin_input"]``. Returns an empty list if the native
    engine cannot be loaded or ``SearchBegin`` fails.
    """
    blob = obs.get("search_begin_input")
    if not blob:
        return []

    root_player = root_player_index(obs)
    cfg = config or sample_determinization(obs, my_deck, rng=rng)  # type: ignore[arg-type]
    terminals: list[TurnLine] = []
    nodes = 0

    try:
        session = SearchSession()
    except Exception:
        return []

    try:
        begin = session.begin(blob, cfg)
        if not begin.ok or begin.search_id is None or begin.observation is None:
            return [
                TurnLine(
                    actions=[],
                    end_obs=None,
                    terminal="error",
                    nodes=0,
                )
            ]

        # Immediate terminal (shouldn't happen mid-decision, but handle it).
        kind0 = classify_terminal(root_player, begin.observation)
        if kind0 is not None:
            return [
                TurnLine(
                    actions=[],
                    end_obs=begin.observation,
                    terminal=kind0,
                    search_id=begin.search_id,
                    nodes=1,
                )
            ]

        frontier: deque[_Node] = deque(
            [_Node(search_id=begin.search_id, obs=begin.observation, actions=[], depth=0)]
        )
        # Track whether root id itself must be released (children forked).
        to_release: list[int] = []

        while frontier and nodes < max_nodes:
            if beam is not None and len(frontier) > beam:
                items = sorted(frontier, key=lambda n: n.depth)
                for n in items[beam:]:
                    to_release.append(n.search_id)
                frontier = deque(items[:beam])

            node = frontier.popleft()
            nodes += 1
            if node.depth >= max_depth:
                terminals.append(
                    TurnLine(
                        actions=node.actions,
                        end_obs=node.obs,
                        terminal="depth",
                        search_id=node.search_id,
                        nodes=nodes,
                    )
                )
                to_release.append(node.search_id)
                continue

            sel = node.obs.get("select") or {}
            options = list(sel.get("option") or [])
            if action_filter is not None:
                actions_list = action_filter(
                    node.obs, options, int(sel.get("minCount", 1) or 1), int(sel.get("maxCount", 1) or 1)
                )
            else:
                actions_list = candidate_actions(node.obs, policy=policy)

            if not actions_list:
                terminals.append(
                    TurnLine(
                        actions=node.actions,
                        end_obs=node.obs,
                        terminal="error",
                        search_id=node.search_id,
                        nodes=nodes,
                    )
                )
                to_release.append(node.search_id)
                continue

            expanded_child = False
            for act in actions_list:
                if nodes >= max_nodes:
                    break
                child: SearchResult = session.step(node.search_id, act)
                if not child.ok or child.observation is None or child.search_id is None:
                    continue
                expanded_child = True
                path = [*node.actions, act]
                kind = classify_terminal(root_player, child.observation)
                if kind is not None:
                    terminals.append(
                        TurnLine(
                            actions=path,
                            end_obs=child.observation,
                            terminal=kind,
                            search_id=child.search_id,
                            nodes=nodes,
                        )
                    )
                    to_release.append(child.search_id)
                else:
                    frontier.append(
                        _Node(
                            search_id=child.search_id,
                            obs=child.observation,
                            actions=path,
                            depth=node.depth + 1,
                        )
                    )
            to_release.append(node.search_id)
            if not expanded_child and not actions_list:
                pass

        # Budget-exhausted frontier → soft terminals.
        while frontier:
            node = frontier.popleft()
            terminals.append(
                TurnLine(
                    actions=node.actions,
                    end_obs=node.obs,
                    terminal="budget",
                    search_id=node.search_id,
                    nodes=nodes,
                )
            )
            to_release.append(node.search_id)

        for sid in to_release:
            try:
                session.release(sid)
            except Exception:
                pass

        # Stamp final node counts.
        for t in terminals:
            t.nodes = nodes
        return terminals
    finally:
        session.close()


def score_line(line: TurnLine, root_player: int) -> tuple:
    """Higher is better. Used to rank BFS end-of-turn leaves.

    Order of importance:
    1. game result (win > eot/budget > draw > loss/error)
    2. own prizes remaining (fewer = better)
    3. opponent prizes remaining (more left = better)
    4. damage on opponent Active (higher = better)
    5. prefer real EOT over depth/budget cutoffs
    6. shorter action sequences (tie-break)
    """
    term_rank = {
        "win": 5,
        "eot": 3,
        "budget": 2,
        "depth": 2,
        "draw": 1,
        "opp_choice": 1,
        "loss": 0,
        "error": -1,
    }.get(line.terminal, 0)

    my_prizes = 6
    opp_prizes = 0
    opp_damage = 0
    if line.end_obs is not None:
        current = line.end_obs.get("current") or {}
        players = current.get("players") or []
        if len(players) > root_player:
            my_prizes = len(players[root_player].get("prize") or [])
        opp_idx = 1 - root_player
        if len(players) > opp_idx:
            opp = players[opp_idx]
            opp_prizes = len(opp.get("prize") or [])
            active = opp.get("active") or []
            if active and active[0] is not None:
                card = active[0]
                max_hp = card.get("maxHp")
                hp = card.get("hp")
                if max_hp is not None and hp is not None:
                    opp_damage = int(max_hp) - int(hp)

    return (
        term_rank,
        -my_prizes,
        opp_prizes,
        opp_damage,
        -len(line.actions),
    )


def first_action_of_best_line(
    lines: list[TurnLine],
    root_player: int,
    score_fn: ScoreFn = score_line,
) -> list[int] | None:
    """Pick the first action of the best-scoring terminal line, per
    ``score_fn`` (defaults to the built-in ``score_line``; pass your own
    ``(TurnLine, root_player) -> comparable`` to rank leaves by a different
    objective -- see ``search``)."""
    usable = [line for line in lines if line.actions and line.terminal != "error"]
    if not usable:
        return None
    ranked = sorted(usable, key=lambda line: score_fn(line, root_player), reverse=True)
    return ranked[0].actions[0]


def _end_state_summary(line: TurnLine, root_player: int) -> str:
    """One-line human summary of a leaf's end observation."""
    if line.end_obs is None:
        return "no-obs"
    current = line.end_obs.get("current") or {}
    players = current.get("players") or []
    my_p = opp_p = "?"
    my_active = opp_active = "?"
    if len(players) > root_player:
        me = players[root_player]
        my_p = str(len(me.get("prize") or []))
        active = me.get("active") or []
        if active and active[0] is not None:
            c = active[0]
            my_active = f"{c.get('name', c.get('id'))} {c.get('hp')}/{c.get('maxHp')}"
    opp_idx = 1 - root_player
    if len(players) > opp_idx:
        opp = players[opp_idx]
        opp_p = str(len(opp.get("prize") or []))
        active = opp.get("active") or []
        if active and active[0] is not None:
            c = active[0]
            opp_active = f"{c.get('name', c.get('id'))} {c.get('hp')}/{c.get('maxHp')}"
    result = current.get("result", -1)
    turn = current.get("turn", "?")
    return (
        f"turn={turn} result={result} prizes={my_p}/{opp_p} "
        f"active={my_active} vs {opp_active}"
    )


def format_turn_lines(
    lines: list[TurnLine],
    root_player: int,
    *,
    max_lines: int = 40,
    score_fn: ScoreFn = score_line,
) -> list[str]:
    """Human-readable dump of BFS end states, best-first per ``score_fn``."""
    if not lines:
        return ["  (no end states)"]
    ranked = sorted(lines, key=lambda line: score_fn(line, root_player), reverse=True)
    out: list[str] = [
        f"  turn_bfs: {len(lines)} end state(s) (showing top {min(len(ranked), max_lines)})"
    ]
    for i, line in enumerate(ranked[:max_lines]):
        score = score_fn(line, root_player)
        acts = " > ".join(str(a) for a in line.actions) if line.actions else "(no actions)"
        out.append(
            f"  [{i}] {line.terminal:8s} score={score} actions={acts} | "
            f"{_end_state_summary(line, root_player)}"
        )
    if len(ranked) > max_lines:
        out.append(f"  ... +{len(ranked) - max_lines} more")
    return out


# --- Generic search entry point ------------------------------------------------

# Hard caps for ``search`` (not lethal-gated).
TURN_BFS_MAX_NODES = 800
TURN_BFS_MAX_DEPTH = 20
TURN_BFS_BEAM = 48
TURN_BFS_MIN_OVERAGE_TIME = 30.0


def search_time_ok(obs: Observation, min_overage: float = TURN_BFS_MIN_OVERAGE_TIME) -> bool:
    """Bail out of native search when the episode overage budget is tight."""
    remaining = obs.get("remainingOverageTime")
    if remaining is None:
        return True
    try:
        return float(remaining) > min_overage
    except (TypeError, ValueError):
        return True


def _known_prize_ids(state: object) -> list[CardId] | None:
    """Best-effort extraction of deduced-prized card ids from a ruleset's
    state, if it happens to expose a ``deck_memory``-shaped attribute --
    entries with ``.id``/``.prized`` -- e.g. ``DragapultState.deck_memory``.
    Returns ``None`` (falls back to a fully random prize guess) if the state
    has no such attribute, or its shape doesn't match what's expected;
    duck-typed rather than importing ``DragapultState`` so this module
    stays usable by any ruleset's state, not just Dragapult's."""
    deck_memory = getattr(state, "deck_memory", None)
    if not deck_memory:
        return None
    try:
        return [entry.id for entry in deck_memory if getattr(entry, "prized", False)]
    except (AttributeError, TypeError):
        return None


def search(
    ctx: Ctx,
    score_fn: ScoreFn = score_line,
    *,
    max_nodes: int = TURN_BFS_MAX_NODES,
    max_depth: int = TURN_BFS_MAX_DEPTH,
    beam: int = TURN_BFS_BEAM,
) -> list[int] | None:
    """Generic search entry point: given one decision (``ctx``) and a scorer
    (``score_fn``), run the budgeted end-of-turn BFS and return the chosen
    action -- ``list[int]`` option indices for *this* decision, or ``None``
    if search doesn't apply or couldn't decide (wrong phase, no engine, no
    time budget left, no usable deck, or every line came back empty/error).

    This is the one thing any decisionmaking engine needs to call to use
    search: hand it a plain ``ctx`` and a scorer, get back the same shape of
    answer every hand-written ``Heuristic`` gives -- so it can be called
    directly from inline logic (e.g. "if close to lethal, try search with a
    win-focused scorer, otherwise defer to normal heuristics") without
    registering a whole ``Ruleset`` entry. ``make_turn_bfs_search`` below is
    a thin convenience wrapper for the one case that *does* need a plain
    ``Heuristic``-shaped (single-argument) callable -- a ``Ruleset``'s
    ``rules`` list.

    Runs on Main when ``search_begin_input`` is present and overage time
    allows. Explores under node/depth/beam caps with the tactical candidate
    policy, scores every leaf with ``score_fn``, and returns the first
    action of the best line.

    With ``play -v``, dumps the ranked list of end states after each search.

    Deck composition is taken from ``ctx.state.my_deck`` (populated by
    ``admin.build_agent`` when it constructs each game's state -- see
    ``admin._init_state``). Read via ``getattr`` rather than a typed
    ``ctx.state`` access -- this module deliberately doesn't import
    anything from ``pokemon.heuristics`` (e.g. ``DragapultState``), so it
    stays usable by any future ruleset's state, not just Dragapult's, and
    to avoid a circular import (``pokemon.heuristics`` registers
    ``turn_bfs_search``, so it can't also be a dependency of this module).
    If the active state has no ``my_deck`` attribute, search is skipped
    rather than guessing a list.

    If the active state also exposes a ``deck_memory``-shaped attribute
    (entries with ``.id``/``.prized``, e.g. ``DragapultState.deck_memory``,
    populated by ``prize_check`` -- see ``pokemon.heuristics.dragapult``),
    the deduced prized card ids feed into the hidden-zone determinization
    (``sample_determinization``'s ``known_prize_ids``) instead of a fully
    random guess at which unseen cards are prized. That in turn makes the
    *rest* of our own deck's composition -- what Poke Pad/Buddy-Buddy
    Poffin/etc. could actually find -- correspondingly more accurate, once
    a search card has revealed enough to resolve some prizes. Same
    duck-typed, no-``pokemon.heuristics``-import approach as ``my_deck``.
    """
    if ctx.sel_type not in (SelectType.MAIN, 0):
        return None
    if not ctx.obs.get("search_begin_input"):
        return None
    if not search_time_ok(ctx.obs):
        return None
    deck = getattr(ctx.state, "my_deck", None)
    if deck is None or len(deck) != 60:
        _log(f"\n--- Turn {ctx.turn} BFS: no my_deck on state, skip ---")
        return None

    config = sample_determinization(
        ctx.obs, deck, known_prize_ids=_known_prize_ids(ctx.state)
    )
    lines = expand_end_of_turn(
        ctx.obs,
        deck,
        policy="tactical",
        max_nodes=max_nodes,
        max_depth=max_depth,
        beam=beam,
        config=config,
    )
    root = root_player_index(ctx.obs)
    if not lines:
        _log(f"\n--- Turn {ctx.turn} BFS: no end states ---")
        return None

    for msg in format_turn_lines(lines, root, score_fn=score_fn):
        _log(msg)

    best = first_action_of_best_line(lines, root, score_fn=score_fn)
    usable = [line for line in lines if line.actions and line.terminal != "error"]
    if usable and best is not None:
        top = max(usable, key=lambda line: score_fn(line, root))
        first_labels = []
        for idx in best:
            if 0 <= idx < len(ctx.options):
                first_labels.append(format_option(ctx.options[idx], ctx.hand))
            else:
                first_labels.append(f"opt[{idx}]")
        _log(
            f"  pick first action of best line "
            f"({top.terminal}, score={score_fn(top, root)}): "
            f"{', '.join(first_labels) or best}"
        )
    return best


def make_turn_bfs_search(
    score_fn: ScoreFn = score_line,
    *,
    max_nodes: int = TURN_BFS_MAX_NODES,
    max_depth: int = TURN_BFS_MAX_DEPTH,
    beam: int = TURN_BFS_BEAM,
) -> Callable[[Ctx], list[int] | None]:
    """Wrap ``search`` as a plain ``Heuristic`` (``Callable[[Ctx], list[int] | None]``)
    for registering as a ``Ruleset``'s rule -- all this adds over calling
    ``search`` directly is currying ``score_fn``/the budget knobs so the
    result matches the one-argument shape a ``Ruleset.rules`` list needs.

    ..  code-block:: python

        def my_score(line: TurnLine, root_player: int) -> tuple:
            # e.g. maximize damage dealt, ignore prizes entirely
            if line.end_obs is None:
                return (0,)
            players = (line.end_obs.get("current") or {}).get("players") or []
            opp = players[1 - root_player] if len(players) > 1 - root_player else {}
            active = (opp.get("active") or [None])[0] or {}
            hp, max_hp = active.get("hp"), active.get("maxHp")
            dmg = int(max_hp) - int(hp) if hp is not None and max_hp is not None else 0
            return (dmg,)

        my_rule = make_turn_bfs_search(score_fn=my_score)
        RULESETS["my_ruleset"] = Ruleset(rules=[my_rule, *DRAGAPULT_HEURISTICS], init_state=_dragapult_init_state)
    """

    def _rule(ctx: Ctx) -> list[int] | None:
        return search(ctx, score_fn, max_nodes=max_nodes, max_depth=max_depth, beam=beam)

    return _rule


# The default-configured instance -- what ``RULESETS["dragapult_search"]``
# actually registers. Build your own via ``make_turn_bfs_search(score_fn=...)``
# for a custom objective, or call ``search(ctx, score_fn)`` directly for
# inline use; see their docstrings.
turn_bfs_search = make_turn_bfs_search()
