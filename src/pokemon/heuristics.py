"""Modular heuristic agent.

Each heuristic is a small, independent function: given the current decision
context, return the chosen option index/indices, or ``None`` if it doesn't
apply. ``make_heuristic_agent`` tries each heuristic in priority order and
falls back to a random legal choice if none fire — so a bug or gap in one
heuristic can never crash a game, only under-perform.

This module encodes the Psychic deck's actual strategy (see
``deck/001_psychic_deck.md``): Slowking's Seek Inspiration discards the top
deck card and, if it's a non-Rule-Box Pokemon, copies one of its attacks for
free. Metagross/Kyurem/Zeraora exist purely as high-damage discard fodder for
that attack; Ciphermaniac's Codebreaking and Academy at Night make the
"random" discard deliberate; Mega Kangaskhan ex/Latias ex are the backup plan.

Some heuristics (marked below) depend on ``select.deck`` / ``select.contextCard``
field shapes that `docs/000_plan_engine_enum_extraction.md` hasn't empirically
verified yet (its Phase 2) — they're best-effort and degrade to "doesn't
apply" (returning ``None``) rather than guessing wrong.
"""

import random
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pokemon.cabt_enums import AreaType, OptionType, SelectContext
from pokemon.catalog import format_option, min_attack_energy_cost
from pokemon.decks import deck_summary

# --- Psychic deck card IDs (see deck/001_psychic_deck_reference.md) ---------

SLOWPOKE = 162
SLOWKING = 163
MEGA_KANGASKHAN_EX = 756
LATIAS_EX = 184
KYUREM = 144
METAGROSS = 276
ZERAORA = 956

ATK_SEEK_INSPIRATION = 213  # Slowking: discard top deck card, copy its attack

# Discard fodder — non-Rule-Box attackers worth stacking on TOP of the deck
# (Ciphermaniac's Codebreaking / Academy at Night) right before a Seek
# Inspiration swing, per real-play advice: the play is to put Metagross or
# Kyurem on top, *then* attack with Seek Inspiration so the discard-and-copy
# is deliberate instead of random. Ordered by how good a copy target they are.
FODDER_TARGETS = [METAGROSS, KYUREM, ZERAORA]

# Engine pieces worth pulling into HAND (Ultra Ball / Poke Pad) — the
# opposite priority from FODDER_TARGETS: Metagross/Kyurem/Zeraora are only
# useful to Seek Inspiration while they're still *in the deck*, so a hand
# search should never spend itself fetching them. Ordered by priority.
ENGINE_TARGETS = [SLOWKING, SLOWPOKE]

# Kept for anything that genuinely doesn't care which of the two roles a
# card fills (e.g. a context that just needs "a legal non-Rule-Box target").
PREFERRED_SEARCH_TARGETS = FODDER_TARGETS + ENGINE_TARGETS

# Backup attackers/mobility plan if Slowking is disrupted.
BACKUP_ATTACKERS = {MEGA_KANGASKHAN_EX, LATIAS_EX}

