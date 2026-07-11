# 000 — Plan: Decode CABT selections via the engine's real enums

**Status:** proposed
**Owner:** unassigned
**Prereqs:** none (the agent runs today: `uv run pokemon-play -v`; code in `src/pokemon/`)

> This is an execution plan written to be handed to an LLM agent. It contains
> all the context needed to start cold. Read the whole "Context" section before
> touching code. Do the work in phases; Phase 1 alone delivers most of the
> value. Phases 3–4 are optional binary reverse-engineering and should only be
> started if Phase 2 leaves real gaps.

---

## Problem in one sentence

Our agent labels and scores game options from a **hand-coded integer→string
map** that is incomplete and ignores the `context` field the engine already
sends — so genuinely different choices collapse to the same label (the
notorious "OK OK OK OK"), and the agent cannot tell them apart to choose well.

## Goal

Replace the guesswork with the engine's **real enums** (`SelectType`,
`SelectContext`, `OptionType`, `AreaType`, …), have the agent read
`select.type` + `select.context` (not just `option.type`), and optionally
verify the enum tables against the shipped binary. Outcome: every option is
labeled unambiguously and the scorer can branch on the true selection context.

## Non-goals

- Rewriting the scoring heuristics' *strategy* (only the plumbing that feeds them).
- Redistributing or modifying `libcg.so`. This is interoperability RE on a file
  we already have locally; keep it read-only.
- Building a full decompilation of the engine. Phases 3–4 are surgical.

---

## Context (verified — trust this over memory)

### What the engine is
- The simulator is a native library: `.venv/lib/python3.14/site-packages/kaggle_environments/envs/cabt/cg/libcg.so`
  (and `cg.dll`, the Windows build of the same engine).
- `libcg.so`: **x86-64 ELF, C++, NOT stripped** (~614 symbols, 99 exported,
  BuildID `54a6c3a9…`). Not-stripped means real function names survive, e.g.
  `State::addOption(SelectOptionType)` (see `reverse-engineering/data/all_symbols.txt`).
- The engine **serializes observations to JSON itself**. Python just
  `json.loads()` the C string — see `cg/game.py:_get_battle_data`. So every
  field we care about already crosses the boundary as JSON.

### The ABI (entire surface — from `cg/sim.py`)
```
GameInitialize()
BattleStart(int* decks[120]) -> StartData{ battlePtr, errorPlayer, errorType }   # 60+60 card IDs
GetBattleData(battlePtr)     -> SerialData{ json (char*), data, count, selectPlayer }
Select(battlePtr, int* choice, n) -> int err   # err==30 => battle_ptr broken; else IndexError
BattleFinish(battlePtr)
VisualizeData(battlePtr)     -> char*          # alternate JSON stream for the visualizer
```
Decks must be exactly 60 cards each (`game.py:battle_start`).

### What the agent does today (`src/pokemon/`)
- Reads `obs["select"]["option"]` and `["maxCount"]`. **It never reads
  `select["type"]` or `select["context"]`.** ← root cause.
- `pokemon.catalog.format_option(opt, hand)` is a hand-written `if opt["type"] == N`
  chain that maps `OptionType` ints to strings. `type == 0` returns `"OK"` (now
  `OK#<number>`).
- `pokemon.agent.score_option(...)` branches on `opt["type"]` only; type 0 gets a
  flat 20.0, so the agent picks the first NUMBER option blindly.
- Card/attack names already resolve via the full catalogs
  (`reverse-engineering/data/all_cards.json`, `all_attacks.json`) — see
  `pokemon.catalog.card_name` / `atk_name`. That part is done; do not redo it.

### The key insight
`OptionType.NUMBER = 0` is **disambiguated by `SelectContext`**, which the engine
sends in `select.context`. e.g. the same `type:0` option means
`DRAW_COUNT (38)` in one spot and `DAMAGE_COUNTER_COUNT (39)` in another. The
information to label/score "OK#n" correctly is **already in the JSON we ignore.**

### Authoritative enum source
The upstream engine docs (mirrored in `## Enum reference` below) define every
enum. There is **no Python `api.py` vendored locally** — the docs describe the
standalone package, so treat the tables below as the spec and verify them
empirically (Phase 2) rather than assuming the vendored build is identical.

---

## Plan

### Phase 1 — Encode the enums + read `type`/`context` (high value, no RE)

