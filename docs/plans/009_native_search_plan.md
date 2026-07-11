# 009 — Native search API: revisiting docs/plans/008's "Out of scope" section

## The finding

`docs/plans/008_review_implementation_plan.md`'s "Out of scope" section defers
`docs/plans/008a_review_brief.md`'s Lethal Line Finder, Boss+Munkidori+attack tactical search, and
general beam search, on the grounds that "there is no exposed forward model
(`simulate_actions`/`apply_action`/`wins_game`) the agent can roll forward
speculatively... building it is a separate, large project (effectively
re-implementing... the real rules engine)."

That's not true, and we no longer have to take it on faith or reverse-engineer
it to prove it: the `ptcgProgram 22/` directory in this repo is the actual
**official competition engine source** (C++20, `Export.cpp` + headers,
Kaggle-provided, competition-use-only license — see
`ptcgProgram 22/LICENSES/`), not just the compiled `libcg.so` we load via
ctypes. Reading it directly answers every question the original version of
this doc had to speculate about from `objdump` output.

## What the source actually shows

### `SearchBegin` — exact signature (`ptcgProgram 22/Export.cpp:96`)

```cpp
const char8_t* SearchBegin(
    ApiData* data,        // agent handle from AgentStart()
    const char* serialized, int count,  // the base64 State blob — same bytes as obs["search_begin_input"]
    int* myDeck, int* myPrize,
    int* enemyDeck, int* enemyPrize, int* enemyHand, int* enemyActive,
    int manualCoin
);
```

Confirms the "~9 args" guess from disassembly, and every one is now named
and typed — no decompiler needed.

### `SearchStep` — mirrors live `Select` (`Export.cpp:134`)

```cpp
const char8_t* SearchStep(ApiData* data, long long searchId, int* select, int selectCount);
```

Same shape as the ordinary `Select(battlePtr, selects, count)` call the
agent already makes every decision — just scoped to a specific cloned
search branch (`searchId`) instead of the live battle.

### It is not MCTS — it's a forward-simulation primitive

`Search.h` (`Search::start`, `Search::step`, `Search::shuffle`) has **no
rollout policy, no iteration count, no time budget anywhere in it.** What it
does:

- `start(config, state)`: clones the current `State` into a sandbox
  (`Search::alloc`), fills in hidden zones from `config` (see below), and
  returns that clone's `searchId`.
- `step(id, selected)`: takes a previously-returned `searchId`, applies one
  `Select`-equivalent choice to *that* clone, and calls `state.step()` until
  the next decision point (`selectMax == 0` loop, same pattern as the live
  `ApiSelect`). Returns a **new** `searchId` for the resulting state — each
  step forks a new clone rather than mutating in place, so a caller can
  branch a single search into many hypothetical lines cheaply (memory pool
  is `Search::stateMemory`, a vector of `std::array<State, 128>` blocks).

So `docs/plans/008`'s framing was backwards: the engine was never going to hand us
a black-box "best move" — it hands us exactly the primitive
`simulate_actions`/`apply_action` that doc said didn't exist. Any actual
search algorithm (Lethal Line Finder's DFS, Boss+Munkidori beam search,
general MCTS if we want it) is still ours to write — but now against a
real, rules-complete `apply_action`, not a hand-rolled Python approximation
of hundreds of card effects.

### Hidden information: the caller must determinize

`SearchStartConfig` (`Search.h:19`):

```cpp
struct SearchStartConfig {
    bool manualCoin = false;
    std::vector<int> myDeck;
    std::vector<int> myPrize;
    std::vector<int> enemyDeck;
    std::vector<int> enemyPrize;
    std::vector<int> enemyHand;
    std::vector<int> enemyActive;
};
```

`SearchBegin`'s body (`Export.cpp:96-131`) only fills each array when the
real state doesn't already know that zone's contents
(`!state.selectDeck`, `IsActiveNull(...)`) — i.e. **we (the caller) must
supply a guessed, consistent assignment of card identities for every zone
we don't actually see**: the opponent's deck order, their prize cards,
their hand, and their active Pokémon if it's still hidden. `Search::start`
then stamps those guessed ids onto the clone's `allCard` array
(`Search.h:100-159`) before handing back a fully-determinized, otherwise
rules-legal `State`.

