# 007 — Heuristics Logic Plan (pre-code) (v2)

**[v2]** Updated against `dragapult_deck_explanation.md` v3: the deck owner decided **not** to add Shaymin or Lillie's Clefairy ex (Section 9 items 7–8, now resolved). This plan no longer needs to account for either card. It also folds in three gaps a critical review flagged: Watchtower/Meowth ex self-lock sequencing (Tier 3), Fezandipiti ex bench-exposure discretion (Tier 3), and a concrete design sketch for Tier 5 archetype-signature detection (previously just asserted).

Grounded against the actual engine surface in `src/pokemon/cabt_enums.py`
(`SelectType`, `SelectContext`, `OptionType`, `AreaType`) and the
`make_heuristic_agent` architecture in `heuristics.py` (ordered list of
`Ctx -> indices|None` functions, first non-`None` match wins, else random).
Where the engine's exact field semantics aren't yet empirically verified
(`docs/000_plan_engine_enum_extraction.md` Phase 2), that's flagged inline —
these heuristics should degrade to "doesn't apply" rather than guess wrong,
same as the existing `_option_card_id` comment already commits to.

---

## A. Ordinary-gameplay defaults (fills Section 9 gaps, finding #2)

These are the three defaults `dragapult_deck_explanation.md` Section 9
explicitly says it doesn't cover. They need to exist before matchup-specific
heuristics, because they fire on nearly every game regardless of opponent.

### A1. Mulligan (`sel_context == SelectContext.MULLIGAN`, `sel_type == YES_NO`)

TCG rules make this non-discretionary: you mulligan only when your hand has
zero Basic Pokémon, and it's forced, not a choice. So the rule is
deterministic, not strategic:

- If the current hand (`ctx.hand`) contains zero Basic Pokémon → answer YES.
- Otherwise → answer NO.

This never needs archetype knowledge and never needs a fallback beyond
"count Basics in hand," so it's safe as an always-first, always-fires rule.
Flag: unverified whether `MULLIGAN`'s yes/no polarity in the live engine
matches this reading (Phase 2 gap) — write it to check hand-basic-count
either way and pick whichever answer matches "keep hand" when count > 0, so
a polarity mistake fails safe (still mulligans a dead hand) rather than
silently keeping an illegal hand.

### A2. Active replacement after a KO (forced switch onto `TO_ACTIVE`)

Priority order over the legal bench options, most-preferred first — stop at
the first tier with an eligible candidate:

1. **A Dragapult ex that can attack immediately** — i.e., has enough energy
   attached right now for Jet Headbutt (any 1 energy) or, better, Phantom
   Dive (1 Fire + 1 Psychic already attached). Promoting an attacker that
   doesn't cost a turn of setup preserves tempo, which matters more than
   anything else once forced into a reactive decision.
2. **A Drakloak that hasn't used Recon Directive this turn yet** — keeps the
   card-selection engine (Section 3) running instead of losing a turn of it.
3. **A Munkidori with Darkness Energy already attached** — can keep tanking
   in Active while still contributing Adrena-Brain, rather than promoting a
   card that does nothing this turn.
4. **Highest-remaining-HP non-Rule-Box piece** (Budew / Meowth ex /
   Fezandipiti ex, in that HP-remaining order) — Rule-Box Pokémon (ex) are
   worth 2 prizes if KO'd, so per Section 5's prize-mapping principle, don't
   voluntarily promote an ex into the Active spot as a "wall" if a
   non-Rule-Box option exists; only promote an ex here if it's the only
   thing left.
5. **Whatever's left** — no real choice remains, promote it.

Within any tier with multiple eligible candidates, break ties by highest
remaining HP (survives longest before the next forced decision).

### A3. Supporter tiebreak (`sel_type == MAIN`, multiple Supporters legal, no matchup note applies)

Ordered preference when more than one Supporter is a legal play and nothing
matchup-specific says otherwise:

1. **Boss's Orders** — only if it sets up a KO this turn (a benched opposing
   target is within lethal range of the attack you're about to make) or is
   needed to stop the opponent stabilizing (e.g., gusting a low-HP support
   piece before it can be retreated safely). Never the default "nothing else
   to do" pick — it's a 3-of, save it for a concrete payoff.
