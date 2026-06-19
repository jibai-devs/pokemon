#!/usr/bin/env python3
"""Fire Deck Agent — plays the 000 fire deck in CABT."""

import typer
import kaggle_environments as kaggle
from kaggle_environments.envs.cabt.cabt import random_agent

app = typer.Typer()

CARD_NAMES = {
    46: "Gouging Fire ex",
    76: "Slugma",
    30: "Magcargo ex",
    2: "Fire Energy",
    1092: "Secret Box",
    1121: "Ultra Ball",
    1145: "Mega Signal",
    1163: "Powerglass",
    1219: "Rocket Petrel",
    1227: "Lillie Determination",
    1245: "Festival Grounds",
}

ATK_NAMES = {
    44: "Heat Blast (60)",
    45: "Blaze Blitz (260)",
    17: "Hot Magma (70)",
    18: "Ground Burn (140+)",
}

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

# Global verbose flag
_verbose = False
_game_num = 0


def _log(msg: str):
    if _verbose:
        print(msg)


def _card_name(card_id: int) -> str:
    return CARD_NAMES.get(card_id, f"Card#{card_id}")


def _format_hand(hand: list) -> str:
    if not hand:
        return "(empty)"
    names = [_card_name(c.get("id", -1)) for c in hand]
    from collections import Counter
    counts = Counter(names)
    return ", ".join(f"{n} x{c}" if c > 1 else n for n, c in counts.most_common())


def _format_option(opt: dict, hand: list) -> str:
    t = opt.get("type", -1)
    if t == 1:
        return "GO FIRST"
    if t == 2:
        return "GO SECOND"
    if t == 3:
        idx = opt.get("index", -1)
        if 0 <= idx < len(hand):
            return f"PLAY {_card_name(hand[idx].get('id', -1))}"
        return f"PLAY hand[{idx}]"
    if t == 7:
        idx = opt.get("index", -1)
        if 0 <= idx < len(hand):
            return f"ATTACH {_card_name(hand[idx].get('id', -1))}"
        return f"ATTACH hand[{idx}]"
    if t == 8:
        idx = opt.get("index", -1)
        if 0 <= idx < len(hand):
            return f"USE {_card_name(hand[idx].get('id', -1))}"
        return f"USE hand[{idx}]"
    if t == 9:
        return "SELECT TARGET"
    if t == 10:
        return "SELECT PRIZE"
    if t == 12:
        return "CONFIRM"
    if t == 13:
        atk = opt.get("attackId", 0)
        return f"ATTACK: {ATK_NAMES.get(atk, f'#{atk}')}"
    if t == 14:
        return "END TURN"
    if t == 0:
        return "OK"
    return f"?type={t}"


def fire_agent(obs: dict) -> list[int]:
    """Smart agent for the fire deck."""

    # Phase 1: Submit deck
    if obs["select"] is None:
        _log(f"\n{'='*60}")
        _log(f"GAME {_game_num}: Submitting deck ({len(DECK)} cards)")
        _log(f"{'='*60}")
        return DECK

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
            a_name = _card_name(a.get("id", -1))
            a_hp = a.get("hp", "?")
            a_max = a.get("maxHp", "?")
            a_nrg = len(a.get("energies", []))
            bench_ids = [_card_name(c.get("id", -1)) for c in bench if c]
            _log(f"\n--- Turn {turn} | Active: {a_name} HP={a_hp}/{a_max} Energy={a_nrg} | Bench: {bench_ids} | Hand: {len(hand)} ---")
        else:
            _log(f"\n--- Turn {turn} | No active Pokemon | Bench: {len(bench)} | Hand: {len(hand)} ---")

    # Log available options
    if _verbose:
        _log(f"  Choices ({len(options)}, pick {max_count}):")
        for i, opt in enumerate(options):
            _log(f"    [{i}] {_format_option(opt, hand)}")

    # Coin flip: always go first
    for i, opt in enumerate(options):
        if opt.get("type") == 1:
            _log(f"  -> Picking: GO FIRST")
            return [i]

    # Mulligan confirm
    if len(options) == 1 and options[0].get("type") == 0:
        _log(f"  -> Picking: OK")
        return [0]

    # Single option
    if len(options) == 1:
        _log(f"  -> Picking: {_format_option(options[0], hand)}")
        return [0]

    # Score each option
    scores = []
    for i, opt in enumerate(options):
        score = _score_option(opt, me, hand, current)
        scores.append((score, i))

    # Sort by score descending, pick best
    scores.sort(reverse=True, key=lambda x: x[0])
    chosen = [idx for _, idx in scores[:max_count]]

    if _verbose:
        picked = [f"{_format_option(options[i], hand)} (score={s})" for s, i in scores[:max_count]]
        _log(f"  -> Picking: {', '.join(picked)}")

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


@app.command()
def play(
    games: int = typer.Option(1, "--games", "-g", help="Number of games to play"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed game log"),
):
    """Play the fire deck against a random agent."""
    global _verbose, _game_num
    _verbose = verbose

    if not verbose:
        typer.echo(f"Playing {games} game(s)...")
        typer.echo()

    wins, losses, draws = 0, 0, 0
    total_steps = 0

    for i in range(games):
        _game_num = i + 1
        env = kaggle.make("cabt", debug=True)
        env.reset()
        steps = env.run([fire_agent, random_agent])

        final = steps[-1]
        reward = final[0].get("reward", 0)
        result = "WIN" if reward == 1 else "LOSS" if reward == -1 else "DRAW"
        total_steps += len(steps)

        if reward == 1:
            wins += 1
        elif reward == -1:
            losses += 1
        else:
            draws += 1

        if verbose:
            _log(f"\n{'='*60}")
            _log(f"RESULT: {result} in {len(steps)} steps")
            _log(f"{'='*60}")
        else:
            typer.echo(f"  Game {i+1}: {result} ({len(steps)} steps)")

    typer.echo()
    typer.echo(f"=== RESULTS ({games} games) ===")
    typer.echo(f"Wins:   {wins} ({wins/games*100:.0f}%)")
    typer.echo(f"Losses: {losses} ({losses/games*100:.0f}%)")
    typer.echo(f"Draws:  {draws} ({draws/games*100:.0f}%)")
    typer.echo(f"Avg game length: {total_steps/games:.0f} steps")


if __name__ == "__main__":
    app()
