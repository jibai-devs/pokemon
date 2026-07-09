"""Dragapult ex ("Pult Noir") deck-specific heuristics — PKM-017/007.

Built against `docs/007_heuristics_logic_plan.md` (v2) and
`docs/dragapult_deck_explanation.md` (v3). Tiers below mirror the plan's
Tier 1-5 ladder; the ordering in ``DRAGAPULT_HEURISTICS`` at the bottom *is*
the priority order (first-match-wins, per ``make_heuristic_agent``).

Several fields this module reads (``energyCards``, ``hp``/``maxHp``,
``inPlayArea``/``inPlayIndex`` on ATTACH options) come from the real Kaggle
replay shape (see `example_replay.json`) but haven't been empirically
verified against the *local* engine's option dicts (Phase 2 of
`docs/000_plan_engine_enum_extraction.md`). Every rule here is written to
degrade to "doesn't apply" (``None``) rather than guess wrong, per that
plan's own convention.

Tier 5 (matchup overrides) is deliberately implemented as one mechanism —
archetype-signature latch + a per-archetype priority-target list — reused by
the Tier 4 targeting rules, rather than ten fully bespoke functions. This
captures the concrete, codifiable part of Section 8 (who to target first)
without engine support for things like hand-content deduction (Judge) or
full stadium-interaction awareness (Battle Cage) — those stay judgment calls
left to the random fallback, as the plan intends for genuinely discretionary
decisions.
"""

from collections import Counter

from pokemon.cabt_enums import AreaType, EnergyType, OptionType, SelectContext, SelectType
from pokemon.catalog import attack_info, card_info
from pokemon.heuristics import (
    Ctx,
    Heuristic,
    _hand_card,
    _option_card_id,
    _rank_and_pick,
    active_card,
    all_pokemon,
    bench_cards,
    energy_cards,
    energy_count,
    max_hp,
    remaining_hp,
)

# --- Card ids (pokemon.decks.DRAGAPULT_DECK) --------------------------------

DREEPY = 119
DRAKLOAK = 120
DRAGAPULT_EX = 121
MUNKIDORI = 112
BUDEW = 235
MOLTRES = 791
FEZANDIPITI_EX = 140
MEOWTH_EX = 1071
LILLIES_DETERMINATION = 1227
CRISPIN = 1198
BOSS_ORDERS = 1182
JUDGE = 1213
CRUSHING_HAMMER = 1120
BUDDY_BUDDY_POFFIN = 1086
POKE_PAD = 1152
ULTRA_BALL = 1121
NIGHT_STRETCHER = 1097
UNFAIR_STAMP = 1080
RISKY_RUINS = 1260
WATCHTOWER = 1256
XEROSIC = 1197
FIRE_ENERGY = 2
PSYCHIC_ENERGY = 5
DARKNESS_ENERGY = 7

_ENERGY_CARD_TYPE = {
    FIRE_ENERGY: EnergyType.FIRE,
    PSYCHIC_ENERGY: EnergyType.PSYCHIC,
    DARKNESS_ENERGY: EnergyType.DARKNESS,
}


# --- Small card-database helpers --------------------------------------------


def is_basic(card_id: int | None) -> bool:
    info = card_info(card_id)
    return bool(info) and info.get("basic", False)


def is_ex(card_id: int | None) -> bool:
    info = card_info(card_id)
    return bool(info) and info.get("ex", False)


def attached_energy_types(card: dict | None) -> list[EnergyType]:
    types: list[EnergyType] = []
    for e in energy_cards(card):
        cid = e.get("id")
        if isinstance(cid, int):
            t = _ENERGY_CARD_TYPE.get(cid)
            if t is not None:
                types.append(t)
    return types