This means: no determinization = no search. Before this is usable we need a
sampler that produces a plausible, constraint-respecting guess (respecting
known deck composition minus cards we've already seen played/discarded/in
our own possession) — this is new work, not something `SearchBegin` does
for us.

### Return schema — same shape as live `obs`

`ToJsonSearch` (`ToJson.h:303-325`):

```json
{
  "state": {
    "observation": { "select": ..., "logs": ..., "current": ... },
    "searchId": 3
  } | null,
  "error": 0
}
```

`observation` is built by the same `ToJsonApi` function that produces the
live `obs` the agent already parses every decision. **This means our
existing `Ctx`/option-parsing code in `heuristics.py` (`_option_card_id`
etc.) can read search-branch observations with zero changes** — a search
node's legal options come back in the identical shape as a live decision's.

`error` is a small integer status code (0 = success; nonzero values are
assigned inline in `Search::start`/`Export.cpp`'s `CopyIdPtr` checks — e.g.
`2` = an illegal enemy-active card id, `98` = active-Pokémon-required-but-
missing-guess, `99` = uncaught C++ exception, `30` = called on the wrong
`ApiData` kind (`apiDataType` — `1` = live battle, `2` = agent/search,
enforced at the top of every `Export.cpp` API function)).

### Perspective and lifecycle

- `myIndex` (whose turn/search this is) comes from the deserialized
  `state.selectPlayer` itself — not a separate argument.
- `AgentStart()` → `ApiAgentStart()` (`Api.h:84`) allocates a fresh
  `ApiData` with `apiDataType = 2`, completely independent of any live
  `battlePtr` — confirms search runs standalone off the serialized blob
  alone, exactly what a real submission needs (it only ever has `obs`, no
  direct engine-process access to the live battle).
- `SearchEnd` → `Search::clear()`: frees all cloned states back to the pool
  but keeps the pool's memory allocated (call once per decision when done
  branching).