2. **Crispin** — if you're energy-short for the current plan: either you
   haven't yet banked the 4 cumulative attachments needed to chain two
   Phantom Dives (Section 4), or a live Munkidori needs Darkness Energy and
   has none. Crispin beats Lillie's Determination whenever energy is the
   bottleneck, per Section 4's "Crispin usually needed at least once per
   game."
3. **Lillie's Determination** — the actual default: play this whenever
   Boss's Orders has no payoff and Crispin isn't energy-urgent. This is
   deliberately the "no better option" fallback, matching its role as the
   format's best pure draw Supporter.
4. **Judge** — never wins the generic tiebreak. It's a dual-use situational
   card (Section 2) that requires either "my hand is unplayable" or "I can
   deduce what they're holding" — both are judgment calls a generic
   ordering shouldn't fake. Leave Judge to a dedicated situational heuristic
   (or the random fallback) rather than folding it into this default order.

---

## B. Munkidori / Darkness Energy attach-order rule (finding #6, tightened)

Only 2 Darkness Energy exist in the whole 60, and Crispin is the only tutor
that can fetch one — so "attach speculatively" is not viable. Concrete rule,
checked in this order:

1. **Never attach Darkness Energy to a Munkidori with no near-term
   Adrena-Brain plan.** A Munkidori sitting passively on the bench with
   nothing to shift damage onto is not a valid attach target — this
   heuristic returns "doesn't apply" (`None`) rather than attach, so the
   fallback either finds a better target or defers.
2. **Exactly one live Munkidori** → always route Darkness Energy to it
   first; no competing target exists.
