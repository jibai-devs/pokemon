# CABT — Pokémon TCG Card Battle Environment

Kaggle environment for simulating Pokémon Trading Card Game battles.
Source: `kaggle_environments` package, `kaggle_environments.envs.cabt`.

## How This Was Discovered

1. Installed `kaggle-environments` via `uv pip install kaggle-environments`
2. Read the source files:
   - `.venv/lib/python3.14/site-packages/kaggle_environments/envs/cabt/cabt.json` — environment spec
   - `.venv/lib/python3.14/site-packages/kaggle_environments/envs/cabt/cabt.py` — interpreter, agents, deck definition
   - `.venv/lib/python3.14/site-packages/kaggle_environments/envs/cabt/cg/game.py` — Python bindings to native C library
   - `.venv/lib/python3.14/site-packages/kaggle_environments/envs/cabt/cg/sim.py` — ctypes FFI definitions
3. Wrote `explore_cabt.py` — ran a game with `random_agent` vs `first_agent`, printed spec, deck, step-by-step state
4. Wrote `explore_cabt_deep.py` — dumped all observed option types and mid-game/final board states

## Environment Spec (cabt.json)

- **Name**: `cabt`
- **Title**: "Card Battle"
- **Description**: "Limited Card Battle."
- **Players**: 2
- **Episode steps**: 10,000 max
- **Run timeout**: 3,000 seconds
- **Reward**: Win=1, Loss=-1, Draw=0
- **Action**: `list[int]` — deck submission (60 card IDs) or list of option indices

## Game Flow

### Phase 1: Deck Submission
- First call to agent: `obs["select"]` is `null`
- Agent must return a list of exactly 60 card IDs
- Both players submit simultaneously

### Phase 2: Coin Flip
- `select.option` offers two choices: `{"type": 1}` (go first) and `{"type": 2}` (go second)

### Phase 3: Battle
- Players alternate turns
- Each turn, the active player receives `select` with available actions
- Player picks action indices; opponent's `select` is `null` or shows pending choices
- Game ends when `current.result >= 0`

## Default Deck (60 cards)

```
Card 3:    x33  (Basic Energy)
Card 721:  x2   (Stage 2, 350 HP)
Card 722:  x4   (Stage 1, 90 HP — evolves into 721)
Card 723:  x4   (Evolution line, 350 HP)
Card 1092: x1   (Supporter/Trainer)
Card 1121: x2   (Trainer)
Card 1145: x2   (Trainer)
Card 1163: x2   (Pokémon Tool)
Card 1219: x4   (Trainer)
Card 1227: x4   (Trainer)
Card 1262: x2   (Trainer)
```

## Observation Structure

```python
obs = {
    "remainingOverageTime": float,   # banked time in seconds
    "step": int,                     # current step number
    "select": None | {               # null during deck submission
        "type": int,                 # context type (see below)
        "context": int,              # context ID
        "minCount": int,             # minimum selections
        "maxCount": int,             # maximum selections
        "remainDamageCounter": int,
        "remainEnergyCost": int,
        "option": list[dict],        # available choices
        "deck": None | list,
        "contextCard": None | dict,
        "effect": None | dict,
    },
    "logs": list,                    # game event log
    "current": {
        "turn": int,                 # current turn number
        "turnActionCount": int,
        "yourIndex": int,            # 0 or 1 — which player you are
        "firstPlayer": int,          # -1 until determined
        "supporterPlayed": bool,
        "stadiumPlayed": bool,
        "energyAttached": bool,
        "retreated": bool,
        "result": int,               # -1=ongoing, 0=p0 wins, 1=p1 wins, 2=draw
        "stadium": list,
        "looking": None | dict,
        "players": [player_state, player_state],
    },
    "search_begin_input": str,       # binary blob for native lib (hidden from agents)
}
```

### Player State (`current.players[i]`)

