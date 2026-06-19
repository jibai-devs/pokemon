"""Deep explorer for CABT (Pokémon TCG Card Battle) environment."""

import json

import kaggle_environments as kaggle
from kaggle_environments.envs.cabt.cabt import first_agent, random_agent

env = kaggle.make("cabt", debug=True)
env.reset()
steps = env.run([random_agent, first_agent])

# ============================================================
# Dump select options with types
# ============================================================
print("=" * 60)
print("SELECT OPTION TYPES OBSERVED")
print("=" * 60)

option_types = {}
for _i, step in enumerate(steps):
    for p in range(2):
        obs = step[p].get("observation", {})
        select = obs.get("select")
        if select and "option" in select:
            for opt in select["option"]:
                t = opt.get("type")
                if t not in option_types:
                    option_types[t] = opt
                    print(f"  Type {t}: {json.dumps(opt)}")

# ============================================================
# Dump a mid-game observation (both players)
# ============================================================
print("\n" + "=" * 60)
print("MID-GAME STATE (Step 50)")
print("=" * 60)

if len(steps) > 50:
    for p in range(2):
        obs = steps[50][p].get("observation", {})
        current = obs.get("current", {})
        print(f"\n--- Player {p} ---")
        print(f"  yourIndex: {current.get('yourIndex')}")
        print(f"  turn: {current.get('turn')}")
        print(f"  result: {current.get('result')}")

        players = current.get("players", [])
        for pi, player in enumerate(players):
            print(f"\n  Player {pi} state:")
            print(f"    active: {player.get('active', [])}")
            print(f"    bench ({len(player.get('bench', []))}): {player.get('bench', [])}")
            print(f"    deckCount: {player.get('deckCount')}")
            print(f"    discard ({len(player.get('discard', []))}): {player.get('discard', [])}")
            print(f"    prize ({len(player.get('prize', []))}): {player.get('prize', [])}")
            print(
                f"    hand: {player.get('hand', []) if pi == current.get('yourIndex') else '(hidden)'}"
            )
            print(
                f"    poisoned={player.get('poisoned')}, burned={player.get('burned')}, "
                f"asleep={player.get('asleep')}, paralyzed={player.get('paralyzed')}, "
                f"confused={player.get('confused')}"
            )

        select = obs.get("select")
        if select:
            print(
                f"\n  Select: type={select.get('type')}, context={select.get('context')}, "
                f"min={select.get('minCount')}, max={select.get('maxCount')}"
            )
            print(f"  Options: {json.dumps(select.get('option', []))}")

# ============================================================
# Dump end-game state
# ============================================================
print("\n" + "=" * 60)
print("FINAL GAME STATE")
print("=" * 60)

final = steps[-1]
for p in range(2):
    obs = final[p].get("observation", {})
    current = obs.get("current", {})
    if current:
        print(f"\nPlayer {p}:")
        players = current.get("players", [])
        for pi, player in enumerate(players):
            print(
                f"  Player {pi}: active={player.get('active')}, bench={len(player.get('bench', []))}, "
                f"deck={player.get('deckCount')}, discard={len(player.get('discard', []))}, "
                f"prize={len(player.get('prize', []))}"
            )
        print(f"  result: {current.get('result')}")