3. **Two live Munkidori** → attach to whichever one has an immediate
   Adrena-Brain payoff available this turn — i.e., there's an opposing
   Pokémon already inside breakpoint range once damage counters shift onto
   it (from Phantom Dive's bench spread or prior damage). If neither has an
   immediate payoff, attach to the **Active** Munkidori over the benched
   one — the Active copy is the one taking damage that needs shifting off,
   so it's the one that benefits from having Darkness available sooner.
4. **Sequencing across the game**: once Munkidori #1 has used its Darkness
   Energy to secure a KO, or has been KO'd, only then does Munkidori #2
   become the primary Adrena-Brain user. This makes the existing doc note
   ("treat a second Munkidori as a reserve piece") into an actual rule
   instead of a sentence — the two Munkidori are never simultaneously
   competing for the second Darkness Energy under normal sequencing, because
   #2 doesn't need it until #1 is spent.
5. **Crispin's energy choice**: default Crispin's fetch to Fire/Psychic
   (Phantom Dive is the primary win condition; Munkidori is support). Only
   fetch Darkness via Crispin when *both* (a) a live Munkidori currently has
   no Darkness Energy, and (b) there's a bench-spread setup this turn or
   next turn that would otherwise go to waste without Adrena-Brain. This
   keeps Darkness-fetching need-driven rather than "top up whenever legal."

---

## D. Stadium-sequencing and bench-exposure rules (v2 addition)

Both of these are called out explicitly and repeatedly in `dragapult_deck_explanation.md` (Section 2, Section 4, Section 5, and the mirror-match/N's Zoroark ex/Grimmsnarl notes in Section 8) but were previously missing from this plan's tiers. They fold into Tier 3 below.

### D1. Team Rocket's Watchtower vs. our own Meowth ex

Watchtower silences Colorless-typed Pokémon's Abilities on **both** sides — our Meowth ex (Colorless) loses Last-Ditch Catch the moment Watchtower is in play, including if we're the ones who played it.

- **Before playing Watchtower from hand**: if a Meowth ex is in hand or already benched *and hasn't yet used Last-Ditch Catch this game*, play/bench Meowth ex (and let its on-play search resolve) first, in the same turn or an earlier one, before dropping Watchtower.
- If Meowth ex has already used Last-Ditch Catch (search already resolved) or isn't available this game, Watchtower has no self-lock cost — play it on its normal matchup timing (Section 4: turn 1 vs. Mega Kangaskhan ex, otherwise hold for hand-disruption pairing).
- If a legal `PLAY` option this turn would place Watchtower while an *un-searched* Meowth ex is still in hand, this rule returns `None` for the Watchtower play (defer it) rather than blocking the turn — a lower-tier default can still pick a different play.

### D2. Bench-exposure discretion for non-Tera Rule-Box Pokémon (Fezandipiti ex, Meowth ex)

Unlike Dragapult ex (Tera protects it while benched), Fezandipiti ex and Meowth ex have no benched-damage immunity — Section 5's "don't hand them an easy map" principle and the mirror-match/N's Zoroark ex notes call this out directly as a real mistake to avoid, not just a style preference.

- Don't bench Fezandipiti ex or Meowth ex as a `SETUP_BENCH_POKEMON` or mid-game `PLAY` choice when a lower-value, non-Rule-Box option (Dreepy, Budew, a spare Munkidori) is also legal and the board doesn't yet need Fezandipiti ex's draw engine or Meowth ex's search this turn.
- Once benched, treat Fezandipiti ex/Meowth ex as retreat/protect priorities if a forced-switch decision (A2) or a voluntary retreat option is legal and either is sitting at a damage total that puts it inside the opponent's live Boss's-Orders-plus-attack breakpoint (Section 10's dynamic calculator) — this is the same "don't leave an easy gust-and-KO target" logic the deck doc applies to Fezandipiti ex specifically in the mirror and Arboliva matchups.
- This is a discretionary ordering rule, not a hard block: if Fezandipiti ex's Flip the Script draw or Meowth ex's search is needed *this turn* to keep the hand functional, benching it anyway is correct — the rule only fires when an equally-good non-Rule-Box alternative exists.

---

## C. Archetype-agnostic core priority ladder (finding #3/#4 — build this before matchup overrides)

`make_heuristic_agent` is first-match-wins over an ordered list, so the
build order *is* the priority order. This tier list is the answer to "what
gets written before the ten Section 8 matchup writeups":

- **Tier 1 — setup phase.** `SETUP_ACTIVE_POKEMON` / `SETUP_BENCH_POKEMON`:
  encode Section 4's "Opening Pokémon priority" directly (Budew > Munkidori
  > Dreepy > Fezandipiti ex > Meowth ex going first; Budew > Dreepy >
  Munkidori > ... going second) plus Section 4's "Standard board setup
  order" (Dreepy, Dreepy, then Budew vs. slow decks / more Dreepy vs. fast
  decks).
- **Tier 2 — forced/reactive, no discretion.** A2 (Active replacement after
  KO) and A1 (mulligan) from Section A above. These fire whenever the
  engine forces the decision, independent of opponent archetype.
- **Tier 3 — resource management, fires almost every turn.** Energy
  attachment defaults (Section 4 "Attaching energy"), the Munkidori/Darkness
  rule (Section B above), discard-sequencing priority (Section 11 — already
  fully specified, translate directly), the Supporter tiebreak (A3), the
  Watchtower/Meowth ex sequencing rule (D1), and the Fezandipiti ex/Meowth ex
  bench-exposure discretion rule (D2).
- **Tier 4 — attack/targeting, archetype-agnostic.** Default Phantom Dive
  bench-spread target selection using Section 10's dynamic breakpoint
  calculator (live HP/attack values off the card DB, no archetype lookup
  required) to pick whichever currently-visible bench target is inside
  lethal range now or next turn; default Boss's Orders target (lowest
  remaining-HP benched Rule-Box Pokémon, or whatever the breakpoint calc
  flags as already lethal); default retreat/tank behavior (Munkidori
  absorbing hits per Section 4). **Ex-damage-blocker fallback (v2):** before
  targeting with an ex attack (Phantom Dive, Cruel Arrow), check the
  opposing Active/target for an in-play Ability or Stadium that zeroes
  Rule-Box-attack damage — currently only one such case is documented
  (Crustle's Mysterious Rock Inn, Section 8) — and if present, this tier's
  ex-attack targeting returns `None` so a non-ex attack (Drakloak's Dragon
  Headbutt, Jet Headbutt) is used instead. This check is archetype-agnostic
  by construction (card-name match against a short deny-list, not a
  matchup lookup), so it belongs in Tier 4, not Tier 5.
- **Tier 5 — matchup-specific overrides.** Section 8's ten archetype
  write-ups (Genesect/Unfair-Stamp timing, Arboliva's Meganium-priority
  target, mirror-match Drakloak-first targeting, etc.) — reached only when
  the opponent's revealed cards match a known signature. This tier is
  explicitly last: Tiers 1–4 need to already produce a coherent, complete
  game on their own (the thing a Kaggle bot pool actually exercises) before
  matchup overrides are worth writing.

  **Archetype-signature detection (v2 — was previously unspecified):**
  matching "the opponent's revealed cards" to a Section 8 write-up needs a
  concrete signal, not a vague lookup. Concretely: maintain a small
  static table mapping *one or two distinctive card names* per Section 8
  archetype to that archetype's override functions — e.g. `Smoliv`/`Dolliv`/
  `Arboliva ex` → Arboliva overrides, `Crustle` → the Mysterious Rock Inn
  fallback (already promoted to Tier 4 above since it's a targeting-legality
  check, not a strategic override), `N's Zoroark ex`/`Pecharunt ex` → N's
  Zoroark ex overrides, etc. The match key is **any opponent Pokémon or
  Stadium that has appeared face-up in `ctx` so far this game** (played to
  their Bench/Active, or revealed by a search/attack effect) — once a
  signature card is seen, latch the matchup identity for the rest of the
  game (don't re-check every turn; archetypes don't change mid-game) and
  route subsequent Tier 5 decisions through that archetype's override
  functions ahead of the Tier 1–4 defaults. If no signature card has been
  seen yet, Tier 5 contributes nothing (`None`) and Tier 1–4 defaults
  govern, which is already the correct behavior for an unidentified/early
  opponent board. This is a lookup table + a "have I seen card X" scan, not
  a new engine capability — it only needs whatever `ctx` field already
  surfaces the opponent's played Pokémon/Stadium, which Tier 1–4 already
  reads for breakpoint calculation.

This directly resolves finding #4: implementation should proceed tier by
tier, top to bottom, not matchup-first — a matchup override is a `None`-safe
addition layered *on top of* an already-functioning Tier 1–4 core, never a
substitute for it.

---

## Still not covered by this plan

- Section 9 items 7–8 (Shaymin / Lillie's Clefairy ex) are now **resolved**
  (deck owner decided against both, `dragapult_deck_explanation.md` v3) —
  this plan never needed heuristics for cards we don't run, so there's
  nothing to remove here, but note the corollary: the Arboliva, Grimmsnarl,
  Mega Starmie, and Raging Bolt Tier 5 overrides should implement the v3
  "avoid benching low-HP support Pokémon" / "race their energy engine down"
  fallback lines rather than any bench-protection logic, since that
  protection doesn't exist in this build.
- Section 9 items 9–10 (Slakoth flex-slot decklist question, Milotic
  ex/Tera interaction) are still open in the explanation doc — deck-
  composition and rules-interaction questions, not heuristic-logic
  questions, still out of scope here.
- The exact `Ctx`/engine field names for "energy attached to a specific
  Pokémon," "damage counters already on a Pokémon," and "Ability used this
  turn" aren't yet confirmed against the live engine (Phase 2 of
  `docs/000_plan_engine_enum_extraction.md`) — A2 tier 1–2, the Munkidori
  rule's "near-term plan" check, Tier 4's breakpoint calculator, and D2's
  breakpoint-based retreat check all need those fields to actually
  implement, not just to plan in prose. **This is a blocking precondition
  on Tiers 2–4 and D2, not a closing footnote** — verify these fields
  empirically before writing any code for those tiers, since a wrong field
  name won't error, it'll silently degrade targeting to a worse default
  (Tier 4 collapsing to "highest-HP non-Rule-Box" on every forced switch)
  with no visible signal in testing.
- Tier 5's archetype-signature table (see Tier 5 above) still needs the
  actual per-archetype override functions written for each Section 8
  matchup — this plan specifies the detection mechanism, not the ten
  matchups' worth of override logic itself.