1. Create `src/pokemon/cabt_enums.py` with `IntEnum`s transcribed from the
   `## Enum reference` section: `AreaType`, `EnergyType`, `CardType`,
   `SpecialConditionType`, `SelectType`, `SelectContext`, `OptionType`,
   `LogType`. Use `IntEnum` so existing int comparisons keep working, and add a
   `safe(cls, value)` helper that returns the member or a sentinel for unknown
   ints (forward-compat if the build has extras).
2. In `pokemon.agent.fire_agent`, pull `sel_type = select.get("type")` and
   `context = select.get("context")`, and **log them** in the verbose turn
   header, e.g. `Choices (4, pick 1) [SelectType.COUNT / SelectContext.DRAW_COUNT]:`.
3. Rewrite `pokemon.catalog.format_option` to take `context` and use the enums:
   - `OptionType.NUMBER` → render `f"{context.name}={opt['number']}"`
     (e.g. `DRAW_COUNT=2`) instead of `OK#n`.
   - `OptionType.CARD` (3) → use `AreaType(opt['area']).name` + the catalog name.
   - Cover the option types we currently miss: `TOOL_CARD(4)`, `ENERGY_CARD(5)`,
     `ENERGY(6)`, `EVOLVE(9)`, `ABILITY(10)`, `DISCARD(11)`, `RETREAT(12)`,
     `SKILL(15)`, `SPECIAL_CONDITION(16)`. (Note: the doc's `OptionType` numbering
     is the ground truth; our old labels in `format_option` were partly wrong —
     reconcile against the reference, do not trust the old `if t == …` numbers.)
4. Make `score_option` context-aware where it matters (at minimum: pick the
   sensible end of a `COUNT` selection per its `SelectContext` — usually max for
   DRAW_COUNT, situational for damage counters).

**Watch out:** the old `format_option` predates the docs and may have
mislabeled types (it was reverse-engineered by observation). When the reference
table and the old code disagree on what an integer means, **the reference wins**;
flag the discrepancy in the PR description.

### Phase 2 — Empirically verify the tables against the live engine

5. Extend `reverse-engineering/scripts/explore_cabt_deep.py` (or add
   `verify_enums.py`) to drive many games with varied decks and assert that
   every observed `select.type`, `select.context`, and `option.type` is a known
   enum member; log any unknown ints with a sample observation.
6. Build a coverage report: which `SelectContext` values were actually seen.
   Rare ones (devolve, special-condition picks, prize selection) need decks that
   trigger them — note the gaps; do not claim full coverage without evidence.
7. If an unknown int appears, that's the signal the vendored build diverges from
   the docs → escalate to Phase 3 for that specific value only.

### Phase 3 — Binary verification (optional; only for gaps Phase 2 found)

Enum *member names* are NOT in the binary (C++ discards them), so do not try to
`strings` them out. Use these to confirm *values/behavior*:

- **Static surface map (cheap):**
  ```bash
  file cg/libcg.so
  readelf -hSd cg/libcg.so
  nm -DC cg/libcg.so                       # exported API, demangled
  nm  -C cg/libcg.so | grep -iE 'addOption|Select|Context|Serial|Observation'
  nm  -C cg/libcg.so | grep -i typeinfo    # RTTI → C++ class names = data model
  strings -a -t x -n 5 cg/libcg.so | grep -iE '"type"|"context"|attackId|cardId'
  ```
- **Dynamic (fastest for real values):** hook the un-stripped builder and watch
  the integers flow across many games — empirical, at the C++ boundary:
  ```bash
  # gdb
  gdb --args .venv/bin/python -m pokemon -g 1 -v
  #   break State::addOption ; run ; info args ; bt
  # Frida (auto-harvest every (context, optionType) the engine produces)
  frida-trace -i 'Select' -i 'GetBattleData' -p $(pgrep -f 'm pokemon')
  #   resolve internal addOption via DebugSymbol.fromName in a JS hook
  ```
- **Static decompile (only if needed):** load `libcg.so` in Ghidra
  (`analyzeHeadless` for scripting), read the JSON serializer / `switch(context)`
  to recover the integer constants per branch.

### Phase 4 — Pull data tables from the binary (optional, independent value)

Cross-check `all_cards.json` / `all_attacks.json` against the engine's own
static arrays in `.rodata` (find the `all_card_data` accessor, recover the
struct layout, dump). Useful to detect drift between the data dump and the
shipped build. Tools: Ghidra, `objdump -s -j .rodata`, `rizin -A`.

---

## Files