# Deck-stacking pieces: make Seek Inspiration's "random" discard deliberate.
SETUP_PIECES = {1188, 1248}  # Ciphermaniac's Codebreaking, Academy at Night

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
    through for future heuristics but no current heuristic branches on it —
    they gate on ``sel_context`` instead, which is the actual disambiguator
    per the engine's enum reference.
    """

    obs: dict
    select: dict
    options: list[dict]
    sel_type: int | None
    sel_context: int | None
    hand: list[dict]
    me: dict
    current: dict


def _build_ctx(obs: dict) -> Ctx:
    select = obs["select"]
    current = obs.get("current", {})
    my_idx = current.get("yourIndex", 0)
    players = current.get("players", [])
    me = players[my_idx] if my_idx < len(players) else {}
    return Ctx(
        obs=obs,
        select=select,
        options=select.get("option") or [],
        sel_type=select.get("type"),
        sel_context=select.get("context"),
        hand=me.get("hand") or [],
        me=me,
        current=current,
    )


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
    ``select.deck`` list. An earlier version checked ``select.deck`` first,
    keyed by the option's position in the option list — that let an
    unrelated ``deck`` entry override a perfectly resolvable "play Latias ex
    from hand" option, picking the wrong card in a real playtest. For
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


# --- Heuristics, in priority order -----------------------------------------


def prefer_seek_inspiration(ctx: Ctx) -> list[int] | None:
    """Fire the win condition: use Seek Inspiration over any other attack."""
    for i, opt in enumerate(ctx.options):
        if opt.get("type") == OptionType.ATTACK and opt.get("attackId") == ATK_SEEK_INSPIRATION:
            return [i]
    return None


def evolve_into_slowking(ctx: Ctx) -> list[int] | None:
    """Evolve Slowpoke into Slowking whenever possible — it's this deck's only
    evolution line and the card the whole strategy runs through."""
    for i, opt in enumerate(ctx.options):
        if opt.get("type") != OptionType.EVOLVE:
            continue
        if opt.get("area") != AreaType.HAND:
            continue
        card = _hand_card(ctx, opt.get("index"))
        if card and card.get("id") == SLOWKING:
            return [i]
    return None


def attach_energy_to_attacker(ctx: Ctx) -> list[int] | None:
    """Feed Slowking to its attack threshold first — it's the deck's actual
    win condition — then feed whichever Pokemon is *actually active*, so
    energy doesn't get stranded on a benched Pokemon that can't use it.

    An earlier version ("attach_energy_to_slowking") always targeted
    Slowking regardless of board position. Real-game evidence (PKM-019's
    ``data/recent_log.txt`` audit) showed this stranding energy: Slowking
    got 6 separate attachments over one game while sitting on the bench the
    entire time (nothing switched it back into active — see
    ``switch_to_backup_attacker``'s fix below), while whichever backup
    attacker *was* active sat at 1 energy all game, well under its actual
    attack cost (Mega Kangaskhan ex/Latias ex both need 3). Zero attacks
    fired the whole game as a result. Once Slowking has enough energy to
    attack, further energy sent its way while benched is equally wasted —
    better spent getting the current active Pokemon to *its* threshold.
    """
    slowking_cap = min_attack_energy_cost(SLOWKING) or 2
    for i, opt in enumerate(ctx.options):
        if opt.get("type") != OptionType.ATTACH:
            continue
        target = _board_card(ctx, opt.get("inPlayArea"), opt.get("inPlayIndex"))
        if target and target.get("id") == SLOWKING and len(target.get("energies") or []) < slowking_cap:
            return [i]

    active = _active_card(ctx)
    active_id = active.get("id") if active else None
    active_cap = min_attack_energy_cost(active_id) if active_id is not None else None
    fallback = None
    if active_id is not None and active_cap is not None:
        for i, opt in enumerate(ctx.options):
            if opt.get("type") != OptionType.ATTACH:
                continue
            target = _board_card(ctx, opt.get("inPlayArea"), opt.get("inPlayIndex"))
            if not target or target.get("id") != active_id:
                continue
            if len(target.get("energies") or []) < active_cap:
                return [i]
            fallback = fallback if fallback is not None else i
    return [fallback] if fallback is not None else None


def play_setup_pieces(ctx: Ctx) -> list[int] | None:
    """Prioritize Ciphermaniac's Codebreaking / Academy at Night — these stack
    the deck so Seek Inspiration's discard isn't left to chance."""
    for i, opt in enumerate(ctx.options):
        if opt.get("type") != OptionType.PLAY:
            continue
        card = _hand_card(ctx, opt.get("index"))
        if card and card.get("id") in SETUP_PIECES:
            return [i]
    return None


def setup_active_prefers_slowking_line(ctx: Ctx) -> list[int] | None:
    """At setup, lead with Slowpoke/Slowking to get the engine online early."""
    if ctx.sel_context != SelectContext.SETUP_ACTIVE_POKEMON:
        return None
    for i, opt in enumerate(ctx.options):
        cid = _option_card_id(ctx, opt)
        if cid in (SLOWKING, SLOWPOKE):
            return [i]
    return None


def switch_to_backup_attacker(ctx: Ctx) -> list[int] | None:
    """When choosing a new active Pokemon (retreat/switch/forced), prefer
    Slowking if it's already loaded enough to attack — it's the deck's
    actual win condition, not the backup plan — and only fall back to the
    backup attackers (Mega Kangaskhan ex / Latias ex) when Slowking isn't
    ready.

    Before this fix there was no heuristic that ever switched Slowking back
    into active once it left: this one unconditionally preferred the backup
    attackers on every switch decision, and ``setup_active_prefers_slowking_
    line`` only covers the initial SETUP_ACTIVE_POKEMON pick, not later
    switches. Real-game evidence (PKM-019's ``data/recent_log.txt`` audit):
    Slowking accumulated 6 energy attachments over one game but was never
    once switched back into active, while the backup attackers (parked
    active the entire game) never reached their own 3-energy attack cost
    either — zero attacks fired all game.
    """
    if ctx.sel_context not in (SelectContext.SWITCH, SelectContext.TO_ACTIVE):
        return None
    slowking_cap = min_attack_energy_cost(SLOWKING) or 2
    for i, opt in enumerate(ctx.options):
        if _option_card_id(ctx, opt) != SLOWKING:
            continue
        card = _board_card(ctx, opt.get("area"), opt.get("index"))
        if card and len(card.get("energies") or []) >= slowking_cap:
            return [i]
    for i, opt in enumerate(ctx.options):
        if _option_card_id(ctx, opt) in BACKUP_ATTACKERS:
            return [i]
    return None


def retreat_when_slowking_endangered(ctx: Ctx) -> list[int] | None:
    """Retreat Slowking to the backup plan when it's about to die, rather than
    risk losing the whole Seek Inspiration engine to a KO."""
    active = _active_card(ctx)
    if not active or active.get("id") != SLOWKING or not active.get("maxHp"):
        return None
    if active["hp"] / active["maxHp"] > 0.35:
        return None
    for i, opt in enumerate(ctx.options):
        if opt.get("type") == OptionType.RETREAT:
            return [i]
    return None


def _rank_and_pick(ctx: Ctx, targets: list[int]) -> list[int] | None:
    """Rank options whose resolved card is in ``targets`` (best-first) and
    return the top ``maxCount`` of them, or ``None`` if there aren't enough
    confident picks to fill the required count.

    Must return exactly ``select["maxCount"]`` indices — e.g. Ciphermaniac's
    Codebreaking searches for *2* cards in one selection. Returning fewer
    than required is an invalid action; a real playtest showed the engine
    silently ending the episode as a draw (no exception, no error message)
    the first time this returned only 1 index for a 2-card select. If there
    aren't enough confident picks to fill the required count, defer to
    random entirely rather than submit a partial selection.
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


def prefer_copy_fodder_targets(ctx: Ctx) -> list[int] | None:
    """When placing cards on TOP of the deck (Ciphermaniac's Codebreaking,
    Academy at Night), prefer Metagross/Kyurem/Zeraora — the only legal,
    non-Rule-Box Seek Inspiration copy targets.

    This is the deliberate half of the strategy a real-play pro described:
    stack Metagross or Kyurem on top of the deck, *then* swing with Seek
    Inspiration, so the discard-and-copy is a guaranteed hit instead of
    whatever happens to be on top. Restricted to ``TO_DECK`` only — not
    ``TO_HAND`` (that's the opposite goal, see ``prefer_engine_targets_to_
    hand``) and not ``TO_DECK_BOTTOM`` (burying fodder at the bottom is the
    one placement that helps nothing; better to defer to random there than
    actively aim fodder at the wrong end of the deck).
    """
    if ctx.sel_context != SelectContext.TO_DECK:
        return None
    return _rank_and_pick(ctx, FODDER_TARGETS)


def prefer_engine_targets_to_hand(ctx: Ctx) -> list[int] | None:
    """When searching a card into HAND (Ultra Ball, Poke Pad), prefer
    Slowking/Slowpoke — the pieces that actually need to reach hand to get
    the Seek Inspiration engine online.

    Deliberately excludes Metagross/Kyurem/Zeraora: their entire value is
    sitting in the deck as discard fodder for Seek Inspiration (see
    ``prefer_copy_fodder_targets``) — pulling them into hand instead removes
    them from the deck and can never be discard-and-copied again. An earlier
    version of this heuristic ranked fodder ahead of engine pieces for every
    search context, which meant Ultra Ball/Poke Pad kept spending themselves
    fetching Metagross/Kyurem into hand instead of finishing the Slowpoke ->
    Slowking line, or leaving fodder in the deck where Seek Inspiration could
    actually use it.
    """
    if ctx.sel_context != SelectContext.TO_HAND:
        return None
    return _rank_and_pick(ctx, ENGINE_TARGETS)


DEFAULT_PSYCHIC_HEURISTICS: list[Heuristic] = [
    prefer_seek_inspiration,
    evolve_into_slowking,
    attach_energy_to_attacker,
    play_setup_pieces,
    setup_active_prefers_slowking_line,
    switch_to_backup_attacker,
    retreat_when_slowking_endangered,
    prefer_copy_fodder_targets,
    prefer_engine_targets_to_hand,
]

# Per-deck heuristic sets, mirroring pokemon.decks.DECKS.
HEURISTIC_SETS: dict[str, list[Heuristic]] = {"psychic": DEFAULT_PSYCHIC_HEURISTICS}


def make_heuristic_agent(
    deck: list[int], heuristics: list[Heuristic] | None = None
) -> Callable[[dict], list[int]]:
    """Build an agent that applies ``heuristics`` in order, falling back to a
    random legal choice when none of them apply to the current decision."""
    rules = heuristics if heuristics is not None else DEFAULT_PSYCHIC_HEURISTICS

    def play(obs: dict) -> list[int]:
        if obs["select"] is None:
            lines, checksum = deck_summary(deck)
            _log(f"\n{'=' * 60}")
            _log(f"GAME {_game_num}: Submitting deck ({len(deck)} cards, sha256:{checksum}) [heuristic]")
            _log(f"{'=' * 60}")
            if _game_num <= 1:
                for line in lines:
                    _log(line)
            return deck

        ctx = _build_ctx(obs)
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
            # multi-select (Ciphermaniac's Codebreaking's "search 2 cards").
            # Treat that as "this heuristic doesn't apply" rather than submit it.
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