def can_pay_cost(attached: list[EnergyType], cost: list[int]) -> bool:
    need = Counter(EnergyType(t) for t in cost if t != EnergyType.COLORLESS)
    n_colorless = sum(1 for t in cost if t == EnergyType.COLORLESS)
    have = Counter(attached)
    for t, n in need.items():
        if have.get(t, 0) < n:
            return False
        have[t] -= n
    return sum(v for v in have.values() if v > 0) >= n_colorless


def can_attack_now(card: dict | None) -> bool:
    """Whether ``card`` has enough attached energy to pay for at least one
    of its own attacks right now."""
    if not card:
        return False
    info = card_info(card.get("id"))
    if not info:
        return False
    types = attached_energy_types(card)
    for aid in info.get("attacks") or []:
        atk = attack_info(aid)
        if atk and can_pay_cost(types, atk.get("energies") or []):
            return True
    return False


def best_attack_damage(card: dict | None) -> int:
    """Highest damage among attacks ``card`` can currently pay for, 0 if none."""
    if not card:
        return 0
    info = card_info(card.get("id"))
    if not info:
        return 0
    types = attached_energy_types(card)
    best = 0
    for aid in info.get("attacks") or []:
        atk = attack_info(aid)
        if atk and can_pay_cost(types, atk.get("energies") or []):
            best = max(best, atk.get("damage", 0))
    return best


def _hand_option_card_id(ctx: Ctx, opt: dict) -> int | None:
    """Card id for a PLAY(7)/DISCARD(11)-shaped option, both of which index
    into hand (per `AGENTS.md`'s OptionType table) rather than the
    CARD/TOOL_CARD/ENERGY_CARD shapes `_option_card_id` handles — that
    function returns ``None`` for these types by design, so it can't be
    reused here. Defaults a missing ``area`` to HAND (PLAY never carries one);
    an explicit non-HAND ``area`` degrades to ``None`` rather than guessing.
    """
    area = opt.get("area", AreaType.HAND)
    if area != AreaType.HAND:
        return None
    card = _hand_card(ctx, opt.get("index"))
    return card.get("id") if card else None


def _resolve_side_card(ctx: Ctx, opt: dict) -> tuple[dict | None, bool]:
    """Resolve a CARD-shaped option's target card, returning ``(card, is_mine)``.

    Real replays show each such option carries an explicit ``playerIndex``
    (PKM-019 batch analysis) identifying whose board ``area``/``index``
    refers to -- a plain SWITCH decision can resolve to either side (our own
    voluntary retreat, or Boss's Orders forcing a pick on the opponent's
    board) depending on who's actually being made to choose, and a prior
    version of this function always assumed the opponent, which made it
    evaluate our own bench as if it were the opponent's whenever the two
    benches differed in size (silently dropping/misassigning candidates).
    When ``playerIndex`` is absent, defaults to the opponent -- this
    function's original, narrower scope (Boss's Orders / Phantom Dive
    always target the opponent, and some call sites' options don't carry
    the field).
    """
    area = opt.get("area")
    idx = opt.get("index")
    if idx is None:
        return None, False
    player_idx = opt.get("playerIndex")
    my_idx = ctx.current.get("yourIndex", 0)
    is_mine = player_idx == my_idx if player_idx is not None else False
    side = ctx.me if is_mine else ctx.opp
    if area == AreaType.ACTIVE:
        return active_card(side), is_mine
    if area == AreaType.BENCH:
        bench = bench_cards(side)
        return (bench[idx] if 0 <= idx < len(bench) else None), is_mine
    return None, is_mine


# --- Tier 5 — archetype signature table -------------------------------------
#
# Detection: any opponent Pokemon/Stadium name seen so far this game (played
# to bench/active, discarded, or in the Stadium slot) latches the matchup
# identity for the rest of the game (plan's Tier 5 design). "mirror" is
# checked last since "Dragapult ex" is the least distinctive signature.