| Path | Role |
|------|------|
| `src/pokemon/cabt_enums.py` | **new** — IntEnum transcription of the reference |
| `src/pokemon/catalog.py` | edit — rewrite `format_option` to take `context` and use the enums |
| `src/pokemon/agent.py` | edit — read `select.type`/`context`; make `score_option` context-aware |
| `reverse-engineering/scripts/verify_enums.py` | **new** — Phase 2 empirical verifier |
| `docs/CABT.md` | update the "Select Option Types" table to match the real enums |

---

## Acceptance criteria

- [ ] `cabt_enums.py` exists; `python -c "from pokemon.cabt_enums import *"` imports clean.
- [ ] Verbose log shows `SelectType` + `SelectContext` per decision, and former
      "OK#n" options now read as their context (e.g. `DRAW_COUNT=2`).
- [ ] No `?type=N` or bare `OK` left in `format_option` output across a 50-game
      verbose run.
- [ ] Phase 2 verifier runs N games and reports **zero** unknown enum ints (or
      explicitly lists the unknowns + coverage gaps).
- [ ] `docs/CABT.md` option-type table reconciled with the reference; any place
      the old code was wrong is called out.
- [ ] `ruff check` / `ruff format --check` pass; one verbose game still completes.

---

## Enum reference (transcribe these — authoritative)

Source: upstream `cabt` engine API docs. IDs are the integer values that appear
in the JSON. Where the old `format_option` disagrees, **this wins.**

### SelectType — `select.type` (which OptionTypes appear)
`0 MAIN` (PLAY/ATTACH/EVOLVE/ABILITY/DISCARD/RETREAT/ATTACK/END) ·
`1 CARD` · `2 ATTACHED_CARD` · `3 CARD_OR_ATTACHED_CARD` · `4 ENERGY` ·
`5 SKILL` · `6 ATTACK` · `7 EVOLVE` · `8 COUNT` (NUMBER) · `9 YES_NO` ·
`10 SPECIAL_CONDITION`

### OptionType — `select.option[*].type` (+ associated fields)
| ID | Name | Fields |
|----|------|--------|
| 0 | NUMBER | `number` |
| 1 | YES | — |
| 2 | NO | — |
| 3 | CARD | `area, index, playerIndex` |
| 4 | TOOL_CARD | `area, index, playerIndex, toolIndex` |
| 5 | ENERGY_CARD | `area, index, playerIndex, energyIndex` |
| 6 | ENERGY | `area, index, playerIndex, energyIndex, count` |
| 7 | PLAY | `index` (hand) |
| 8 | ATTACH | `area, index, inPlayArea, inPlayIndex` |
| 9 | EVOLVE | `area, index, inPlayArea, inPlayIndex` |
| 10 | ABILITY | `area, index` |
| 11 | DISCARD | `area, index` |
| 12 | RETREAT | — |
| 13 | ATTACK | `attackId` |
| 14 | END | — |
| 15 | SKILL | `cardId, serial` |
| 16 | SPECIAL_CONDITION | `specialConditionType` |

> NOTE the divergence from our old map: the old `format_option` treated
> `7=ATTACH, 8=USE, 3=PLAY`. The real engine is `7=PLAY, 8=ATTACH`. Reconcile.

