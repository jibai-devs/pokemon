"""Scored agent for the 000 fire deck.

A hand-written heuristic agent: it labels and scores the engine's options and
picks the highest-scoring one(s). This is the reference agent we use to play and
understand games before training anything. Verbose logging is gated by module
state set via :func:`set_verbose` / :func:`set_game_num` (the CLI drives these).
"""

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
        _log(f"  Choices ({len(options)}, pick {max_count}):")
        for i, opt in enumerate(options):
            _log(f"    [{i}] {format_option(opt, hand)}")

    # Coin flip: always go first
    for i, opt in enumerate(options):
        if opt.get("type") == 1:
            _log("  -> Picking: GO FIRST")
            return [i]

    # Mulligan confirm
    if len(options) == 1 and options[0].get("type") == 0:
        _log("  -> Picking: OK")
        return [0]

    # Single option
    if len(options) == 1:
        _log(f"  -> Picking: {format_option(options[0], hand)}")
        return [0]

    # Score each option
    scores = []
    for i, opt in enumerate(options):
        score = score_option(opt, me, hand, current)
        scores.append((score, i))

    # Sort by score descending, pick best
    scores.sort(reverse=True, key=lambda x: x[0])
    chosen = [idx for _, idx in scores[:max_count]]

    if _verbose:
        picked = [f"{format_option(options[i], hand)} (score={s})" for s, i in scores[:max_count]]
        _log(f"  -> Picking: {', '.join(picked)}")

    return chosen


def score_option(opt: dict, me: dict, hand: list, current: dict) -> float:
    """Score an option - higher is better."""
    opt_type = opt.get("type", -1)
    score = 0.0

    # === Type 3: Play Pokemon from hand ===
    if opt_type == 3:
        area = opt.get("area", 0)
        index = opt.get("index", -1)

        if area == 2 and 0 <= index < len(hand):
            card = hand[index]
            card_id = card.get("id", -1)

            if card_id == 46:  # Gouging Fire ex
                score += 90
            elif card_id == 76:  # Slugma
                score += 85
            elif card_id == 30:  # Magcargo ex
                active = me.get("active", [])
                bench = me.get("bench", [])
                has_slugma = any(c.get("id") == 76 for c in active + bench)
                score += 95 if has_slugma else 20
            elif card_id in {1092, 1121, 1145, 1163, 1219, 1227, 1245}:
                score += 40
            else:
                score += 30

    # === Type 8: Play trainer/item from hand ===
    elif opt_type == 8:
        area = opt.get("area", 0)
        index = opt.get("index", -1)

        if area == 2 and 0 <= index < len(hand):
            card = hand[index]
            card_id = card.get("id", -1)

            if card_id == 1121:  # Ultra Ball
                score += 70
            elif card_id == 1145:  # Mega Signal
                score += 65
            elif card_id == 1092:  # Secret Box
                score += 75
            elif card_id == 1219:  # Team Rocket's Petrel
                if not current.get("supporterPlayed", False):
                    score += 80
                else:
                    score -= 50
            elif card_id == 1227:  # Lillie's Determination
                if not current.get("supporterPlayed", False):
                    score += 85
                else:
                    score -= 50
            elif card_id == 1245:  # Festival Grounds
                if not current.get("stadiumPlayed", False):
                    score += 60
                else:
                    score -= 50
            elif card_id == 1163:  # Powerglass
                score += 55
            else:
                score += 35

    # === Type 7: Attach energy ===
    elif opt_type == 7:
        index = opt.get("index", -1)
        if 0 <= index < len(hand):
            card = hand[index]
            card_id = card.get("id", -1)
            if card_id == 2:  # Fire energy
                active = me.get("active", [])
                if active:
                    energies = active[0].get("energies", [])
                    if len(energies) == 0:
                        score += 95
                    elif len(energies) < 3:
                        score += 80
                    else:
                        score += 60
                else:
                    score += 50
            else:
                score += 30

    # === Type 13: Attack ===
    elif opt_type == 13:
        attack_id = opt.get("attackId", 0)
        attack_damage = {44: 60, 45: 260, 17: 70, 18: 140}
        score += attack_damage.get(attack_id, 50)

    # === Other types ===
    elif opt_type == 9:
        score += 70
    elif opt_type == 10:
        score += 65
    elif opt_type == 12:
        score += 60
    elif opt_type == 14:
        score += 10
    elif opt_type == 0:
        score += 20

    return score