TIER5_SIGNATURES: dict[str, list[str]] = {
    "arboliva": ["Arboliva ex", "Dolliv", "Smoliv"],
    "alakazam": ["Alakazam", "Kadabra", "Dudunsparce"],
    "mega_lucario": ["Mega Lucario ex", "Riolu"],
    "n_zoroark": ["N's Zoroark ex", "Pecharunt ex"],
    "cynthia_garchomp": ["Cynthia's Garchomp ex", "Cynthia's Gabite"],
    "crustle_kangaskhan": ["Crustle", "Mega Kangaskhan ex", "Milotic ex"],
    "grimmsnarl": ["Marnie's Grimmsnarl ex", "Froslass"],
    "mega_starmie": ["Mega Starmie ex", "Mega Froslass ex"],
    "raging_bolt": ["Raging Bolt", "Raging Bolt ex"],
    "mega_box": ["Absol", "Area Zero Underdepths"],
    "mirror": ["Dragapult ex"],
}

# Per Section 8: which opposing Pokemon to prioritize once an archetype is
# latched — the concrete, codifiable half of each matchup write-up.
TIER5_PRIORITY_TARGETS: dict[str, list[str]] = {
    "arboliva": ["Meganium", "Dolliv", "Smoliv"],
    "alakazam": ["Dudunsparce", "Genesect"],
    "mega_lucario": ["Makuhita", "Lunatone", "Solrock", "Mega Lucario ex"],
    "n_zoroark": ["Pecharunt ex", "N's Zoroark ex"],
    "cynthia_garchomp": ["Cynthia's Garchomp ex", "Cynthia's Roserade"],
    "crustle_kangaskhan": ["Milotic ex", "Mega Kangaskhan ex"],
    "grimmsnarl": ["Munkidori", "Froslass"],
    "mega_starmie": ["Munkidori", "Mega Froslass ex"],
    "raging_bolt": ["Teal Mask Ogerpon ex"],
    "mega_box": ["Absol"],
    "mirror": ["Drakloak"],
}

# Section 8 (Crustle/Mega Kangaskhan ex): Mysterious Rock Inn blocks all
# damage from Pokemon-ex attacks entirely.
EX_ATTACK_DENY_TARGETS = {"Crustle"}

# Which of our own attacks come from an ex Pokemon (Phantom Dive, Cruel Arrow).
_EX_ATTACK_IDS = {154, 183}


def archetype_latch(ctx: Ctx) -> list[int] | None:
    """Side-effect-only hook (Tier 5 detection) — always returns ``None``.
    Run first every decision so later rules can read ``ctx.state["archetype"]``."""
    if ctx.state.get("archetype"):
        return None
    seen_names: set[str] = set()
    for c in all_pokemon(ctx.opp):
        if c.get("name"):
            seen_names.add(c["name"])
    for c in ctx.opp.get("discard") or []:
        if c.get("name"):
            seen_names.add(c["name"])
    for c in ctx.current.get("stadium") or []:
        if c.get("name"):
            seen_names.add(c["name"])
    for archetype, sigs in TIER5_SIGNATURES.items():
        if any(s in seen_names for s in sigs):
            ctx.state["archetype"] = archetype
            break
    return None


# --- Tier 1 — setup phase ----------------------------------------------------

_PRIORITY_FIRST = [BUDEW, MUNKIDORI, DREEPY, FEZANDIPITI_EX, MEOWTH_EX]
_PRIORITY_SECOND = [BUDEW, DREEPY, MUNKIDORI, FEZANDIPITI_EX, MEOWTH_EX]


def setup_pokemon(ctx: Ctx) -> list[int] | None:
    """Section 4 opening-Pokemon priority for SETUP_ACTIVE/SETUP_BENCH selects."""
    if ctx.sel_context not in (SelectContext.SETUP_ACTIVE_POKEMON, SelectContext.SETUP_BENCH_POKEMON):
        return None
    priority = _PRIORITY_FIRST if ctx.going_first is not False else _PRIORITY_SECOND
    return _rank_and_pick(ctx, priority)


