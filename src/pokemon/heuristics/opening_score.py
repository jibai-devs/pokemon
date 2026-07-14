"""Custom search objective for our own first turn (whichever side we're on).

Translates ``deck/guidelines_for_first turn.txt``'s stated priorities into a
scorable end-of-turn objective for ``pokemon.search_function.search`` --
deliberately *not* a line-by-line port of that file's procedural
if/then/else script (which item to play in what order, etc.). The whole
point of using search here is that it already explores the option tree
itself; this only judges which resulting board state best matches the
guideline's goals, and lets the BFS find its own way there.

Judgment calls made translating prose into a strict, lexicographically
ordered tuple (documented on ``opening_turn_score`` itself): the guideline
states "put as many dreepys as you can... but also make sure you have a
good 2nd turn" as one combined goal. A tuple can't express "maximize both
under a soft tradeoff" -- it orders things strictly. Treated "make sure you
have a good 2nd turn" as the higher-priority constraint (the guideline's
own wording -- "make sure" reads as a gate) and Dreepy count as what to
maximize under it, not the other way around. Revisit this ordering if
real games show it under- or over-weighting either goal.
"""

from pokemon.heuristics.dragapult import (
    BUDEW,
    BUDDY_BUDDY_POFFIN,
    DRAKLOAK,
    DREEPY,
    JUDGE,
    LILLIES_DETERMINATION,
    MUNKIDORI,
    POKE_PAD,
    ULTRA_BALL,
)
from pokemon.search_function import TurnLine
from pokemon.types import CardState

_TERM_RANK = {
    "win": 5,
    "eot": 3,
    "budget": 2,
    "depth": 2,
    "draw": 1,
    "opp_choice": 1,
    "loss": 0,
    "error": -1,
}


def _card_ids(cards: list[CardState] | None) -> set[int]:
    return {c.get("id") for c in (cards or []) if c and c.get("id") is not None}


def _energy_count(card: CardState | None) -> int:
    return len((card or {}).get("energyCards") or [])


def opening_turn_score(line: TurnLine, root_player: int) -> tuple:
    """Higher is better. Judges the board state at the end of our first
    turn against ``deck/guidelines_for_first turn.txt``'s priorities:

    1. game result safety net (win/loss/draw) -- same convention as
       ``score_line``; shouldn't matter turn 1, kept for consistency
    2. "Good second turn" -- the guideline's own
       ``<GOOD SECOND TURN IF I DO CURRENT ACTION>`` check, approximated
       from the resulting hand (Drakloak already in hand to evolve into,
       or Lillie's Determination/Judge in hand to keep drawing toward one)
       rather than re-simulating turn 2 itself
    3. Dreepy count in play (active + bench), capped at 3 -- "put as many
       dreepys as you can on the bench, up to 3"
    4. Energy actually attached to a Dreepy/Munkidori this turn -- the
       guideline's energy-attach priority, for both starting-order variants
    5. Budew in the Active slot -- only really scores when going second
       (the Itchy Pollen route); harmless no-op when going first, since a
       first-turn Budew in Active isn't part of that guideline's plan
    6. Dead-hand avoidance -- penalize a near-empty hand with no path to a
       good turn 2 (the guideline's own "will I be put in a dead end" check)
    7. Item-priority proxy -- penalize spending Ultra Ball (lowest priority
       per "buddy-buddy poffin > poke pad > ultra ball") while a
       higher-priority item sat unused in hand instead
    8. shorter action sequences, tie-break (same convention as ``score_line``)
    """
    if line.end_obs is None:
        return (0, 0, 0, 0, 0, 0, 0, -len(line.actions))

    term_rank = _TERM_RANK.get(line.terminal, 0)

    current = line.end_obs.get("current") or {}
    players = current.get("players") or []
    me = players[root_player] if len(players) > root_player else {}

    active = me.get("active") or []
    active_card = active[0] if active else None
    bench = me.get("bench") or []
    board = ([active_card] if active_card else []) + bench

    hand = me.get("hand") or []
    hand_ids = _card_ids(hand)
    good_second_turn = bool(
        DRAKLOAK in hand_ids or LILLIES_DETERMINATION in hand_ids or JUDGE in hand_ids
    )
    good_second_turn_score = 1 if good_second_turn else 0

    dreepy_count = sum(1 for c in board if c and c.get("id") == DREEPY)
    dreepy_score = min(dreepy_count, 3)

    energy_progress_score = 1 if any(
        c.get("id") in (DREEPY, MUNKIDORI) and _energy_count(c) > 0 for c in board
    ) else 0

    budew_active_score = 1 if active_card and active_card.get("id") == BUDEW else 0

    dead_hand_penalty = 0 if (len(hand) > 1 or good_second_turn) else -1

    discard_ids = _card_ids(me.get("discard"))
    wasted_ultra_ball = ULTRA_BALL in discard_ids and (
        BUDDY_BUDDY_POFFIN in hand_ids or POKE_PAD in hand_ids
    )
    item_priority_penalty = -1 if wasted_ultra_ball else 0

    return (
        term_rank,
        good_second_turn_score,
        dreepy_score,
        energy_progress_score,
        budew_active_score,
        dead_hand_penalty,
        item_priority_penalty,
        -len(line.actions),
    )
