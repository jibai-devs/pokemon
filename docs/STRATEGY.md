# The Strategy, in Plain Language

**Last updated: 2026-07-12** (after plan 011 Phases 1–2, the matchup-identification module split, and the hand-verified archetype-core reference)

This is the "explain it to me like I stepped away for a month" view of the project.
No jargon without a definition, no detail that doesn't change a decision. The
technical counterparts are `AGENTS.md` (full reference) and `docs/plans/` (execution
plans). **Keep this file updated whenever the strategy meaningfully changes** — it's
the map, not the territory.

---

## The goal

Win (or place well in) the Kaggle Pokémon TCG AI Battle competition. Prize money is
in the linked *Strategy* competition, which scores agent performance (70%), deck
choice rationale (20%), and report quality (10%) — so a middle-of-leaderboard bot
with excellent analysis can still win money. Deadlines: simulation entry **Aug 9,
2026**, final submission **Aug 16**, writeup **Sep 13**.

## What we have

**1. A bot that plays Dragapult using a checklist of rules.**
`src/pokemon/heuristics_dragapult.py` is a big ordered checklist. Every time the
game asks "what do you do?", the bot walks down the list — evolve? attach energy?
which attack? who to hit? — and the first rule with an opinion wins. If no rule
fires, it picks randomly. This is the whole agent, and it works: measured at **61%
win rate** (up from 42%).

**2. A feedback loop that makes the bot better.** (`heuristic_loop/`)
Play ~30 games → collect the losses → read them and find dumb decisions → fix a
rule → re-measure win rate to prove the fix helped. Nothing is "kept" without a
measured before/after delta. This loop produced the 42% → 61% jump and is the
project's most valuable asset. **Golden rule: no heuristic change ships on vibes.**

**3. A deck detector that figures out what the opponent is playing.**
(`src/pokemon/deck_id.py`, fed by the library in `data/meta_decks/library.json`)
It watches every card the opponent reveals and matches against a library of known
decks. Three levels of knowledge:
- **Level 1:** "I know their exact 60 cards."
- **Level 2:** "I know which archetype (deck family) they're playing."
- **Level 3:** "No idea yet."

The library has two halves:
- **~137 real opponent decks**, extracted from our 1,500 downloaded replays. Our
  Kaggle opponents are other competitors' fixed submissions — a small, knowable
  set, not an infinite space. This half identifies today's actual opponents.
