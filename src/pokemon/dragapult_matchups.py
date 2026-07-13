"""Dragapult ex Tier 5 matchup identification/classification (plan 007
Section 8, extended by plan 011 Phase 2).

Detection is two mechanisms sharing one hand-written signature table.
Preferred: the PKM-023 deck-id belief — classify the believed archetype's
full (predicted) list through the signatures via ``_matchup_bucket``, which
usually resolves by ~turn 2. Fallback: the original hard latch — any
opponent Pokemon/Stadium name seen so far this game (played to bench/active,
discarded, or in the Stadium slot) latches the matchup identity for the rest
of the game (plan 007's Tier 5 design). "mirror" is checked last since
"Dragapult ex" is the least distinctive signature (it appears as a partner
in other decks too).

This module is purely about *identification* — "who is my opponent." The
decision rules that consume its output (``boss_orders_target``,
``bench_spread_target`` in ``heuristics_dragapult.py``) live separately.
"""

from pokemon.catalog import card_name
from pokemon.deck_id import DeckIdentifier
from pokemon.heuristics import Ctx, all_pokemon

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


def archetype_latch(ctx: Ctx) -> list[int] | None:
    """Side-effect-only hook (Tier 5 detection) — always returns ``None``.
    Run first every decision so later rules can read ``ctx.state["archetype"]``."""
    if ctx.state.get("archetype"):
        return None
    seen_names: set[str] = set()
    for c in all_pokemon(ctx.opp):
        name = c.get("name")
        if name:
            seen_names.add(name)
    for c in ctx.opp.get("discard") or []:
        name = c.get("name")
        if name:
            seen_names.add(name)
    for c in ctx.current.get("stadium") or []:
        name = c.get("name")
        if name:
            seen_names.add(name)
    for archetype, sigs in TIER5_SIGNATURES.items():
        if any(s in seen_names for s in sigs):
            ctx.state["archetype"] = archetype
            break
    return None


def deck_belief_update(ctx: Ctx) -> list[int] | None:
    """Side-effect-only hook (PKM-023) -- always returns ``None``. Folds this
    decision's opponent-visible state into a per-game ``DeckIdentifier``
    (``ctx.state["deck_id"]``) so any heuristic can read
    ``archetype_belief()``/``opp_remaining()``/``p_in_hand()``/
    ``identified_list()`` off it. Consumed by ``_matchup_bucket`` below
    (plan 011 Phase 2), which the Tier 4 targeting rules prefer over the
    ``archetype_latch`` hard read."""
    identifier = ctx.state.get("deck_id")
    if not isinstance(identifier, DeckIdentifier):
        identifier = DeckIdentifier()
        ctx.state["deck_id"] = identifier
    identifier.update(ctx.opp)
    return None


def _tier5_bucket_from_names(names: set[str]) -> str | None:
    """Classify a set of card names into a ``TIER5_SIGNATURES`` bucket --
    the same signature scan ``archetype_latch`` runs over the visible board,
    applied instead to a full (predicted) decklist. Bucket order matters the
    same way: "mirror" last, since Dragapult ex also appears as a partner in
    other decks."""
    for bucket, sigs in TIER5_SIGNATURES.items():
        if any(s in names for s in sigs):
            return bucket
    return None


def _matchup_bucket(ctx: Ctx) -> str | None:
    """Which ``TIER5_PRIORITY_TARGETS`` bucket targeting rules should use
    (plan 011 Phase 2). Prefers the deck-id belief -- classifying the
    identified exact list (level 1) or the best archetype's core+flex
    (level 2) through the signature table -- because the belief usually
    concentrates by ~turn 2, before the signature Pokemon is physically on
    the board. Falls back to ``archetype_latch``'s board-observation read
    (level 3, or a believed archetype with no signature overlap)."""
    ident = ctx.state.get("deck_id")
    if isinstance(ident, DeckIdentifier):
        exact = ident.identified_list()
        if exact is not None:
            bucket = _tier5_bucket_from_names({card_name(cid) for cid in exact})
            if bucket is not None:
                return bucket
        else:
            best = ident.best_archetype()
            if best is not None:
                cache = ctx.state.get("matchup_bucket_cache")
                if not isinstance(cache, dict):
                    cache = {}
                    ctx.state["matchup_bucket_cache"] = cache
                if best[0] not in cache:
                    arch = ident.archetypes().get(best[0], {})
                    ids = set(arch.get("core", {})) | set(arch.get("flex", {}))
                    cache[best[0]] = _tier5_bucket_from_names({card_name(int(cid)) for cid in ids})
                bucket = cache[best[0]]
                if isinstance(bucket, str):
                    return bucket
    latched = ctx.state.get("archetype")
    return latched if isinstance(latched, str) else None