# --- Tier 2 — forced/reactive, no discretion --------------------------------


def mulligan(ctx: Ctx) -> list[int] | None:
    """A1: mulligan iff hand has zero Basic Pokemon — deterministic, not strategic."""
    if ctx.sel_context != SelectContext.MULLIGAN or ctx.sel_type != SelectType.YES_NO:
        return None
    has_basic = any(is_basic(c.get("id")) for c in ctx.hand)
    want = OptionType.NO if has_basic else OptionType.YES
    for i, opt in enumerate(ctx.options):
        if opt.get("type") == want:
            return [i]
    return None


def _own_board_tier(ctx: Ctx, card: dict) -> int:
    """A2: priority order when choosing among OUR OWN board for a switch --
    best-ready attacker first, then the Drakloak line, then a Darkness-loaded
    Munkidori, then any non-ex, ex last. Shared by ``active_replacement``
    (forced KO switch) and ``boss_orders_target``'s own-board branch
    (voluntary retreat / forced switch that resolves to our own bench) so
    both use the same tiering rather than duplicating it."""
    cid = card.get("id")
    if cid == DRAGAPULT_EX and can_attack_now(card):
        return 0
    if cid == DRAKLOAK and not ctx.state.get(f"recon_used_{card.get('serial')}_{ctx.turn}"):
        return 1
    if cid == MUNKIDORI and EnergyType.DARKNESS in attached_energy_types(card):
        return 2
    if not is_ex(cid):
        return 3
    return 4


def active_replacement(ctx: Ctx) -> list[int] | None:
    """A2: priority order over legal bench options after a forced KO switch."""
    if ctx.sel_context != SelectContext.TO_ACTIVE:
        return None
    bench = bench_cards(ctx.me)
    candidates = []
    for i, opt in enumerate(ctx.options):
        if opt.get("type") != OptionType.CARD or opt.get("area") != AreaType.BENCH:
            continue
        idx = opt.get("index")
        if idx is None or not (0 <= idx < len(bench)):
            continue
        candidates.append((i, bench[idx]))
    if not candidates:
        return None
    candidates.sort(key=lambda ic: (_own_board_tier(ctx, ic[1]), -(remaining_hp(ic[1]) or 0)))
    return [candidates[0][0]]


# --- Tier 3 — resource management, fires almost every turn ------------------


def watchtower_meowth_sequencing(ctx: Ctx) -> list[int] | None:
    """D1: never let Watchtower go down before Meowth ex's on-play search."""
    ids: dict[int, int] = {}
    for i, opt in enumerate(ctx.options):
        if opt.get("type") != OptionType.PLAY:
            continue
        cid = _hand_option_card_id(ctx, opt)
        if cid is not None:
            ids.setdefault(cid, i)
    if MEOWTH_EX in ids and WATCHTOWER in ids:
        return [ids[MEOWTH_EX]]
    return None


_FUEL_TARGETS = (DREEPY, DRAKLOAK, DRAGAPULT_EX, MUNKIDORI, BUDEW)


