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
        "type": int,                 # SelectType — which OptionTypes appear (see below)
        "context": int,              # SelectContext — disambiguates the selection
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

All options are dicts with at least a `"type"` key. **Canonical source:**
`src/pokemon/cabt_enums.py` (`OptionType`), transcribed from the engine docs and
verified empirically by `reverse-engineering/scripts/verify_enums.py`. The table
below matches the engine's real `OptionType`.

> ⚠️ **This table was previously wrong.** The earlier reverse-engineered version
> read these by observation and mislabeled the action types: it claimed
> `3 = play a card`, `7 = attach energy`, `8 = use attack/ability`, `9 = select
> target`, `10 = select prize`, `12 = confirm`. The engine actually uses
> `3 = CARD` (generic card pick), `7 = PLAY`, `8 = ATTACH`, `9 = EVOLVE`,
> `10 = ABILITY`, `12 = RETREAT`. Acting on the old labels meant the agent was
> attaching when it meant to play (and vice-versa); fixing the dispatch lifted
> the fire deck's win-rate vs `random_agent` from ~43% to ~74%.

| Type | Name | Shape | Meaning |
|------|------|-------|---------|
| 0 | NUMBER | `{number}` | A count; meaning set by `select.context` (e.g. `DRAW_COUNT`) |
| 1 | YES | `{}` | "Yes" in a yes/no select (context says which question) |
| 2 | NO | `{}` | "No" in a yes/no select |
| 3 | CARD | `{area, index, playerIndex}` | Pick a card (setup actives/bench, search, discard…) |
| 4 | TOOL_CARD | `{area, index, playerIndex, toolIndex}` | Pick an attached tool card |
| 5 | ENERGY_CARD | `{area, index, playerIndex, energyIndex}` | Pick an attached energy card |
| 6 | ENERGY | `{area, index, playerIndex, energyIndex, count}` | Pick attached energy (e.g. discard for cost) |
| 7 | PLAY | `{index}` | Play a card from hand (index into hand) |
| 8 | ATTACH | `{area, index, inPlayArea, inPlayIndex}` | Attach energy to a Pokémon in play |
| 9 | EVOLVE | `{area, index, inPlayArea, inPlayIndex}` | Evolve a Pokémon in play |
| 10 | ABILITY | `{area, index}` | Use an ability |
| 11 | DISCARD | `{area, index}` | Discard a card |
| 12 | RETREAT | `{}` | Retreat the active Pokémon |
| 13 | ATTACK | `{attackId}` | Use an attack (by attack ID) |
| 14 | END | `{}` | End turn / pass |
| 15 | SKILL | `{cardId, serial}` | Use a card skill |
| 16 | SPECIAL_CONDITION | `{specialConditionType}` | Choose a special condition |

`select.type` (`SelectType`) groups which OptionTypes appear, and
`select.context` (`SelectContext`) disambiguates them — e.g. a `NUMBER` option is
`DRAW_COUNT` in one place and `DAMAGE_COUNTER_COUNT` in another. See
`cabt_enums.py` for the full `SelectType` / `SelectContext` tables, and
`docs/000_plan_engine_enum_extraction.md` for the authoritative reference.

### Area Codes (`AreaType`)

`1 DECK` · `2 HAND` · `3 DISCARD` · `4 ACTIVE` · `5 BENCH` · `6 PRIZE` ·
`7 STADIUM` · `8 ENERGY` · `9 TOOL` · `10 PRE_EVOLUTION` · `11 PLAYER` · `12 LOOKING`

> The old notes here guessed `4 = Bench`, `5 = Hand (energy)`, `7 = Prize` from a
> handful of observations — all wrong. `4 = ACTIVE`, `5 = BENCH`, `7 = STADIUM`.

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
