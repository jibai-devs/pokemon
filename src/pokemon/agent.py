"""Scored agent for the 000 fire deck.

A hand-written heuristic agent: it labels and scores the engine's options and
picks the highest-scoring one(s). This is the reference agent we use to play and
understand games before training anything. Verbose logging is gated by module
state set via :func:`set_verbose` / :func:`set_game_num` (the CLI drives these).
"""

from pokemon.cabt_enums import AreaType, OptionType, SelectContext, SelectType, safe
from pokemon.catalog import card_name, format_option
from pokemon.decks import FIRE_DECK, deck_summary

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


def fire_agent(obs: dict) -> list[int]:
    """Pick action(s) for the fire deck given an engine observation."""

    # Phase 1: Submit deck
    if obs["select"] is None:
        lines, checksum = deck_summary(FIRE_DECK)
        _log(f"\n{'=' * 60}")
        _log(f"GAME {_game_num}: Submitting deck ({len(FIRE_DECK)} cards, sha256:{checksum})")
        _log(f"{'=' * 60}")
        # Print the full card breakdown only once to avoid repeating every game.
        if _game_num <= 1:
            for line in lines:
                _log(line)
        return FIRE_DECK

    select = obs["select"]
    options = select["option"]
    max_count = select["maxCount"]
    sel_type = safe(SelectType, select.get("type"))
    context = safe(SelectContext, select.get("context"))
    current = obs.get("current", {})
    my_idx = current.get("yourIndex", 0)
    players = current.get("players", [])
    me = players[my_idx] if my_idx < len(players) else {}
    hand = me.get("hand", []) or []
    active = me.get("active", [])
    bench = me.get("bench", [])
    turn = current.get("turn", 0)

    # Log turn info
    if _verbose:
        if active and active[0]:
            a = active[0]
            a_name = card_name(a.get("id", -1))
            a_hp = a.get("hp", "?")
            a_max = a.get("maxHp", "?")
            a_nrg = len(a.get("energies", []))
            bench_ids = [card_name(c.get("id", -1)) for c in bench if c]
            _log(
                f"\n--- Turn {turn} | Active: {a_name} HP={a_hp}/{a_max} "
                f"Energy={a_nrg} | Bench: {bench_ids} | Hand: {len(hand)} ---"
            )
        else:
            _log(
                f"\n--- Turn {turn} | No active Pokemon | "
                f"Bench: {len(bench)} | Hand: {len(hand)} ---"
            )

    # Log available options
    if _verbose:
        st = sel_type.name if sel_type is not None else "?"
        cx = context.name if context is not None else "?"
        _log(f"  Choices ({len(options)}, pick {max_count}) [{st} / {cx}]:")
        for i, opt in enumerate(options):
            _log(f"    [{i}] {format_option(opt, hand, context)}")

    # Coin flip: take the first turn when the engine asks who goes first.
    if context == SelectContext.IS_FIRST:
        for i, opt in enumerate(options):
            if opt.get("type") == OptionType.YES:
                _log("  -> Picking: GO FIRST")
                return [i]

    # Single option (e.g. a forced mulligan confirm, lone count).
    if len(options) == 1:
        _log(f"  -> Picking: {format_option(options[0], hand, context)}")
        return [0]

    # Score each option
    scores = []
    for i, opt in enumerate(options):
        score = score_option(opt, me, hand, current, context)
        scores.append((score, i))

    # Sort by score descending, pick best
    scores.sort(reverse=True, key=lambda x: x[0])
    chosen = [idx for _, idx in scores[:max_count]]

    if _verbose:
        picked = [
            f"{format_option(options[i], hand, context)} (score={s})" for s, i in scores[:max_count]
        ]
        _log(f"  -> Picking: {', '.join(picked)}")

    return chosen


# Per-card desirability of putting a Pokémon from hand into play (used by both
# PLAY and the setup CARD selection). Higher = play sooner.
_POKEMON_PLAY = {
    46: 90,  # Gouging Fire ex — main attacker, basic
    76: 85,  # Slugma — basic, line into Magcargo ex
}
# How much we value keeping a card. Used to pick what to KEEP vs what to lose
# (discard/return-to-deck), so duplicates and spare energy go first.
_CARD_VALUE = {
    46: 90,  # Gouging Fire ex
    30: 80,  # Magcargo ex
    76: 70,  # Slugma
    2: 10,  # Fire Energy — plentiful, cheapest to lose
}
# SelectContexts where the chosen card LEAVES play for somewhere worse, so we
# want to part with the least valuable card.
_LOSE_CONTEXTS = frozenset(
    {
        SelectContext.DISCARD,
        SelectContext.TO_DECK,
        SelectContext.TO_DECK_BOTTOM,
        SelectContext.TO_PRIZE,
    }
)