def attach_energy(ctx: Ctx) -> list[int] | None:
    """Section B (Munkidori/Darkness routing) + Section 4's energy-attach default."""
    attach_opts = [(i, opt) for i, opt in enumerate(ctx.options) if opt.get("type") == OptionType.ATTACH]
    if not attach_opts:
        return None
    bench = bench_cards(ctx.me)
    active = active_card(ctx.me)

    def target_card(opt: dict) -> dict | None:
        area, idx = opt.get("inPlayArea"), opt.get("inPlayIndex")
        if area == AreaType.ACTIVE:
            return active
        if area == AreaType.BENCH and idx is not None and 0 <= idx < len(bench):
            return bench[idx]
        return None

    def energy_id(opt: dict) -> int | None:
        card = _hand_card(ctx, opt.get("index"))
        return card.get("id") if card else None

    darkness = [(i, target_card(opt)) for i, opt in attach_opts if energy_id(opt) == DARKNESS_ENERGY]
    darkness = [(i, c) for i, c in darkness if c is not None]
    if darkness:
        munkidoris = [(i, c) for i, c in darkness if c.get("id") == MUNKIDORI]
        if not munkidoris:
            return None
        opp_damaged = [t for t in all_pokemon(ctx.opp) if 0 < (remaining_hp(t) or 0) < (max_hp(t) or 0)]
        if not opp_damaged:
            return None  # B1: no near-term Adrena-Brain payoff, defer rather than attach speculatively
        if len(munkidoris) == 1:
            return [munkidoris[0][0]]
        has_payoff = any(0 < (remaining_hp(t) or 999) <= 30 for t in opp_damaged)
        if has_payoff:
            return [munkidoris[0][0]]
        for i, c in munkidoris:
            if c is active:
                return [i]
        return [munkidoris[0][0]]

    fuel = [(i, target_card(opt)) for i, opt in attach_opts if energy_id(opt) in (FIRE_ENERGY, PSYCHIC_ENERGY)]
    fuel = [(i, c) for i, c in fuel if c is not None and c.get("id") in _FUEL_TARGETS]
    if not fuel:
        return None
    unready = [(i, c) for i, c in fuel if not (c.get("id") == DRAGAPULT_EX and energy_count(c) >= 2)]
    if not unready:
        return [fuel[0][0]]
    for i, c in unready:
        if c is active:
            return [i]
    # attacker line first (Dreepy/Drakloak/Dragapult ex); Munkidori needs Psychic
    # for Mind Bend so it's a real payoff, not just a fallback; Budew's only
    # attack is free, so it's last -- attaching there wastes the energy but
    # beats leaving the decision to the random fallback.
    unready.sort(key=lambda ic: (_FUEL_TARGETS.index(ic[1].get("id")), -energy_count(ic[1])))
    return [unready[0][0]]


def _discard_priority(card_id: int | None) -> int:
    """Section 11 — lower means "discard this first" (least costly to lose)."""
    if card_id is None:
        return 50
    if card_id in (BOSS_ORDERS, UNFAIR_STAMP, CRISPIN):
        return 100  # never discard if avoidable
    if card_id in (DRAGAPULT_EX, DRAKLOAK):
        return 90
    if card_id == DREEPY:
        return 80  # avoid, but the least-bad of the attacker line
    if card_id == DARKNESS_ENERGY:
        return 30  # only 2 exist and only Crispin can refetch one
    if card_id in (FIRE_ENERGY, PSYCHIC_ENERGY):
        return 10  # low-risk excess beyond what 2 Phantom Dives need
    if card_id in (BUDEW, MUNKIDORI, MOLTRES, FEZANDIPITI_EX, MEOWTH_EX):
        return 20  # spent non-attacker basics
    if card_id in (BUDDY_BUDDY_POFFIN, POKE_PAD, ULTRA_BALL, NIGHT_STRETCHER):
        return 0  # no discard-recursion value in this deck once played out
    return 40


def discard_sequencing(ctx: Ctx) -> list[int] | None:
    """Options in a DISCARD-context select aren't reliably typed
    ``OptionType.DISCARD`` (observed as generic ``OptionType.CARD`` across
    every discard decision in three logged games, per PKM-019 batch
    analysis) -- ``sel_context`` alone is what disambiguates this select as
    a discard choice, so every option here is a candidate regardless of its
    own ``type``. ``_hand_option_card_id`` already degrades to ``None`` for
    non-HAND-area options (e.g. an attached-card removal choice under
    DISCARD_CARD_OR_ATTACHED_CARD), so those are filtered out below rather
    than by type.
    """
    if ctx.sel_context not in (SelectContext.DISCARD, SelectContext.DISCARD_CARD_OR_ATTACHED_CARD):
        return None
    need = ctx.select.get("maxCount") or 1
    scored = []
    for i, opt in enumerate(ctx.options):
        cid = _hand_option_card_id(ctx, opt)
        if cid is None:
            continue
        scored.append((_discard_priority(cid), i))
    if len(scored) < need:
        return None
    scored.sort()
    return [i for _, i in scored[:need]]