### SelectContext — `select.context` (the disambiguator; SelectType in parens)
`0 MAIN(MAIN)` · `1 SETUP_ACTIVE_POKEMON(CARD)` · `2 SETUP_BENCH_POKEMON(CARD)` ·
`3 SWITCH(CARD)` · `4 TO_ACTIVE(CARD)` · `5 TO_BENCH(CARD)` · `6 TO_FIELD(CARD)` ·
`7 TO_HAND(CARD)` · `8 DISCARD(CARD)` · `9 TO_DECK(CARD)` · `10 TO_DECK_BOTTOM(CARD)` ·
`11 TO_PRIZE(CARD)` · `12 NOT_MOVE(CARD)` · `13 DAMAGE_COUNTER(CARD)` ·
`14 DAMAGE_COUNTER_ANY(CARD)` · `15 DAMAGE(CARD)` · `16 REMOVE_DAMAGE_COUNTER(CARD)` ·
`17 HEAL(CARD)` · `18 EVOLVES_FROM(CARD)` · `19 EVOLVES_TO(CARD)` · `20 DEVOLVE(CARD)` ·
`21 ATTACH_FROM(CARD)` · `22 ATTACH_TO(CARD)` · `23 DETACH_FROM(CARD)` · `24 LOOK(CARD)` ·
`25 EFFECT_TARGET(CARD)` · `26 DISCARD_ENERGY_CARD(ATTACHED_CARD)` ·
`27 DISCARD_TOOL_CARD(ATTACHED_CARD)` · `28 SWITCH_ENERGY_CARD(ATTACHED_CARD)` ·
`29 DISCARD_CARD_OR_ATTACHED_CARD(CARD_OR_ATTACHED_CARD)` · `30 DISCARD_ENERGY(ENERGY)` ·
`31 TO_HAND_ENERGY(ENERGY)` · `32 TO_DECK_ENERGY(ENERGY)` · `33 SWITCH_ENERGY(ENERGY)` ·
`34 SKILL_ORDER(SKILL)` · `35 ATTACK(ATTACK)` · `36 DISABLE_ATTACK(ATTACK)` ·
`37 EVOLVE(EVOLVE)` · `38 DRAW_COUNT(COUNT)` · `39 DAMAGE_COUNTER_COUNT(COUNT)` ·
`40 REMOVE_DAMAGE_COUNTER_COUNT(COUNT)` · `41 IS_FIRST(YES_NO)` · `42 MULLIGAN(YES_NO)` ·
`43 ACTIVATE(YES_NO)` · `44 FIRST_EFFECT(YES_NO)` · `45 MORE_DEVOLVE(YES_NO)` ·
`46 COIN_HEAD(YES_NO)` · `47 AFFECT_SPECIAL_CONDITION(SPECIAL_CONDITION)` ·
`48 RECOVER_SPECIAL_CONDITION(SPECIAL_CONDITION)`

### AreaType — `option.area`, `inPlayArea`, `Log.fromArea`
`1 DECK` · `2 HAND` · `3 DISCARD` · `4 ACTIVE` · `5 BENCH` · `6 PRIZE` ·
`7 STADIUM` · `8 ENERGY` · `9 TOOL` · `10 PRE_EVOLUTION` · `11 PLAYER` · `12 LOOKING`

### EnergyType
`0 COLORLESS` · `1 GRASS` · `2 FIRE` · `3 WATER` · `4 LIGHTNING` · `5 PSYCHIC` ·
`6 FIGHTING` · `7 DARKNESS` · `8 METAL` · `9 DRAGON` · `10 RAINBOW` · `11 TEAM_ROCKET`

### CardType
`0 POKEMON` · `1 ITEM` · `2 TOOL` · `3 SUPPORTER` · `4 STADIUM` · `5 BASIC_ENERGY` · `6 SPECIAL_ENERGY`

### SpecialConditionType
`0 POISON` · `1 BURN` · `2 SLEEP` · `3 PARALYZE` · `4 CONFUSE`

### LogType — `Log.type` (events since last selection; `obs.logs`)
`0 SHUFFLE` · `1 HAS_BASIC_POKEMON` · `2 TURN_START` · `3 TURN_END` · `4 DRAW` ·
`5 DRAW_REVERSE` · `6 MOVE_CARD` · `7 MOVE_CARD_REVERSE` · `8 SWITCH` · `9 CHANGE` ·
`10 PLAY` · `11 ATTACH` · `12 EVOLVE` · `13 DEVOLVE` · `14 MOVE_ATTACHED` · `15 ATTACK` ·
`16 HP_CHANGE` · `17 POISONED` · `18 BURNED` · `19 ASLEEP` · `20 PARALYZED` ·
`21 CONFUSED` · `22 COIN` · `23 RESULT` (`result`: 0=p0 win, 1=p1 win, 2=draw;
`reason`: 1=no prizes, 2=no deck, 3=no active, 4=card effect)

### Selected `SelectData` / `State` fields worth reading
- `SelectData`: `type, context, minCount, maxCount, remainDamageCounter,
  remainEnergyCost, option[], deck, contextCard, effect`.
- `State`: `turn, yourIndex, firstPlayer, supporterPlayed, stadiumPlayed,
  energyAttached, retreated, result, stadium, looking, players[2]`.
- `PlayerState`: `active[0..1], bench, benchMax, deckCount, discard, prize,
  handCount, hand|None, poisoned/burned/asleep/paralyzed/confused`.

---

## References
- `docs/CABT.md` — current (partly reverse-engineered, partly wrong) notes.
- `cg/sim.py`, `cg/game.py` — the ctypes ABI boundary.
- `reverse-engineering/data/` — symbol dumps, card/attack JSON, ELF sections.
- `reverse-engineering/scripts/explore_cabt_deep.py` — existing option-type catalog.
- Upstream engine API docs — origin of the enum tables above.
