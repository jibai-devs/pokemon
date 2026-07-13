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


def _resolve_opp_card(ctx: Ctx, opt: dict) -> dict | None:
    """Resolve a CARD-shaped option against the OPPONENT's board.

    Select contexts that only ever target the opponent (Boss's Orders'
    switch-in choice, Phantom Dive's bench-spread target) are resolved
    directly against ``ctx.opp`` rather than reusing ``_option_card_id``
    (which only resolves against ``ctx.me`` — see that function's
    docstring), since which player's board an option's ``area``/``index``
    refers to for these contexts isn't itself confirmed (Phase 2 gap), but
    game rules guarantee it's always the opponent's here.
    """
    area = opt.get("area")
    idx = opt.get("index")
    if idx is None:
        return None
    if area == AreaType.ACTIVE:
        return active_card(ctx.opp)
    if area == AreaType.BENCH:
        bench = bench_cards(ctx.opp)
        return bench[idx] if 0 <= idx < len(bench) else None
    return None


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

_PRIORITY_FIRST =  [BUDEW, MUNKIDORI, DREEPY, MOLTRES, FEZANDIPITI_EX,   MEOWTH_EX]
_PRIORITY_SECOND = [BUDEW, DREEPY, MUNKIDORI, MOLTRES, FEZANDIPITI_EX, MEOWTH_EX]


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

    def tier(card: dict) -> int:
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

    candidates.sort(key=lambda ic: (tier(ic[1]), -(remaining_hp(ic[1]) or 0)))
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
    fuel = [(i, c) for i, c in fuel if c is not None and c.get("id") in (DREEPY, DRAKLOAK, DRAGAPULT_EX)]
    if not fuel:
        return None
    unready = [(i, c) for i, c in fuel if not (c.get("id") == DRAGAPULT_EX and energy_count(c) >= 2)]
    if not unready:
        return [fuel[0][0]]
    for i, c in unready:
        if c is active:
            return [i]
    unready.sort(key=lambda ic: -energy_count(ic[1]))
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
    if ctx.sel_context not in (SelectContext.DISCARD, SelectContext.DISCARD_CARD_OR_ATTACHED_CARD):
        return None
    discard_opts = [(i, opt) for i, opt in enumerate(ctx.options) if opt.get("type") == OptionType.DISCARD]
    if not discard_opts:
        return None
    need = ctx.select.get("maxCount") or 1
    scored = []
    for i, opt in discard_opts:
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


# --- Tier 4 — attack/targeting, archetype-agnostic --------------------------


def boss_orders_target(ctx: Ctx) -> list[int] | None:
    """Default Boss's Orders target: lethal-this-turn first, else the
    matchup's priority target, else the highest-value (ex) benched piece."""
    if ctx.sel_context not in (SelectContext.SWITCH, SelectContext.TO_ACTIVE):
        return None
    candidates = []
    for i, opt in enumerate(ctx.options):
        if opt.get("type") != OptionType.CARD:
            continue
        card = _resolve_opp_card(ctx, opt)
        if card is not None:
            candidates.append((i, card))
    if not candidates:
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

    candidates.sort(key=score)
    return [candidates[0][0]]


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
        card = _resolve_opp_card(ctx, opt)
        if card is not None and card in opp_bench:
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
    attach_energy,
    discard_sequencing,
    supporter_tiebreak,
    bench_play_discretion,
    boss_orders_target,
    bench_spread_target,
    attack_choice,
]
