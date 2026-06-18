"""Explore the CABT (Card Battle) Kaggle environment."""

import json
import kaggle_environments as kaggle
from kaggle_environments.envs.cabt.cabt import random_agent, first_agent, deck

# ============================================================
# 1. Environment Specification
# ============================================================
print("=" * 60)
print("1. ENVIRONMENT SPECIFICATION")
print("=" * 60)
env = kaggle.make("cabt", debug=True)
spec = env.specification
print(json.dumps(spec, indent=2))

# ============================================================
# 2. Default Deck (60 cards)
# ============================================================
print("\n" + "=" * 60)
print("2. DEFAULT DECK (60 card IDs)")
print("=" * 60)
print(f"Deck size: {len(deck)}")
print(f"Unique cards: {sorted(set(deck))}")
from collections import Counter
counts = Counter(deck)
print("Card counts:")
for card_id, count in sorted(counts.items()):
    print(f"  Card {card_id}: x{count}")

# ============================================================
# 3. Run a Game (random vs first agent)
# ============================================================
print("\n" + "=" * 60)
print("3. RUNNING A GAME: random_agent vs first_agent")
print("=" * 60)

env = kaggle.make("cabt", debug=True)
env.reset()

# Run with built-in agents
steps = env.run([random_agent, first_agent])
print(f"Total steps: {len(steps)}")

# ============================================================
# 4. Inspect Game Steps
# ============================================================
print("\n" + "=" * 60)
print("4. GAME STEP INSPECTION")
print("=" * 60)

for i, step in enumerate(steps[:10]):  # first 10 steps
    print(f"\n--- Step {i} ---")
    for player_idx, player_state in enumerate(step):
        status = player_state.get("status", "?")
        reward = player_state.get("reward", "?")
        obs = player_state.get("observation", {})
        action = player_state.get("action", None)

        select = obs.get("select")
        current = obs.get("current")

        print(f"  Player {player_idx}: status={status}, reward={reward}")
        if action is not None:
            if isinstance(action, list) and len(action) > 10:
                print(f"    action: [deck of {len(action)} cards]")
            else:
                print(f"    action: {action}")
        if current:
            print(f"    current.yourIndex: {current.get('yourIndex')}")
            print(f"    current.result: {current.get('result')}")
        if select:
            options = select.get("option", [])
            max_count = select.get("maxCount", "?")
            print(f"    select: {len(options)} options, maxCount={max_count}")
            if len(options) <= 5:
                print(f"    options: {options}")

# ============================================================
# 5. Inspect Full Observation Structure
# ============================================================
print("\n" + "=" * 60)
print("5. FULL OBSERVATION STRUCTURE (Step 1, Player 0)")
print("=" * 60)

if len(steps) > 1:
    obs = steps[1][0].get("observation", {})
    # Remove search_begin_input (binary blob)
    obs_clean = {k: v for k, v in obs.items() if k != "search_begin_input"}
    print(json.dumps(obs_clean, indent=2, default=str)[:3000])

# ============================================================
# 6. Final Result
# ============================================================
print("\n" + "=" * 60)
print("6. FINAL RESULT")
print("=" * 60)
final = steps[-1]
for i, p in enumerate(final):
    print(f"  Player {i}: status={p.get('status')}, reward={p.get('reward')}")

winner = "Draw"
if final[0].get("reward", 0) == 1:
    winner = "Player 0 (random_agent)"
elif final[1].get("reward", 0) == 1:
    winner = "Player 1 (first_agent)"
print(f"  Winner: {winner}")