def _boss_orders_has_payoff(ctx: Ctx) -> bool:
    dmg = best_attack_damage(active_card(ctx.me))
    for t in bench_cards(ctx.opp):
        hp = remaining_hp(t)
        if hp is not None and dmg >= hp:
            return True
    return False


def _energy_short(ctx: Ctx) -> bool:
    my_active = active_card(ctx.me)
    if my_active and my_active.get("id") == DRAGAPULT_EX and energy_count(my_active) < 2:
        return True
    return any(
        c.get("id") == MUNKIDORI and EnergyType.DARKNESS not in attached_energy_types(c)
        for c in all_pokemon(ctx.me)
    )


def supporter_tiebreak(ctx: Ctx) -> list[int] | None:
    """A3: default ordering when multiple Supporters are legal and nothing
    matchup-specific applies. Never picks Judge (left to a dedicated
    situational rule or the random fallback)."""
    play_opts = [(i, opt) for i, opt in enumerate(ctx.options) if opt.get("type") == OptionType.PLAY]
    ids: dict[int, int] = {}
    for i, opt in play_opts:
        cid = _hand_option_card_id(ctx, opt)
        if cid in (BOSS_ORDERS, CRISPIN, LILLIES_DETERMINATION, JUDGE):
            ids.setdefault(cid, i)
    if len(ids) < 2:
        return None
    if BOSS_ORDERS in ids and _boss_orders_has_payoff(ctx):
        return [ids[BOSS_ORDERS]]
    if CRISPIN in ids and _energy_short(ctx):
        return [ids[CRISPIN]]
    if LILLIES_DETERMINATION in ids:
        return [ids[LILLIES_DETERMINATION]]
    return None


_LOW_VALUE_BENCH = [DREEPY, BUDEW, MUNKIDORI, MOLTRES]


def bench_play_discretion(ctx: Ctx) -> list[int] | None:
    """D2: don't bench Fezandipiti ex/Meowth ex when a lower-value basic is
    also a legal play this decision."""
    play_opts = [(i, opt) for i, opt in enumerate(ctx.options) if opt.get("type") == OptionType.PLAY]
    candidates = []
    for i, opt in play_opts:
        cid = _hand_option_card_id(ctx, opt)
        if cid is not None and is_basic(cid):
            candidates.append((i, cid))
    if len(candidates) < 2:
        return None
    low = [(i, cid) for i, cid in candidates if cid in _LOW_VALUE_BENCH]
    if not low:
        return None
    low.sort(key=lambda ic: _LOW_VALUE_BENCH.index(ic[1]))
    return [low[0][0]]


def _dreepy_stalled(ctx: Ctx) -> bool:
    """No Dreepy in play or hand -- the deck's evolution line has nothing
    left to build on and needs a fresh one."""
    return not any(c.get("id") == DREEPY for c in all_pokemon(ctx.me)) and not any(
        c.get("id") == DREEPY for c in ctx.hand
    )


def play_search_for_dreepy(ctx: Ctx) -> list[int] | None:
    """No prior heuristic ever valued playing Poke Pad or Night Stretcher, so
    this Main-phase decision fell to whatever else won by default (usually
    Attack/Attach) even when the Dreepy line was stalled and one of these
    was a free search sitting right there (PKM-019, P2). Only overrides the
    default when the line is actually stalled -- otherwise leaves the
    decision to whatever already handles Attack/Attach/Supporters."""
    if not _dreepy_stalled(ctx):
        return None
    ids: dict[int, int] = {}
    for i, opt in enumerate(ctx.options):
        if opt.get("type") != OptionType.PLAY:
            continue
        cid = _hand_option_card_id(ctx, opt)
        if cid is not None:
            ids.setdefault(cid, i)
    if POKE_PAD in ids:
        return [ids[POKE_PAD]]
    if NIGHT_STRETCHER in ids:
        return [ids[NIGHT_STRETCHER]]
    return None