- `SearchRelease(agent, searchId)` → `Search::clearSingle(id)`: frees one
  specific branch early (e.g. after determining it's a dead line) without
  clearing everything.

## What's no longer unknown

Every item the original version of this doc flagged as needing a
decompiler spike is now answered directly from source:

| Original unknown | Answer |
|---|---|
| `SearchBegin`'s 9-arg layout | Fully named/typed above — no `SearchStartConfig` mystery, it's a plain struct of six `vector<int>` + a bool |
| What `SearchStep`/`SearchBegin` return | `{state: {observation, searchId} \| null, error}` — `observation` reuses the live JSON schema |
| Whose perspective it searches from | `state.selectPlayer`, read from the serialized blob itself |
| Whether it needs the live `battle_ptr` | No — `AgentStart()` is fully standalone, confirmed by source |

## What's still unknown (the real remaining risk)

- **Determinization strategy.** We must write the hidden-zone sampler
  (opponent deck/prize/hand contents, respecting known deck list minus
  seen cards) before any search call can succeed. This is genuinely new
  work — the RE spike is gone, but this replaces it as the real
  prerequisite.
- **Cost of a `start`/`step` call.** No time/iteration budget exists to
  reason about because there's no internal rollout — but we don't yet know
  the wall-clock cost of one clone-and-step call, and `remainingOverageTime`
  (600s, shared across the whole episode per `cabt.json`) still caps how
  many nodes we can afford to expand per decision across a 30-200+ decision
  game.
- **Tree management overhead in Python via ctypes.** Every node is a
  separate `searchId` behind the C API — driving a nontrivial search tree
  means many small ctypes calls; needs a real binding to measure, not
  guessed.
- **Determinism/variance across resamples.** Since we supply the hidden
  cards, a single search only explores one sampled world; a real Lethal
  Line Finder or ISMCTS-style approach needs multiple determinizations
  averaged, which multiplies the per-decision cost above.

## Phased plan

### Phase 0 — DONE (superseded)

Originally: RE spike with Ghidra to recover `SearchBegin`'s signature.
Not needed — resolved directly from `ptcgProgram 22/` source, see above.

### Phase 1 — Determinization sampler — DONE

Implemented in `src/pokemon/determinize.py` (`sample_determinization`),
tested in `tests/test_determinize.py` against both synthetic `obs` and all
14 captured real-game logs under `heuristic_loop/logs/`.

Two findings that shaped the implementation, confirmed empirically against
real captured `obs`:

- **Our own prize contents and deck order are hidden from us too** —
  `prize` entries are always `None` until taken (array *length* shrinks as
  prizes are taken; entries never reveal), matching real Pokemon TCG rules.
  So `myDeck`/`myPrize` need the same kind of guess as the opponent's zones,
  just backed by exact known composition (we submitted the 60-card list)
  rather than a placeholder.
- **`active` can be `[None]`**, not just `[]`, when a Pokemon was KO'd and
  not yet replaced — both count as "hidden, needs a guess" for
  `SearchStartConfig` purposes, not "no active Pokemon".

Opponent zones (`enemyDeck`/`enemyPrize`/`enemyHand`/`enemyActive` when
hidden) use a placeholder strategy, not real belief modeling: resample with
replacement from cards the opponent has actually revealed (board +
discard), falling back to a generic filler id before anything's revealed.
This is intentionally cruder than `tickets/PKM-015.md`'s archetype-informed
ISMCTS belief modeling — good enough for near-term consumers (a
single-turn Lethal Line Finder mostly doesn't exercise opponent hidden
identities before it terminates) without taking on PKM-015's dependency on
PKM-012's meta clusters.

**Incidental finding, not fixed here (out of scope for this doc):**
`heuristics.py`'s `prizes_remaining()` counts non-`None` prize-array
entries as "still remaining" — but real data shows entries are *always*
`None` (untaken prizes are hidden, not merely "not None"), so it always
returns `0`. `heuristics_dragapult.py`'s `_boss_orders_wins_game` (line 579)
consumes this value, so its win-detection check is currently vacuous
(`0 - prize_value(t) <= 0` is always true). Worth a follow-up ticket.

### Phase 2 — Minimal binding — BLOCKED (environment), not started

`src/pokemon/native_search.py`, a thin ctypes wrapper (mirroring
`reverse-engineering/scripts/extract_engine_data.py`'s existing pattern —
this doc originally said "`sim.py`", which doesn't exist; that script is the
actual precedent) exposing: `agent_start() -> handle`,
`search_begin(handle, search_begin_input: str, config: SearchStartConfig)
-> SearchResult`, `search_step(handle, search_id, selections: list[int]) ->
SearchResult`, `search_end(handle)`, `search_release(handle, search_id)`.
Validate against several real captured `obs["search_begin_input"]` blobs
(not just one) with the Phase 1 sampler feeding the hidden-zone arrays. No
integration into `heuristics_dragapult.py` yet — this phase is just "can we
drive it repeatably and get parseable `observation` JSON back."

Why "validate against the real engine" matters here specifically (not just
process ceremony): a search's whole value is telling us the outcome of a
*specific hypothetical* game state we can't get by reading source — that
requires executing the real rules against that state, not reasoning about
the rules in the abstract. Separately, the ctypes binding itself is an ABI
boundary (Python calling a compiled C++ library) — a wrong `argtypes`
doesn't raise a Python exception, it can silently corrupt memory or hang.
Both of those are only checkable by actually calling the library, which is
what's currently blocked:

**Blocker 1 — WSL can't start.** The precompiled engine binary this repo
already loads for live play is `libcg.so`, Linux-only, normally run under
WSL (see `heuristic_loop/eval_heuristic_change.py`'s docstring). On this
machine, `wsl.exe` currently fails to boot its VM with
`Wsl/Service/CreateInstance/CreateVm/HCS/0x80070705aa` ("insufficient
system resources") even after `wsl --shutdown`. Needs troubleshooting
outside this repo (Hyper-V/VM platform state, available memory, possibly a
reboot) before the `.so` path is usable again.

**Discovery — we don't actually need WSL for this.** `ptcgProgram 22/`
isn't just headers to read for signatures — it's a complete, buildable,
dependency-free Visual Studio 2022 solution (`game.sln` / `game.vcxproj`,
`README.md`'s "Build notes": C++20, header-only style, "no third-party or
open-source dependencies"). `game.vcxproj`'s `ConfigurationType` is
`DynamicLibrary`, output name `cg$(TargetExt)` — i.e. building it produces
our own `cg.dll`, the exact Windows counterpart of the `libcg.so` we
already load via ctypes. This is a strictly better path than WSL for local
dev: native, no VM, same source that produced the competition binary.

**Blocker 2 — MSVC toolchain isn't installed.** `MSBuild.exe` exists
(`C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe`),
but there's no `VC\Tools\MSVC` under the VS2022 Community install — the
actual C++ compiler/toolset was never installed, only base MSBuild
scaffolding. Needs the "Desktop development with C++" workload added via
the Visual Studio Installer (a few GB, requires interactive
click-through/elevation — not something to script unattended).

**Next session:** pick one — install the C++ workload and build `cg.dll`
natively (recommended, no WSL dependency going forward), or get WSL's VM
booting again and use the existing `libcg.so`. Either unblocks the same
next step: compile/obtain a working binary, then write and run
`native_search.py` against it.

### Phase 3 — Write the actual search algorithm

Now that `observation` decodes through the existing `Ctx`/option-parsing
code, build the specific searches `docs/plans/008a_review_brief.md` wants on top of
`search_begin`/`search_step`:

- **Lethal Line Finder:** bounded-depth DFS from the current node, using
  `search_step` per candidate action, terminating on a winning `current`
  state or depth limit.
- **Boss+Munkidori+attack tactical search:** same DFS shape, narrower — only
  triggered when those specific cards are in hand/available.
- General beam search stays explicitly out of scope until the two narrow
  cases above are validated — same "don't build ahead of evidence"
  discipline as `docs/plans/008`.

### Phase 4 — Budget-aware integration

Gate native search behind a cheap pre-filter, not "every decision" — reuse
the existing `Ctx`/heuristic-ordering machinery so `heuristics_dragapult.py`
tries a fast heuristic first and only reaches for native search on the
genuinely hard tactical spots `docs/plans/008a_review_brief.md` flagged. Track cumulative time
spent against `obs["remainingOverageTime"]` and stop calling search once
the budget gets tight, falling back to existing heuristics for the rest of
the game — same "degrade to None/random rather than guess wrong" discipline
the rest of this codebase already follows.

### Phase 5 — Validate

Same discipline as every other change in this loop:
`heuristic_loop/eval_heuristic_change.py` for win-rate delta, n>=120 given
how noisy smaller runs have been — plus explicit latency logging, since a
native-code integration risks a new failure mode (timeout disqualification)
that pure-Python heuristic changes don't have.

## Recommendation

The blocking uncertainty this doc originally worried about (an undecodable
C ABI) is gone — the source removes it entirely. The real next piece of
work is Phase 1 (determinization), which is a bounded, well-specified
Python task, not open-ended RE. Worth starting directly.

## Relationship to docs/plans/008

Supersedes docs/plans/008's "Out of scope (search infra)" section's blocking
assumption ("not being built until/unless a real forward model exists")
with: a forward model exists, confirmed from the official engine source
(`ptcgProgram 22/`), not just inferred from disassembly. The prerequisite
to using it is a determinization sampler (Phase 1 above), not a rules-engine
rewrite and not a reverse-engineering spike. `docs/plans/008`'s Phase 1-3
heuristic work stands regardless of how this plays out; that's the fallback
path if this doesn't pan out.