```python
{
    "active": [card],        # active Pokémon (list, usually 0 or 1)
    "bench": [card, ...],    # bench Pokémon (max 5)
    "benchMax": 5,
    "deckCount": int,        # cards remaining in deck
    "discard": [card, ...],  # discard pile
    "prize": [card | None],  # 6 prize cards (None = taken)
    "handCount": int,        # number of cards in hand
    "hand": list | None,     # your hand (visible) or None (opponent's, hidden)
    "poisoned": bool,
    "burned": bool,
    "asleep": bool,
    "paralyzed": bool,
    "confused": bool,
}
```

### Card Object

```python
{
    "id": int,           # card ID (matches deck list)
    "serial": int,       # unique instance serial number
    "playerIndex": int,  # 0 or 1
    "hp": int,           # current HP
    "maxHp": int,        # max HP
    "appearThisTurn": bool,
    "energies": [int],       # energy type IDs attached
    "energyCards": [card],   # energy card objects attached
    "tools": [card],         # Pokémon tool cards attached
    "preEvolution": [card],  # evolution chain (child first)
}
```

## Select Option Types

All options are dicts with at least a `"type"` key.

| Type | Shape | Meaning |
|------|-------|---------|
| 0 | `{type:0, number:int}` | Contextual choice (mulligan confirm, etc.) |
| 1 | `{type:1}` | Coin flip: choose heads (go first) |
| 2 | `{type:2}` | Coin flip: choose tails (go second) |
| 3 | `{type:3, area:int, index:int, playerIndex:int}` | Play a card from hand/area |
| 7 | `{type:7, index:int}` | Attach energy to a Pokémon |
| 8 | `{type:8, area:int, index:int, inPlayArea:int, inPlayIndex:int}` | Use attack or ability |
| 9 | `{type:9, area:int, index:int, inPlayArea:int, inPlayIndex:int}` | Select target for an effect |
| 10 | `{type:10, area:int, index:int}` | Select from prize cards |
| 12 | `{type:12}` | Confirm / mulligan acknowledge |
| 13 | `{type:13, attackId:int}` | Attack selection (by attack ID) |
| 14 | `{type:14}` | End turn / pass |

### Area Codes (observed)

- `2` — Hand
- `4` — Bench
- `5` — Hand (energy attachment context)
- `7` — Prize

## Built-in Agents

```python
from kaggle_environments.envs.cabt.cabt import random_agent, first_agent
```

- **`random_agent(obs)`**: Submits default deck; picks random options during battle
- **`first_agent(obs)`**: Submits default deck; always picks the first option

## Running a Game

```python
import kaggle_environments as kaggle
from kaggle_environments.envs.cabt.cabt import random_agent, first_agent

env = kaggle.make("cabt", debug=True)
env.reset()
steps = env.run([random_agent, first_agent])

# steps[i] = [player_0_state, player_1_state]
# Each state has: status, reward, observation, action
```

## Writing a Custom Agent

```python
def my_agent(obs: dict) -> list[int]:
    # Phase 1: Deck submission
    if obs["select"] is None:
        return [3] * 33 + [721]*2 + [722]*4 + [723]*4 + [1092] + [1121]*2 + [1145]*2 + [1163]*2 + [1219]*4 + [1227]*4 + [1262]*2

    # Phase 2: Battle decisions
    options = obs["select"]["option"]
    max_count = obs["select"]["maxCount"]

    # Return list of indices into options list
    return list(range(max_count))
```

## Native Library

The game engine is a compiled C library (`libcg.so` on Linux, `cg.dll` on Windows) loaded via `ctypes`. Python bindings are in `cg/game.py` and `cg/sim.py`. Key functions:

- `lib.GameInitialize()` — init
- `lib.BattleStart(cards_ptr) -> StartData` — start battle with 120 card IDs
- `lib.GetBattleData(battle_ptr) -> SerialData` — get current state as JSON
- `lib.Select(battle_ptr, indices, count) -> int` — submit selection
- `lib.BattleFinish(battle_ptr)` — free battle memory
- `lib.VisualizeData(battle_ptr) -> str` — get visualization data

## Explorer Scripts

- `explore_cabt.py` — prints spec, deck breakdown, step-by-step game trace, full observation dump
- `explore_cabt_deep.py` — catalogs all observed option types, dumps mid-game and final board states