def search_for_dreepy(ctx: Ctx) -> list[int] | None:
    """The ToHand search-target decision that follows PLAY Poke Pad (deck
    search, AreaType.DECK options) or Night Stretcher (discard retrieval,
    AreaType.DISCARD options): pick Dreepy when it's offered and the line is
    stalled. Gated to these two effects specifically (via ``select.effect``)
    rather than any ToHand/DECK search, since other search effects in this
    deck may have different priorities this heuristic isn't confident about."""
    if ctx.sel_context != SelectContext.TO_HAND:
        return None
    effect_id = (ctx.select.get("effect") or {}).get("id")
    if effect_id not in (POKE_PAD, NIGHT_STRETCHER):
        return None
    if not _dreepy_stalled(ctx):
        return None
    discard = ctx.me.get("discard") or []
    for i, opt in enumerate(ctx.options):
        if opt.get("type") != OptionType.CARD:
            continue
        area, idx = opt.get("area"), opt.get("index")
        if idx is None:
            continue
        if area == AreaType.DECK:
            cid = _option_card_id(ctx, opt)
        elif area == AreaType.DISCARD:
            card = discard[idx] if 0 <= idx < len(discard) else None
            cid = card.get("id") if card else None
        else:
            continue
        if cid == DREEPY:
            return [i]
    return None


# --- Tier 4 — attack/targeting, archetype-agnostic --------------------------


def boss_orders_target(ctx: Ctx) -> list[int] | None:
    """Default target for a SWITCH/TO_ACTIVE CARD-shaped decision. Splits by
    which side the options actually resolve to (see ``_resolve_side_card``):
    a decision that resolves to OUR OWN board (voluntary retreat, or a
    forced switch that happens to land on us) uses ``active_replacement``'s
    attacker-priority tiering; a decision that resolves to the OPPONENT's
    board (Boss's Orders, or any effect that forces their pick) uses
    lethal-this-turn first, else the matchup's priority target, else the
    highest-value (ex) benched piece."""
    if ctx.sel_context not in (SelectContext.SWITCH, SelectContext.TO_ACTIVE):
        return None
    mine, theirs = [], []
    for i, opt in enumerate(ctx.options):
        if opt.get("type") != OptionType.CARD:
            continue
        card, is_mine = _resolve_side_card(ctx, opt)
        if card is None:
            continue
        (mine if is_mine else theirs).append((i, card))

    if mine:
        mine.sort(key=lambda ic: (_own_board_tier(ctx, ic[1]), -(remaining_hp(ic[1]) or 0)))
        return [mine[0][0]]

    if not theirs:
        return None
    my_dmg = best_attack_damage(active_card(ctx.me))
    archetype = ctx.state.get("archetype")
    priority_names = TIER5_PRIORITY_TARGETS.get(archetype, []) if isinstance(archetype, str) else []

    def score(item: tuple[int, dict]) -> tuple:
        _, card = item
        hp = remaining_hp(card)
        lethal = hp is not None and my_dmg >= hp
        name = card.get("name")
        pref = priority_names.index(name) if name in priority_names else len(priority_names)
        return (0 if lethal else 1, pref, 0 if is_ex(card.get("id")) else 1, hp if hp is not None else 9999)

    theirs.sort(key=score)
    return [theirs[0][0]]


