"""Fire Deck Agent — plays the 000 fire deck in CABT."""

import kaggle_environments as kaggle
from kaggle_environments.envs.cabt.cabt import random_agent

# Fire deck card IDs
DECK = (
    [46] * 2  # Gouging Fire ex
    + [76] * 4  # Slugma
    + [30] * 4  # Magcargo ex
    + [1092]  # Secret Box
    + [1121] * 2  # Ultra Ball
    + [1145] * 2  # Mega Signal
    + [1163] * 2  # Powerglass
    + [1219] * 4  # Team Rocket's Petrel
    + [1227] * 4  # Lillie's Determination
    + [1245] * 2  # Festival Grounds
    + [2] * 33  # Basic Fire Energy
)


def fire_agent(obs: dict) -> list[int]:
    """Smart agent for the fire deck."""

    # Phase 1: Submit deck
    if obs["select"] is None:
        return DECK

    select = obs["select"]
    options = select["option"]
    max_count = select["maxCount"]
    current = obs.get("current", {})
    my_idx = current.get("yourIndex", 0)
    players = current.get("players", [])
    me = players[my_idx] if my_idx < len(players) else {}
    hand = me.get("hand", []) or []

    # Coin flip: always go first
    for i, opt in enumerate(options):
        if opt.get("type") == 1:
            return [i]

    # Mulligan confirm (type 0 with number)
    if len(options) == 1 and options[0].get("type") == 0:
        return [0]

    # Single option: just take it
    if len(options) == 1:
        return [0]

    # Score each option
    scores = []
    for i, opt in enumerate(options):
        score = _score_option(opt, me, hand, current)
        scores.append((score, i))

    # Sort by score descending, pick best
    scores.sort(reverse=True, key=lambda x: x[0])
    chosen = [idx for _, idx in scores[:max_count]]
    return chosen


def _score_option(opt: dict, me: dict, hand: list, current: dict) -> float:
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

            # Prioritize playing basics to bench
            if card_id == 46:  # Gouging Fire ex (basic)
                score += 90
            elif card_id == 76:  # Slugma (basic)
                score += 85
            elif card_id == 30:  # Magcargo ex (stage 1)
                # Check if we have Slugma in play
                active = me.get("active", [])
                bench = me.get("bench", [])
                has_slugma = any(c.get("id") == 76 for c in active + bench)
                score += 95 if has_slugma else 20
            elif card_id in {1092, 1121, 1145, 1163, 1219, 1227, 1245}:
                # Trainer cards - lower priority than Pokemon
                score += 40
            else:
                score += 30

    # === Type 8: Play trainer/item from hand or use ability ===
    elif opt_type == 8:
        area = opt.get("area", 0)
        index = opt.get("index", -1)

        if area == 2 and 0 <= index < len(hand):
            card = hand[index]
            card_id = card.get("id", -1)

            # Playing trainer cards
            if card_id == 1121:  # Ultra Ball - search Pokemon
                score += 70
            elif card_id == 1145:  # Mega Signal - search Mega
                score += 65
            elif card_id == 1092:  # Secret Box
                score += 75
            elif card_id == 1219:  # Team Rocket's Petrel - search trainer
                if not current.get("supporterPlayed", False):
                    score += 80
                else:
                    score -= 50
            elif card_id == 1227:  # Lillie's Determination - draw
                if not current.get("supporterPlayed", False):
                    score += 85
                else:
                    score -= 50
            elif card_id == 1245:  # Festival Grounds
                if not current.get("stadiumPlayed", False):
                    score += 60
                else:
                    score -= 50
            elif card_id == 1163:  # Powerglass (tool)
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
                # Prefer attaching to active Pokemon
                active = me.get("active", [])
                if active:
                    energies = active[0].get("energies", [])
                    if len(energies) == 0:
                        score += 95  # Desperately needs energy
                    elif len(energies) < 3:
                        score += 80
                    else:
                        score += 60
                else:
                    score += 50
            else:
                score += 30

    # === Type 13: Attack selection ===
    elif opt_type == 13:
        attack_id = opt.get("attackId", 0)
        # Prefer higher damage attacks
        attack_damage = {
            44: 60,  # Heat Blast
            45: 260,  # Blaze Blitz
            17: 70,  # Hot Magma
            18: 140,  # Ground Burn
        }
        damage = attack_damage.get(attack_id, 50)
        score += damage

    # === Type 9: Select target ===
    elif opt_type == 9:
        score += 70

    # === Type 10: Select prize ===
    elif opt_type == 10:
        score += 65

    # === Type 12: Confirm ===
    elif opt_type == 12:
        score += 60

    # === Type 14: End turn ===
    elif opt_type == 14:
        score += 10  # Low priority - only if nothing else

    # === Type 0: Contextual ===
    elif opt_type == 0:
        score += 20

    return score


def run_game(verbose: bool = False):
    """Run a single game and return the result."""
    env = kaggle.make("cabt", debug=True)
    env.reset()
    steps = env.run([fire_agent, random_agent])

    final = steps[-1]
    reward = final[0].get("reward", 0)
    result = "WIN" if reward == 1 else "LOSS" if reward == -1 else "DRAW"

    if verbose:
        print(f"Game: {len(steps)} steps, result={result}")
        if len(steps) > 2:
            obs = steps[-2][0].get("observation", {})
            current = obs.get("current", {})
            players = current.get("players", [])
            if players:
                me = players[0]
                print(f"  My active: {[c.get('id') for c in me.get('active', [])]}")
                print(f"  My bench: {[c.get('id') for c in me.get('bench', [])]}")
                print(f"  My hand: {me.get('handCount', 0)} cards")
                print(f"  My deck: {me.get('deckCount', 0)} cards")

    return reward, len(steps)


if __name__ == "__main__":
    print("=== FIRE DECK AGENT ===")
    print(f"Deck: {len(DECK)} cards")
    print()

    # Run multiple games
    wins, losses, draws = 0, 0, 0
    games = 20
    total_steps = 0

    for i in range(games):
        reward, steps = run_game(verbose=(i < 5))
        total_steps += steps
        if reward == 1:
            wins += 1
        elif reward == -1:
            losses += 1
        else:
            draws += 1

    print(f"\n=== RESULTS ({games} games) ===")
    print(f"Wins: {wins} ({wins / games * 100:.0f}%)")
    print(f"Losses: {losses} ({losses / games * 100:.0f}%)")
    print(f"Draws: {draws} ({draws / games * 100:.0f}%)")
    print(f"Avg game length: {total_steps / games:.0f} steps")
