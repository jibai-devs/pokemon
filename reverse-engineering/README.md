# Reverse Engineering libcg.so — CABT Pokémon TCG Engine

## What is libcg.so?

The compiled C++ game engine for the Pokémon TCG AI Battle competition. It runs the full game rules — card effects, damage calculation, status conditions, coin flips, search/targeting, and the MCTS search API. It's loaded by Python via `ctypes.cdll.LoadLibrary()`.

**Location:** `data/sample_submission/cg/libcg.so`

---

## How to extract data — the commands

### 1. `file` — identify the binary
```bash
file data/sample_submission/cg/libcg.so
# ELF 64-bit LSB shared object, x86-64, dynamically linked, not stripped
```

### 2. `nm` — list symbols (function/variable names)
```bash
# Exported (dynamic) symbols only
nm -D libcg.so | grep " T "

# ALL symbols including internal (.symtab)
nm libcg.so

# Demangle C++ names
nm --demangle libcg.so | grep " T "

# Global variables (BSS/Data/Readonly)
nm --demangle libcg.so | grep -E " [BbDdRr] "
```

Symbol types: `T` = code, `B`/`b` = uninitialized data, `D`/`d` = initialized data, `U` = undefined (imported from other libs)

### 3. `strings` — extract readable text from the binary
```bash
# All strings
strings libcg.so

# Minimum length filter
strings -n 4 libcg.so

# Game-specific terms
strings libcg.so | grep -i "attack\|damage\|energy"

# Internal C++ function names (mangled, then demangled)
strings libcg.so | grep "^_Z" | c++filt
```

The mangled `_Z...` names in the strings section come from RTTI, exception handling, and template instantiations — they reveal the full internal function API even though the binary is stripped of local symbols.

### 4. `c++filt` — demangle C++ names
```bash
echo "_Z10CalcDamageRK5Statei7CardRefRK4CardS2_S5_bPK6Attack" | c++filt
# → CalcDamage(State const&, int, CardRef, Card const&, CardRef, Card const&, bool, Attack const*)
```

### 5. `readelf` — inspect ELF structure
```bash
readelf -S libcg.so   # Section headers
readelf -h libcg.so   # ELF header
readelf -d libcg.so   # Dynamic dependencies
```

### 6. `ldd` — shared library dependencies
```bash
ldd libcg.so
# → libstdc++.so.6, libgcc_s.so.1, libc.so.6
```

### 7. Python `ctypes` — call functions directly
```python
import ctypes
lib = ctypes.cdll.LoadLibrary("libcg.so")
lib.GameInitialize()

lib.AllCard.restype = ctypes.c_char_p
cards_json = lib.AllCard().decode("utf-8")  # returns JSON string

lib.AllAttack.restype = ctypes.c_char_p
attacks_json = lib.AllAttack().decode("utf-8")
```

---

## Extracted data files

| File | Description | Records |
|---|---|---|
| `data/all_cards.json` | Full card database | 1,267 cards |
| `data/all_attacks.json` | Full attack database | 1,556 attacks |
| `data/exported_symbols.txt` | 13 exported C functions | 99 lines |
| `data/all_symbols.txt` | Full symbol table (.symtab) | 614 symbols |
| `data/internal_functions.txt` | Demangled internal C++ functions | 452 functions |
| `data/game_strings.txt` | Game-related strings from binary | 1,598 strings |
| `data/elf_sections.txt` | ELF section headers | 74 lines |
| `data/ldd_output.txt` | Shared library dependencies | 7 lines |

---

## Data schemas

### Card (all_cards.json)

| Field | Type | Meaning |
|---|---|---|
| `cardId` | int | Unique ID (used in deck.csv) |
| `name` | string | Card name |
| `cardType` | int | 0=Pokemon, 1=Item, 2=Tool, 3=Supporter, 4=Stadium, 5=Basic Energy, 6=Special Energy |
| `pokemonType` | int | 0=Energy/None, 1=Normal, 2=Fossil, 3=ex, 4=Mega ex |
| `energyType` | int | 0=None, 1=Grass, 2=Fire, 3=Water, 4=Lightning, 5=Psychic, 6=Fighting, 7=Darkness, 8=Metal, 9=Dragon, 10=Fairy |
| `hp` | int | Hit points (0 for non-Pokemon, 30–380 for Pokemon) |
| `weakness` | int/null | Energy type code |
| `resistance` | int/null | Energy type code |
| `retreatCost` | int | Energy cards to retreat |
| `basic` | bool | Is Basic stage |
| `stage1` | bool | Is Stage 1 |
| `stage2` | bool | Is Stage 2 |
| `ex` | bool | Is Pokemon ex |
| `megaEx` | bool | Is Mega ex |
| `tera` | bool | Is Tera Pokemon |
| `aceSpec` | bool | Is ACE SPEC card |
| `evolvesFrom` | string/null | Name of pre-evolution |
| `skills` | array | Abilities: `[{name, text}]` |
| `attacks` | int[] | Attack IDs (reference all_attacks.json) |

### Attack (all_attacks.json)