def bench_spread_target(ctx: Ctx) -> list[int] | None:
    """Default Phantom Dive bench-spread target(s): matchup priority first,
    else whatever's already inside the 60-damage spread's KO range."""
    if ctx.sel_context not in (SelectContext.DAMAGE_COUNTER_ANY, SelectContext.DAMAGE_COUNTER, SelectContext.EFFECT_TARGET):
        return None
    opp_bench = bench_cards(ctx.opp)
    candidates = []
    for i, opt in enumerate(ctx.options):
        if opt.get("type") != OptionType.CARD:
            continue
        card, is_mine = _resolve_side_card(ctx, opt)
        if not is_mine and card is not None and card in opp_bench:
            candidates.append((i, card))
    if not candidates:
        return None
    need = ctx.select.get("maxCount") or 1
    archetype = ctx.state.get("archetype")
    priority_names = TIER5_PRIORITY_TARGETS.get(archetype, []) if isinstance(archetype, str) else []

    def score(item: tuple[int, dict]) -> tuple:
        _, card = item
        hp = remaining_hp(card) or 9999
        name = card.get("name")
        pref = priority_names.index(name) if name in priority_names else len(priority_names)
        return (pref, 0 if hp <= 60 else 1, hp)

    candidates.sort(key=score)
    chosen = [i for i, _ in candidates[:need]]
    return chosen if len(chosen) >= need else None


def evolve_choice(ctx: Ctx) -> list[int] | None:
    """No prior heuristic ever selected an EVOLVE option, so ``attack_choice``
    always won the Main-phase menu when both were legal -- Dreepy/Drakloak
    never evolved into the deck's actual win condition (PKM-019, P1).
    Evolves whenever doing so wouldn't forgo a lethal attack this turn
    (evolving the active Pokemon costs its attack for the turn, so only a
    lethal attack is worth trading away)."""
    evolve_opts = [(i, opt) for i, opt in enumerate(ctx.options) if opt.get("type") == OptionType.EVOLVE]
    if not evolve_opts:
        return None
    attack_opts = [opt for opt in ctx.options if opt.get("type") == OptionType.ATTACK]
    if not attack_opts:
        return [evolve_opts[0][0]]
    best_attack_dmg = 0
    for opt in attack_opts:
        atk = attack_info(opt.get("attackId"))
        if atk:
            best_attack_dmg = max(best_attack_dmg, atk.get("damage", 0))
    opp_hp = remaining_hp(active_card(ctx.opp))
    if opp_hp is not None and best_attack_dmg >= opp_hp:
        return None  # a lethal attack is on the table -- don't trade it for evolving
    return [evolve_opts[0][0]]


def attack_choice(ctx: Ctx) -> list[int] | None:
    """Default attack: highest-damage legal attack, skipping our own ex
    attacks (Phantom Dive, Cruel Arrow) when the opposing Active blocks all
    ex-attack damage outright (Crustle's Mysterious Rock Inn)."""
    attack_opts = [(i, opt) for i, opt in enumerate(ctx.options) if opt.get("type") == OptionType.ATTACK]
    if not attack_opts:
        return None
    opp_active = active_card(ctx.opp)
    blocked = bool(opp_active) and opp_active.get("name") in EX_ATTACK_DENY_TARGETS
    scored = []
    for i, opt in attack_opts:
        aid = opt.get("attackId")
        atk = attack_info(aid) if aid is not None else None
        if blocked and aid in _EX_ATTACK_IDS:
            continue
        dmg = atk.get("damage", 0) if atk else 0
        scored.append((-dmg, i))
    if not scored:
        return None  # only ex attacks legal and they're blocked — defer, don't guess
    scored.sort()
    return [scored[0][1]]


# --- Registration ------------------------------------------------------------

DRAGAPULT_HEURISTICS: list[Heuristic] = [
    archetype_latch,
    mulligan,
    active_replacement,
    setup_pokemon,
    watchtower_meowth_sequencing,
    search_for_dreepy,
    play_search_for_dreepy,
    attach_energy,
    discard_sequencing,
    supporter_tiebreak,
    bench_play_discretion,
    boss_orders_target,
    bench_spread_target,
    evolve_choice,
    attack_choice,
]