def _card_value(card_id: int) -> float:
    return _CARD_VALUE.get(card_id, 40.0)


# Trainers/items/stadium and their base value when PLAYed from hand.
_TRAINER_PLAY = {
    1092: 75,  # Secret Box (item)
    1121: 70,  # Ultra Ball (item)
    1145: 65,  # Mega Signal (item)
    1163: 55,  # Powerglass (item)
}


def _hand_card_id(opt: dict, hand: list) -> int:
    """Resolve the hand card an option acts on, or -1 if not from our hand."""
    if opt.get("area", AreaType.HAND) != AreaType.HAND:
        return -1
    index = opt.get("index", -1)
    if 0 <= index < len(hand):
        return hand[index].get("id", -1)
    return -1


def _play_score(card_id: int, me: dict, current: dict) -> float:
    """Score playing ``card_id`` from hand during the main phase."""
    if card_id in _POKEMON_PLAY:
        return _POKEMON_PLAY[card_id]
    if card_id == 30:  # Magcargo ex — only good once a Slugma exists to evolve
        in_play = me.get("active", []) + me.get("bench", [])
        return 95 if any(c.get("id") == 76 for c in in_play) else 20
    if card_id == 1219:  # Team Rocket's Petrel (supporter)
        return -50 if current.get("supporterPlayed", False) else 80
    if card_id == 1227:  # Lillie's Determination (supporter)
        return -50 if current.get("supporterPlayed", False) else 85
    if card_id == 1245:  # Festival Grounds (stadium)
        return -50 if current.get("stadiumPlayed", False) else 60
    if card_id in _TRAINER_PLAY:
        return _TRAINER_PLAY[card_id]
    return 35


def score_option(opt: dict, me: dict, hand: list, current: dict, context=None) -> float:
    """Score an option - higher is better.

    Dispatches on the engine's real :class:`OptionType` (7=PLAY, 8=ATTACH, …),
    and uses ``context`` (a :class:`SelectContext`) where the type alone is
    ambiguous — notably NUMBER, where we pick the sensible end of the range.
    """
    t = safe(OptionType, opt.get("type"))
    score = 0.0

    # === PLAY a card from hand (Pokémon / trainer / item / stadium) ===
    if t == OptionType.PLAY:
        score += _play_score(_hand_card_id(opt, hand), me, current)

    # === CARD selection (setup actives/bench, search/discard targets) ===
    elif t == OptionType.CARD:
        card_id = _hand_card_id(opt, hand)
        if context in _LOSE_CONTEXTS:
            # Lose the least valuable card: invert so cheap cards score highest.
            score += 100.0 - _card_value(card_id)
        elif card_id in _POKEMON_PLAY:
            score += _POKEMON_PLAY[card_id]
        elif card_id == 30:  # Magcargo ex is a Stage 1 — a poor setup basic
            score += 20
        elif card_id != -1:
            score += 40
        else:
            score += 30

    # === ATTACH energy to a Pokémon in play ===
    elif t == OptionType.ATTACH:
        card_id = _hand_card_id(opt, hand)
        to_active = opt.get("inPlayArea") == AreaType.ACTIVE
        if card_id == 2:  # Fire Energy
            active = me.get("active", [])
            n = len(active[0].get("energies", [])) if active and active[0] else 0
            base = 95 if n == 0 else 80 if n < 3 else 60
            score += base if to_active else base - 25
        else:
            score += 30

    # === EVOLVE a Pokémon in play ===
    elif t == OptionType.EVOLVE:
        card_id = _hand_card_id(opt, hand)
        score += 95 if card_id == 30 else 70  # Slugma -> Magcargo ex

    # === ATTACK ===
    elif t == OptionType.ATTACK:
        attack_damage = {44: 60, 45: 260, 17: 70, 18: 140}
        score += attack_damage.get(opt.get("attackId", 0), 50)

    # === Yes/No — context-aware (default: lean yes, as before) ===
    elif t == OptionType.YES:
        score += 50
    elif t == OptionType.NO:
        score += 40

    # === NUMBER — pick the sensible end of the range per context ===
    elif t == OptionType.NUMBER:
        n = opt.get("number", 0) or 0
        # DRAW_COUNT / damage / heal: more is better, so prefer the largest n.
        score += float(n)

    # === Remaining option types — fixed priorities ===
    elif t == OptionType.ABILITY:
        score += 65
    elif t == OptionType.RETREAT:
        score += 30
    elif t == OptionType.DISCARD:
        # Prefer discarding low-value cards (energy/duplicates) over key Pokémon.
        card_id = _hand_card_id(opt, hand)
        score += 70 if card_id in (2, -1) else 20
    elif t == OptionType.END:
        score += 10
    else:
        score += 25

    return score