| Field | Type | Meaning |
|---|---|---|
| `attackId` | int | Unique ID |
| `name` | string | Attack name |
| `text` | string | Full English effect description |
| `damage` | int | Base damage (0–350) |
| `energies` | int[] | Cost — codes: 0=Colorless, 1=Grass, 2=Fire, 3=Water, 4=Lightning, 5=Psychic, 6=Fighting, 7=Darkness, 8=Metal |

### Energy type codes

| Code | Type |
|---|---|
| 0 | Colorless |
| 1 | Grass |
| 2 | Fire |
| 3 | Water |
| 4 | Lightning |
| 5 | Psychic |
| 6 | Fighting |
| 7 | Darkness |
| 8 | Metal |
| 9 | Dragon |
| 10 | Fairy |

### Card type codes

| Code | Type | Count |
|---|---|---|
| 0 | Pokemon | 1,056 |
| 1 | Item | 77 |
| 2 | Tool | 27 |
| 3 | Supporter | 61 |
| 4 | Stadium | 26 |
| 5 | Basic Energy | 8 |
| 6 | Special Energy | 12 |

---

## Exported C API (13 functions)

| Function | Signature | Purpose |
|---|---|---|
| `GameInitialize()` | `void()` | Init engine, load card database |
| `BattleStart(int*)` | `StartData(int[120])` | Start battle with two 60-card decks |
| `BattleFinish(void*)` | `void(battlePtr)` | Free battle memory |
| `GetBattleData(void*)` | `SerialData(battlePtr)` | Get current game state as JSON |
| `Select(void*, int*, int)` | `int(battlePtr, selects, count)` | Submit agent's choice |
| `VisualizeData(void*)` | `char*(battlePtr)` | Get HTML replay data |
| `AllCard()` | `char*()` | JSON of all 1,267 cards |
| `AllAttack()` | `char*()` | JSON of all 1,556 attacks |
| `AgentStart()` | `void*()` | Create search agent |
| `SearchBegin(...)` | `char*(...)` | Start MCTS search |
| `SearchStep(...)` | `char*(...)` | Step MCTS search |
| `SearchEnd(void*)` | `void(agentPtr)` | End search |
| `SearchRelease(void*, int64)` | `void(agentPtr, searchId)` | Release search memory |

---

## Internal C++ architecture (from demangled strings)

### Game flow
`SetupGame` → `TurnStart` → `MainSelect` → `SelectCard` → `AttackDamage` → `AttackEffect` → `AfterAttack` → `TurnEnd` → `PokemonCheckup`

### State machine
The engine uses a **function pointer stack** pattern:
- `State::pushFunction(fn)` — push next action
- `State::step()` — execute top function
- `State::callFunction()` — dispatch
- `State::setSelect(type, ...)` — present choices to agent

### Key internal functions

| Category | Functions |
|---|---|
| **Damage** | `CalcDamage`, `AddDamage`, `AttackDamage`, `EffectAttackDamage` |
| **Status** | `EffectBurn`, `EffectPoison`, `EffectSleep`, `BurnProc`, `SleepProc`, `ConfuseProc`, `ParalyzeProc` |
| **Card movement** | `MoveCard`, `MoveRefCard`, `AttachProc`, `EvolveProc`, `DevolveProc` |
| **Selection** | `SelectCard`, `SelectActivePokemon`, `SelectSwitchPokemon`, `SelectPokemonEnergy`, `SelectPrize` |
| **Triggers** | `PullTrigger`, `TriggerList`, `AfterAttack`, `AfterDamage`, `AfterAbility`, `AfterRetreat` |
| **Chain (card effects)** | `Chain::attack`, `Chain::ability`, `Chain::condition`, `Chain::effectDraw`, `Chain::effectTrashEnergy` |
| **Search (MCTS)** | `Search::start`, `Search::alloc` |
| **Serialization** | `CardJson`, `PlayerJson`, `PokemonJson`, `LogJson`, `SelectJson` |

### Global data tables (in BSS)
- `CardTable` — `unordered_map<int, CardMaster>`
- `AttackTable` — `unordered_map<int, Attack>`
- `FunctionTable` — game function registry
- `SkillTable` — ability/skill definitions
- `NameTable` — card name strings
- `AllCardJson` / `AllAttackJson` — cached JSON strings

---

## How to hook / trace calls

### Monkey-patch in Python (easiest)
```python
# In sim.py, after lib = ctypes.cdll.LoadLibrary(...)
_original_select = lib.Select
def _traced_select(bp, selects, count):
    print(f"[TRACE] Select: count={count}")
    import traceback; traceback.print_stack()
    return _original_select(bp, selects, count)
lib.Select = _traced_select
```

### LD_PRELOAD shim (C level)
```c
// trace_shim.c
#include <dlfcn.h>
#include <stdio.h>
int Select(void* bp, int* s, int c) {
    fprintf(stderr, "[HOOK] Select(%p, %d)\n", bp, c);
    int (*real)(void*,int*,int) = dlsym(RTLD_NEXT, "Select");
    return real(bp, s, c);
}
```
```bash
gcc -shared -fPIC -o trace_shim.so trace_shim.c -ldl
LD_PRELOAD=./trace_shim.so python run_battle.py
```

### GDB (native debugging)
```bash
gdb -ex "break Select" -ex "run" --args python run_battle.py
```