- **179 human tournament decks** (scraped from a real 179-player Regional). Mostly
  useless *today* (bots don't play tournament lists), but kept for the endgame: if
  competitors netdeck real lists near the deadline, this half becomes relevant.
  Re-weighting between the halves is one command.

Current accuracy (measured over 3,000 games): knows the **archetype by turn 2** in
92% of games, knows the **exact 60 cards by turn ~7** in 40% of games — and when it
claims an exact match, it has never been wrong.

**Guardrail (decided 2026-07-12): the replay decks are for *recognition only*.**
They're the detector's photo album — a photo only ever matches an opponent actually
playing that deck, and sits inert otherwise — so they cost nothing against better
opponents. But we do **not** invest hand-crafted strategy in them: any hand-written
matchup knowledge (priority targets, playbooks) is written for **human-tournament
archetypes only**, because low-elo bot brews are expected to vanish as we climb and
as the meta netdecks toward the deadline. Bot brews get *computed* knowledge only
(threat facts derived automatically from their identified list). Note: the old
hand-written signature/target table (`TIER5_SIGNATURES`) predates this rule and IS
keyed to bot-meta decks — it's kept as a working fallback but not extended.

**4. The detector now actually changes behavior** (new, pending final validation).
"Who do I attack first" (Boss's Orders pulls, Phantom Dive bench spread) now uses
the detector's prediction, which resolves by ~turn 2 — before the old system (which
had to physically *see* a signature Pokémon on the board) could react. The old
system remains as a fallback, so knowledge is only ever gained earlier, never lost.
This "who is my opponent" logic now lives in its own file
(`src/pokemon/dragapult_matchups.py`), separate from the "what do I do about it"
decision rules — a pure reorganization, not a behavior change.

**5. A hand-verified reference for what actually defines each human archetype.**
(`docs/tournament_archetype_cores.md`) Early attempts to compute "core cards" from
raw presence statistics kept surfacing format-wide staples (cards nearly every deck
runs) instead of a deck's actual identity, so this list is hand-picked instead —
e.g. Dragapult's identity is just Dragapult ex, not the seven cards that happened to
be common across its lists. Checking this against the bot pool found something
useful: the 5 human archetypes we'd already hand-written matchup knowledge for
(back when the signature table was first built) cover **~59% of all bot
game-instances**, while every archetype we *haven't* written knowledge for adds up
to only ~1.3% combined. So expanding hand-written matchup knowledge further isn't
worth it against today's bot pool — it becomes worth it once the meta shifts toward
human-tournament lists, which is exactly the scenario this reference is for.

**6. A full-information sanity check on the archetype-core reference.**
(`scripts/classify_replay_decks.py`, `data/meta_decks/archetype_core_match_report.txt`)
The detector (point 3) has to guess archetype from a *partial* reveal mid-game — a
harder problem than the question "does this reference doc even cover what our
opponents actually play?" This script answers the easier question directly: since
every replay already exposes both players' full 60-card lists, just check whether
each deck's Pokémon contain a known archetype's core, no guessing involved. First
run found the hand-verified reference only covered **60%** of bot game-instances;
the other 40% turned out to be real, recurring decks nobody had named yet
(Archaludon ex, Hop's Phantump, Iono's Bellibolt, Spheal/Walrein, Crustle,
Comfey, Mega Abomasnow, Ethan's Cyndaquil) — not noise. Adding those 8 entries to
`docs/tournament_archetype_cores.md` brought coverage to **98%** of game-instances
(2% genuinely ambiguous — decks that legitimately run two cores at once — and <1%
truly unclassified). This is an offline diagnostic on the reference doc itself,
not a change to the live in-game detector (`deck_id.py` still does incremental
partial-reveal matching against `library.json`, unaffected).

## The core insight everything rests on

**Our opponent pool is a lookup table, not an infinite space.** Every opponent is
another competitor's fixed 60-card submission, and replays reveal full decklists.
Identify the list → know all 60 cards → most "skill" (what can they do next turn?
do they still have Boss's Orders? is my bench safe?) becomes *computable* instead
of guessable. That's the moat we're building; most competitors won't bother.

## What's next, in order

1. **One WSL eval run** (blocked: WSL won't start until reboot/RAM freed):
   `uv run python heuristic_loop/eval_heuristic_change.py -g 60 --old-ref HEAD` —
   validates the detector-driven targeting (keep or revert), then commit.
2. **Phase 3 — computed threat awareness:** from the identified list, compute what
   the opponent can actually do next turn (max damage, gust effects left, bench
   snipe) and feed it into bench/retreat/heal decisions. One decision point at a
   time, each measured.
3. **Keep the feedback loop running** against fresh losses — still the main lever
   on ladder rank.
4. **Phase 4 decision (later):** per-matchup posture (race vs. conserve) — only if
   Phase 3 measurably pays off, and per the guardrail above, written only for
   human-tournament archetypes.
5. **Pre-deadline refresh:** re-download replays, re-run
   `scripts/extract_replay_decks.py` (library tracks the current pool), consider
   re-weighting toward the human-tournament half if the meta netdecks.

## What we deliberately are NOT doing (and why)

- **Neural networks (behavioral cloning / PPO, PKM-008–010):** parked. The
  heuristic bot improves faster per hour invested right now; also blocked by a
  known label-alignment bug in the replay data that must be fixed first.
- **Full game-tree search (MCTS, plan 009):** one foundation piece exists
  (`determinize.py`), rest deferred until the cheaper levers are exhausted.
- **Hand-writing strategy for low-elo bot decks:** we compute knowledge from the
  identified decklist instead; hand-written matchup knowledge is reserved for
  human-tournament archetypes (the likely deadline meta) — see the guardrail in
  "What we have" point 3.

## Score card

| Date | Milestone | Measured result |
|---|---|---|
| 2026-07-08 | Deck switched to Dragapult, heuristic agent built | — |
| 2026-07-10 | First feedback-loop batch: 4 gaps found and fixed | 42% → 61% win rate (120 games) |
| 2026-07-11 | Human-tournament deck library + detector built | Detector nearly blind on real pool (89% no-read) |
| 2026-07-12 | Replay-extracted library merged (plan 011 Phase 1) | 92% archetype reads (turn ~2), 40% exact-list reads, 0 false exacts |
| 2026-07-12 | Detector wired into attack targeting (Phase 2) | Win-rate eval pending (WSL down) |
| 2026-07-12 | Matchup identification split into its own module; archetype-core reference built | No behavior change; found existing signature table already covers ~59% of bot games |
| 2026-07-12 | Archetype-core reference sanity-checked against full replay info, 8 missing archetypes added | Coverage 60% → 98% of bot game-instances |
