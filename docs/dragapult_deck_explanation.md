# Dragapult ex (Pult Noir) Deck Explanation (v3)

> Working document. Source: `guide videos/misc resources/dump` (author: @wet_goose) + card database (`pokemon/data/cards_pokemon.csv`, `cards_trainer.csv`) + ongoing Q&A with deck owner.
> Purpose: give an AI agent (Claude) enough grounded understanding of this deck to build heuristics for an automated player.


> **[v3] Resolved: Shaymin and Lillie's Clefairy ex are NOT going in the 60.** Several supplemental matchup files (`matchups_dump/arboliva.txt`, `grimmsnarl.txt`, `mega starmie.txt`, `ragingbolt.txt`, `lucario.txt`, `slopbox.txt`, `dragapult.txt`, plus the Alakazam section) called for one or both as tech pieces, and this was left open through v2 (Section 9, items 7–8). **Decision (deck owner): stick with the Section 1 decklist as-is — no Shaymin, no Lillie's Clefairy ex.** Every matchup section below that leaned on either card as its answer has been rewritten in v3 to rely only on cards actually in the 60 (see each section's rewritten counterplay). Where a matchup's coverage is genuinely weaker without the tech (notably bench-spread-heavy matchups: Arboliva, Mega Starmie, Raging Bolt, Grimmsnarl), that's now stated plainly as a real matchup weakness rather than patched over with a card we don't run.



---

## 1. Decklist (60 cards)

### Pokémon (18)
| Qty | Card | Set/No |
|---|---|---|
| 4 | Dreepy | TWM 128 |
| 4 | Drakloak | TWM 129 |
| 3 | Dragapult ex | TWM 130 |
| 2 | Munkidori | TWM 95 |
| 2 | Budew | ASC 16 |
| 1 | Moltres | PFL 14 |
| 1 | Fezandipiti ex | ASC 142 |
| 1 | Meowth ex | POR 62 |

### Trainers (33)
| Qty | Card | Set/No | Type |
|---|---|---|---|
| 4 | Lillie's Determination | MEG 119 | Supporter |
| 3 | Crispin | SCR 133 | Supporter |
| 3 | Boss's Orders | MEG 114 | Supporter |
| 1 | Judge | POR 76 | Supporter |
| 4 | Crushing Hammer | POR 71 | Item |
| 4 | Buddy-Buddy Poffin | TEF 144 | Item |
| 4 | Poké Pad | POR 81 | Item |
| 4 | Ultra Ball | MEG 131 | Item |
| 2 | Night Stretcher | ASC 196 | Item |
| 1 | Unfair Stamp | TWM 165 | Item (ACE SPEC) |
| 1 | Risky Ruins | MEG 127 | Stadium |
| 1 | Team Rocket's Watchtower | DRI 180 | Stadium |
| 1 | Xerosic's Machinations | SFA 64 | Supporter |

### Energy (9)
| Qty | Card |
|---|---|
| 4 | Fire Energy |
| 3 | Psychic Energy |
| 2 | Darkness Energy |

**Confirmed:** the decklist counts (1x Risky Ruins, 1x Team Rocket's Watchtower, 1x Xerosic's Machinations) are correct. The "2 Team Rocket's Watchtower" mention in the dump's prose is just an outdated/typo reference — treat it as 1/1/1.


---

## 2. Card-by-card purpose

### Pokémon

**Dreepy (TWM 128)** — 70 HP Basic, Stage 0 of the main attacker line.
- Petty Grudge: {P}, 10 dmg
- Bite: {R}{P}, 40 dmg
- Run 4 copies (max). Needed because you want to reliably find/evolve into 3 Drakloak per game — see "why 4 Dreepy / triple Drakloak" below.

**Drakloak (TWM 129)** — 90 HP Stage 1.
- Ability *Recon Directive* (once/turn): look at top 2 cards of deck, take 1, put other on bottom. This is the deck's primary card-selection/draw engine.
- Dragon Headbutt: {R}{P}, 70 dmg.
- Run 4 copies. Triple Drakloak (i.e., 3 live copies used per game) is important for card draw/selection since the deck lost Counter Catcher and Iono (older support cards) — the deck leans harder on Recon Directive + Crispin to dig for what it needs.

**Dragapult ex (TWM 130)** — 320 HP Stage 2, the deck's namesake win condition.
- Ability *[Tera]*: while on the Bench, prevents all damage to it (both players' attacks). This makes backup Dragapult ex essentially unkillable while benched, letting you always have a second/third one ready without fear of it being sniped.
- Jet Headbutt: {C} (1 energy any type), 70 dmg — a "cheap" filler attack.
- **Phantom Dive**: {R}{P}, 200 dmg, AND put 6 damage counters on the opponent's Benched Pokémon in any way you like. This is the deck's core win condition — a single Phantom Dive does 200 to the active AND spreads 60 damage (6 counters) across the bench however you choose, which combined with Munkidori's damage-shifting or a second Phantom Dive next turn, sets up knockouts on multiple benched targets.
- Run 3 copies (only 2 are attacked with in a normal game, but the 3rd exists as insurance / to deny easy knockouts on a lone Drakloak, and because the Tera bench-damage-immunity means having a spare is very low risk).

**Munkidori (TWM 95)** — Basic Pokémon.
- Ability *Adrena-Brain* (once/turn, requires a {D}/Darkness Energy attached to this Munkidori): move up to 3 damage counters from one of your own Pokémon to one of the opponent's Pokémon.
- Mind Bend: {P}{C}, 60 dmg, opponent's Active becomes Confused.
- Purpose per dump: "to heal and shift damage to set up a pokemon for death from phantom dive" — i.e., Munkidori takes damage counters off your own damaged Pokémon (effectively healing them / saving them from a KO) and moves that damage onto an opposing Pokémon that Phantom Dive's bench-spread already softened up, finishing it off without needing a second attack.
- **[v2, review #6]** The deck only runs 2 Darkness Energy total (Section 1), and Crispin — the only tutor that can fetch Darkness — is a 1-per-turn Supporter play. Running "2 Munkidori" as a matchup's ideal board state (see Section 8) implies both want their own Darkness Energy at once; that's achievable but tight on this energy count, not something to assume happens every game. Treat a second Munkidori as a reserve piece that takes over once the first has traded or used its Darkness, not a guarantee both fire Adrena-Brain simultaneously.

**Budew (ASC 16)** — 30 HP Basic.
- Itchy Pollen: no cost, 10 dmg, opponent can't play Item cards during their next turn.
- Purpose: early-game wall + item-lock disruption. Since the deck now opts to go first more often, the item-lock is less impactful than before (opponent doesn't get a turn of items before you lock them), so it's valued lower than in older lists (only 1 copy now vs. 2 previously). Mainly played when Budew is safe from being knocked out, especially valuable when the opponent is down to 5 prizes (see prize-race section).

**Moltres (PFL 14)** — 120 HP Basic, {R}/Fire type tech attacker.
- Fighting Wings: {R} (1 Fire energy), 20 dmg, +90 more damage if opponent's Active is a Pokémon ex (110 total vs. an ex, before weakness).
- **Confirmed purpose:** specifically a tech card to snipe Grass-type ex attackers that are weak to Fire — the named example is Teal Mask Ogerpon ex, which is a common/relevant meta threat. Since Ogerpon ex is Grass (weak to Fire), Moltres' 110 damage vs. an ex gets doubled by Weakness, likely enabling a 1-hit KO for a single Fire Energy attachment — a very cheap, efficient answer to that specific threat. Only 1 copy since it's a narrow answer card, not a general attacker.


**Fezandipiti ex (ASC 142)** — 210 HP Basic ex.
- Ability *Flip the Script* (once/turn): if any of your Pokémon were knocked out during opponent's last turn, draw 3 cards.
- Cruel Arrow: 3 colorless energy, 100 dmg to any one opponent Pokémon (bench damage allowed, no weakness/resistance on bench).
- Purpose: extra draw engine during the mid-game, specifically rewards you for trading/losing a Pokémon (since this deck expects to take some KOs on Dreepy/Drakloak along the way). Considered one of the best Pokémon in the format.

**Meowth ex (POR 62)** — 170 HP Basic ex.
- Ability *Last-Ditch Catch*: when played from hand onto the Bench, search deck for a Supporter card into hand (once per turn across "Last-Ditch" abilities).
- Tuck Tail: 3 colorless energy, 60 dmg, returns itself + attached cards to hand.
- Purpose: turns Ultra Ball (a Pokémon-search Item) effectively into extra Supporter-search consistency, boosting opening hand consistency. Only 1 copy is run mainly due to bench space constraints (this list uses 2 Budew instead of a 2nd Meowth ex, unlike some straight Dragapult lists).
- **[v2, review #4]** Meowth ex (POR 62) is itself Colorless-typed — which means our own **Team Rocket's Watchtower** (see below) silences its own Last-Ditch Catch Ability while in play. Sequence Meowth ex's on-play search *before* dropping Watchtower if you plan to run both this game, or accept losing the Ability for the rest of the game once Watchtower is down.

### Trainers

**Lillie's Determination (MEG 119)** — Shuffle hand into deck, draw 6 (draw 8 instead if you have exactly 6 prizes remaining — i.e., it's your first turn/still full prizes). Best draw Supporter in the format; 4 copies maximizes odds of opening with it since your opening setup quality determines a large % of games.

**Crispin (SCR 133)** — Search deck for up to 2 basic Energy of different types; reveal them, put 1 into hand, attach the other to one of your Pokémon. Needed because chaining two Phantom Dives (without other acceleration) requires 4 total energy attachments; Crispin is the deck's energy acceleration/consistency piece. Run 3 copies (bumped from 2) because the mirror match especially requires playing 2 Crispins in a game often, and using Meowth ex's search for it isn't efficient enough.

**Boss's Orders (MEG 114)** — Switch 1 of opponent's Benched Pokémon into the Active spot. The single best Supporter in the format; used to close out games by dragging up a weak/damaged bench target for the kill, or to force bad trades early. Only need ~2 per game typically, so 3 copies is enough while leaving room for other draw support.

**Judge (POR 76)** — Each player shuffles hand into deck and draws 4.
- **Confirmed purpose (dual-use card):**
  1. **Offensive/disruption use** (similar in spirit to Xerosic's Machinations): play it when you know or strongly suspect the opponent is holding a specific important card they need next turn — e.g., their only Boss's Orders, or a needed Energy card. Shuffling it away denies them that specific answer for at least a turn. You determine "what they're holding" via deduction: what cards are missing from their discard pile / what's already in play, general archetype knowledge (what staples that deck typically runs, e.g. "this deck always runs 2-3 Boss's Orders"), and any information revealed by their own searches (e.g. if they searched and visibly kept a card, or revealed one during a search effect).
  2. **Defensive/reset use**: played on yourself in a pinch when your own hand is bad/unplayable, to reshuffle and draw a fresh 4 — a bail-out button similar in spirit to Unfair Stamp's draw, but usable anytime (no KO requirement) at the cost of also refreshing the opponent's hand.
- Only 1 copy since it's a situational tech/disruption piece, not a primary draw engine (Lillie's Determination fills that role).


**Crushing Hammer (POR 71)** — Coin flip; if heads, discard an Energy from 1 of opponent's Pokémon. Best disruption Item in the format — the goal isn't necessarily to strip all energy, but to buy time to set up your own board while denying/delaying the opponent's attacks. Can also deny knockouts on Budew early and can enable comebacks off lucky flips.

**Buddy-Buddy Poffin (TEF 144)** — Search deck for up to 2 Basic Pokémon with 70 HP or less, put onto Bench. Core consistency piece for finding Dreepy/Budew (all ≤70 HP) since the deck opts to go first and needs to maximize Pokémon search.

**Poké Pad (POR 81)** — Search deck for a Pokémon without a Rule Box (i.e., not an ex/V/etc.), put into hand. Flexibly fetches non rule box pokemon. Same consistency logic as Buddy-Buddy Poffin — 4 copies, non-negotiable per the author.

**Ultra Ball (MEG 131)** — Discard 2 other cards from hand, search deck for any Pokémon into hand. Core Pokémon search; combos with Meowth ex to also net a Supporter when played. 4 copies, non-negotiable.

**Night Stretcher (ASC 196)** — Put a Pokémon OR a Basic Energy card from discard pile into hand. Recursion piece; 2 copies is the "standard" count (would like 3 but no room in this 60). Because only 2 copies are run, Ultra Ball discards early in the game must be made carefully (can't over-rely on discarding Pokémon expecting to Night Stretcher it back, since recursion is scarce).

**Unfair Stamp (TWM 165, ACE SPEC)** — Usable only if one of your Pokémon was KO'd during opponent's last turn. Each player shuffles hand into deck; you draw 5, opponent draws 2. Chosen ACE SPEC because it provides strong hand disruption (opponent effectively "mulligans" down to 2 relevant cards) that Supporters can no longer replicate as effectively, while also functioning as a big draw effect for you. See Section 4 for usage timing.

**Risky Ruins (MEG 127, Stadium)** — Whenever any player puts a Basic non-Darkness Pokémon onto their Bench during their turn, place 2 damage counters on it. Used as a 1-of flex/meta tech: pre-damages incoming benched Pokémon for both players, useful for setting up breakpoints (and can help trigger Munkidori's Adrena-Brain / act as pre-damage that helps a later Phantom Dive/Cruel Arrow finish something off). Situational — good vs. decks without their own spread damage, more nuanced vs. decks with spread damage depending on who attacks first. **[v2, review #7]** Note: 2 damage counters is only 20 damage — enough to help set up a breakpoint alongside a real attack, not enough on its own to meaningfully threaten anything above ~20 HP. See the mirror-match note in Section 8 for a case where this was previously overstated.

**Team Rocket's Watchtower (DRI 180, Stadium)** — Colorless-type Pokémon (both players') have no Abilities while this Stadium is in play. 1-of flex/meta tech aimed specifically at shutting off abilities on decks like Meowth ex, Mega Kangaskhan ex, and Dudunsparce (all rely on {C}-type Pokémon abilities). Also incidentally can shut off some Meowth ex lines. **[v2, review #4]** This cuts both ways: our own Meowth ex is Colorless-typed too, so playing Watchtower also silences our own Last-Ditch Catch Ability for as long as it's in play. Sequence Meowth ex's search before dropping Watchtower, or accept the trade-off consciously.

**Xerosic's Machinations (SFA 64)** — Opponent discards down to 3 cards in hand. 1-of flex/meta tech hand-disruption, specifically valuable vs. decks like Alakazam that build up a very large hand.

### Energy

**Fire Energy (4 copies)** — Needed for Dragapult ex's Phantom Dive ({R}{P} cost) and Moltres. You usually only need access to 2 at a time; 4 copies also helps Crispin's search odds (more copies = more likely Crispin finds one).

**Psychic Energy (3 copies)** — Same logic; usually need 2 at a time. 4 copies could be justified for extra uses with "Mind Bend" (Munkidori) though this is described as a fringe scenario.

**Darkness Energy (2 copies)** — Rarely need more than 1 at a time, but 2 copies ensures more consistent access to Munkidori + Darkness Energy simultaneously (needed for Adrena-Brain), and pairs with Crispin (which needs 2 *different* energy types to search, and Darkness is the only way to fetch it since Crispin is the only tutor for it). **[v2, review #6]** This is also the deck's hard cap: only 2 Darkness Energy exist in the 60, so "2 Munkidori both running Adrena-Brain" (called for as an ideal state in several Section 8 matchups) is bounded by this count, not just by having 2 Munkidori in play — see the Munkidori entry above.

---

## 3. Why 4 Dreepy / triple Drakloak matters

**[v2, review #5]** The decklist runs the full 4 copies of Dreepy, not 3 — the v1 heading said "3 Dreepy," which didn't match Section 1's decklist and was never independently explained (the body only justified the Drakloak count). The 4th Dreepy exists as a consistency/mulligan buffer: only 3 live Drakloak per game are typically needed to drive the card-selection engine (below), so the extra Dreepy copy absorbs early-game prize/mulligan variance and gives Ultra Ball a safe discard target without threatening the "triple Drakloak" target itself.

Triple Drakloak (3 live copies in play across a game) is important primarily for the card draw/selection from *Recon Directive*. With Counter Catcher (a gust-from-behind card) and Iono (a hand-disruption/draw supporter) no longer available in this format, the deck can't easily gust from behind without spending its Supporter for turn — so it leans on Recon Directive off multiple Drakloak to dig for outs instead. This also explains reliance on Crispin (uses Supporter for turn) and inclusion of Unfair Stamp as substitute disruption.

---

## 4. General strategy / gameplan (from dump)

### Go first or second?
**Important context (confirmed by user):** the source guide (`dump`) was written for a *variant* of this deck that includes a Duskull/Dusclops/Dusknoir tech line. **Our actual decklist (Section 1) does not run Duskull/Dusclops/Dusknoir at all** — it's the "straight" Dragapult ex build. Most general strategic advice in the guide still applies, but any specific reference to Duskull/Dusclops/Dusknoir as *our own* tech should be disregarded/adjusted for this list.

With that context: go first against every archetype **except** when facing an opposing Dragapult ex/Dusknoir deck (i.e., an opponent running that Dusknoir tech), since Dusknoir decks play better from ahead. This is a matchup note about the *opponent's* possible deck, not about our own build. Since our list doesn't run Dusclops itself, treat this as: vs. an opponent's Dragapult ex/Dusknoir list specifically, lean toward going second.


### Opening Pokémon priority (blind opening)
- Going first: Budew > Munkidori > Dreepy > Fezandipiti ex > Meowth ex
- Going second: Budew > Dreepy > Munkidori > Fezandipiti ex > Meowth ex

### Standard board setup order
The dump's exact phrasing ("Dreepy, Dreepy, Duskull vs slower decks, or Dreepy vs faster decks") comes from the Duskull-variant guide and doesn't directly apply to our list (no Duskull line here). **For our deck, adapt this as:** Dreepy, Dreepy, then Budew (vs slower decks that won't punish a low-HP bench addition) OR just keep adding Dreepy (vs faster decks that are attacking consistently by turn 2, where Budew's 30 HP is too fragile/its tempo play is too slow to matter). Budew is usually slotted in after the 2nd Dreepy, or before the 2nd Dreepy if the opponent's hand looks weak and unlikely to KO Budew that turn.


### Itchy Pollen (Budew) usage
- Less valuable now than historically because comebacks are harder to engineer in general.
- Use it when it's the difference between the opponent setting up at all vs any deck.
- Against aggressive decks: use it to enable a Phantom Dive chain before the opponent sets up.
- Against slower/spread decks: only worth it if Budew's damage output is meaningfully impactful (i.e., the opponent has to attack second, or it causes them to miss a key KO breakpoint).
- Going first with a good setup (2 Drakloak found): generally do NOT use Itchy Pollen unless it stops a KO entirely or a KO on a Drakloak — don't waste the attachment/tempo when already winning.
- Going second: only use Budew if it can survive the turn, does substantial damage to their setup, or specifically vs. Dragapult ex decks.

### Attaching energy / preparing attackers
- Default: attach to a benched Dreepy/Drakloak/Dragapult ex if you expect the opponent to KO your current Active.
- If your Active is already a Dreepy/Drakloak/Dragapult ex and you expect to attack first, attach to the Active instead.
- Splitting attachments across two Drakloak is correct when a Drakloak is at serious risk of being KO'd.
- Crispin is usually needed at least once per game to have enough attachments to finish the game (each game, 2 Dragapult ex are attacked with, needing 4 total attachments to chain two Phantom Dives without prior acceleration).
- **Common mistake to avoid:** not preparing for back-to-back Phantom Dives — e.g., when the opponent is at 5 prizes, you should Crispin and attach across two *different* Drakloak/would-be-Dragapult so that if the first Dragapult ex is KO'd, the next one can also attack immediately, rather than Crispin + attack with one Dragapult ex and then being unable to find a second Crispin.

### Preparing an attack (tempo before Phantom Dive)
While setting up energy for Phantom Dive, use Itchy Pollen to disrupt the opponent's setup, or use Munkidori to tank hits in the Active spot (buying time).
- Prize-count timing terminology: "6-5" means you are at 6 prizes remaining (haven't lost any) and opponent is at 5 (has lost 1). Ideal to start attacking with Phantom Dive around 6-5 or 6-4; if the opponent is already down to 3 prizes before your first attack, the deck is unlikely to win many matchups from there (i.e., you don't want to fall too far behind before your engine starts firing).
- **[v2, review #1 — revised]** A turn-2 Phantom Dive is a genuinely strong outcome when it happens, but it's a best-case draw, not the default plan: with no Rare Candy in this list, it requires Dreepy as your *starting* Active, on-schedule draws through Drakloak into Dragapult ex, *and* both a Fire and a Psychic Energy attached across turns 1–2 (which usually means timing Crispin just right on turn 1 instead of playing Lillie's Determination). That's a fairly narrow parlay of conditions lining up together — take it if it's actually available, but don't plan matchups around it as a baseline. **Turn 3 is the more realistic floor** for the first Phantom Dive in most games; treat any matchup note below that cites "turn 2 Phantom Dive" as an upside case rather than the expected line.

### Unfair Stamp usage
- Use it whenever your hand/board is unplayable and you need the card draw (its draw is a strong safety net).
- If the opponent has a weak board, consider pairing Unfair Stamp with a "Boss check" (forcing them to find Boss's Orders for a KO) or with Itchy Pollen.
- Main intended use: disrupt the opponent's hand while you're already attacking, forcing them to either find Boss's Orders (Boss check) or assemble a big combo (or both) under a thinned hand.

### Playing around opponent's Unfair Stamp
- Best defense is having strong card draw available on board, or having your board maximally set up (2 Dragapult ex ready).
- Rarely correct to intentionally not attack just to avoid triggering their Unfair Stamp — the main exception is delaying a KO on your own Budew specifically when you have Boss's Orders available (to control the trade instead).

### Opening a "bad" starter (2-prize Pokémon in Active)
Not ideal, but treat it as a wall while you build up the bench. If the opponent needs 2 turns to KO it going second (or 3 going first) it works out equivalent to them getting a 1-prize KO each of those turns — i.e., it's not as big a tempo loss as it first seems.

### Risky Ruins usage
- Playing it early just to pre-damage both players' incoming Basics is strong vs. decks without their own spread damage (fewer relevant breakpoints against you, more relevant breakpoints for you, plus Adrena-Brain [Munkidori ability] activation support).
- Vs. decks with spread damage: avoid playing it early if you expect to attack *after* your opponent (i.e., you're behind on tempo) — but fine to slam it down early if you expect to attack first.

### Team Rocket's Watchtower usage
- Play immediately turn 1 vs. Mega Kangaskhan ex decks.
- Otherwise, hold and pair it with hand disruption.
- Vs. Dudunsparce decks: use as disruption timing tool.
- Vs. other decks: mostly just a Stadium-bump effect, occasionally shutting off Meowth ex.
- **[v2, review #4]** Also shuts off our own Meowth ex (Colorless-typed) while it's in play — play Meowth ex's bench-search first if you intend to drop Watchtower the same game.

---

## 5. Prize-race / Prize-mapping concepts (general TCG theory, applies to this deck)

- The real win condition of the TCG is taking all 6 of your prize cards before the opponent does — KOs are just the mechanism.
- Prize values: regular Pokémon = 1 prize, Pokémon ex = 2 prizes, Mega Pokémon (ex) = 3 prizes. **Correction (confirmed by user): VMAX/V Pokémon no longer exist in the current format** — the modern 3-prize category is **Mega Pokémon ex** (e.g., Mega Charizard X ex, seen in the card database), not VMAX.

- **Favorable trade** = your KO nets you more prizes than the KO the opponent gets back on you (e.g., a 1-prize attacker KOs their 2-prize ex, then they KO your 1-prize attacker back — net you're ahead 2-to-1).
- **Prize mapping** = planning, from turn 1, exactly which of the opponent's Pokémon you intend to KO to reach 6 prizes (e.g., a "2-2-2 map" = three 2-prize Pokémon to KO; a "3-3 map" = two 3-prizers; a "1-1-2-2 map" = mixed).
- **Don't hand them an easy map**: avoid benching your own multi-prize (ex) Pokémon unless you must/plan to use it that turn — every benched rule-box Pokémon is a target for the opponent's Boss's Orders.
- **Forcing the "7th prize"**: if you can tell the opponent's deck is built around a small number of big KOs (e.g., 2-2-2), you can sometimes force them into taking KOs on your single-prize support Pokémon instead, making them net take more than 6 actual knockouts worth of "turns," slowing them down and burning their resources (e.g., limited Boss's Orders count).
- **Prize checking**: the first time you search your deck (Ultra Ball, Poké Pad, etc.), you may look at your discard/decklist state — use that opportunity to figure out which of your key cards (e.g., your only Boss's Orders) are stuck in your face-down prizes, and adjust your plan for which Pokémon you need to KO (and when) to dig into the prizes that likely contain it.

### How this deck's win condition maps onto prize theory
- Dragapult ex is a 2-prize attacker (Rule Box "ex"). Phantom Dive's 200 damage + 6-damage-counter bench spread is efficient because a single attack often threatens lethal on the Active *and* pre-loads a KO on a benched Pokémon for the following turn — effectively working toward 2 different prizes off 1-2 attacks.
- Because you're a 2-prize-attacker deck yourself, you want to avoid over-extending your own board with things the opponent can Boss's Orders for value — Dragapult ex on the Bench is safe (Tera ability blocks damage while benched), but this doesn't protect against non-damage effects; the main risk pieces to not over-expose are Fezandipiti ex / Meowth ex (also Rule Box, but no self-protection).

---

## 6. Confirmed win condition (summary)

> **Confirmed by user as accurate.**

The deck wins by:
1. Setting up 2–3 Dragapult ex with enough energy attachments to chain **Phantom Dive** turn after turn.
2. Using Phantom Dive's bench-damage-spread (6 damage counters placed anywhere on opponent's Bench) plus **Munkidori's Adrena-Brain** ability to convert "almost-KOs" into actual knockouts on multiple opposing Pokémon without needing extra attacks.
3. Using **Boss's Orders** plus prize-mapping to pick off the right targets so you take exactly 6 prizes before the opponent does.

Supporting this engine:
- **Fezandipiti ex / Meowth ex / Drakloak's Recon Directive** keep the hand stocked with outs (draw/search consistency).
- **Disruption** (Crushing Hammer, Budew's Itchy Pollen, Judge, Xerosic's Machinations, Unfair Stamp) buys time and slows the opponent down while the Phantom Dive engine gets going.

---

## 8. Matchup notes (from `matchup_dump`, adapted for our build)

> **Important context:** `matchup_dump` is from the same Duskull/Dusclops/Dusknoir-variant guide as `dump`. **Our decklist does not run Duskull/Dusclops/Dusknoir, nor Latias ex.** Anywhere the source mentions Dusclops/Dusknoir combos (e.g. Cursed Blast, Shadow Bind) or Latias ex's Eon Blade, that specific combo is **not available to us** — I've adapted the notes to focus on what still applies (Phantom Dive, Munkidori's Adrena-Brain, Boss's Orders, Jet Headbutt, Budew, Crushing Hammer, Unfair Stamp) and flagged where a line simply doesn't translate. **Per user: Psyduck (which counters Dusclops/Dusknoir's self-KO Cursed Blast ability via its "Damp" ability) is no longer a relevant concern for us since we don't run that tech.**

> **[v2, review #2] Terminology note on "ideal board state" below:** several supplemental matchup notes list an "ideal board state" (e.g. Alakazam's "4 Drakloak + 2 Munkidori") that, read as a literal simultaneous Bench snapshot, exceeds the 5-slot Bench limit once you add the required Active attacker (4 Drakloak + 2 Munkidori + 1 attacker = 7; similarly for Grimmsnarl and Raging Bolt's notes below). Section 4's "Standard board setup order" uses "board state" to mean *what's in play at once*, but these Section 8 lines clearly mean something else — **cumulative copies you expect to cycle through across the whole game**, not a target for the Bench at any single instant. Read every "ideal board state: N Drakloak + M Munkidori + ..." line below with that in mind; none of them are proposing an illegal simultaneous Bench.

### vs. Alakazam (Abra/Kadabra/Alakazam + Dudunsparce engine)
**Correction: the relevant Abra/Kadabra/Alakazam line for this matchup is the MEG printing, not the TWM printing.**

**Their full gameplan (per author's own write-up of this deck, provided by deck owner):** this is a simple, aggressive "glass cannon" deck. It draws a huge hand via the Alakazam line's *Psychic Draw* ability plus Dudunsparce/Enriching Energy, then one-shots whatever is in the opponent's Active spot with **Powerful Hand**. They race every matchup rather than playing a long/nuanced game, using Rare Candy + Boss's Orders mainly to speed up their own setup and buy time, not for grindy value.

**Key opposing cards:**
- **Abra (MEG 54)**, 50 HP — Teleportation Attack: {P}, 10 dmg, switch this Pokémon with 1 of their Benched Pokémon.
- **Kadabra (MEG 55)**, 80 HP — Ability *Psychic Draw*: once per turn, when played from hand to evolve one of their Pokémon, draw 2 cards. Super Psy Bolt: {P}, 30 dmg.
- **Alakazam (MEG 56)**, 140 HP — Ability *Psychic Draw*: same as Kadabra's but draws 3 cards on evolve. **Powerful Hand: {P} (single Psychic energy), places 2 damage counters (20 dmg) on our Active Pokémon for EACH card in their hand** — this is their primary win condition, not a fixed-damage attack. Critically, **Powerful Hand's damage is dealt as an "effect" of the attack, not direct attack damage** — see counter-tech note below.
- **Dudunsparce (TEF 129)**, 140 HP — Ability *Run Away Draw*: once per turn, may draw 3 cards; if any cards were drawn this way, shuffle this Pokémon and all attached cards back into their deck. Land Crush: ●●●, 90 dmg. This is their secondary "cycle for cards" engine alongside Psychic Draw — they can repeatedly shuffle Dudunsparce back in and re-find it to keep drawing.
- **Enriching Energy (SSP 191, ACE SPEC, Special Energy)** — provides {C}; when attached from hand to a Pokémon, draw 4 cards. Used to further inflate hand size for Powerful Hand and combos with Dudunsparce/Hilda for extra card advantage ("essentially drawing 7 cards for one Supporter" per the author, via Hilda searching Dudunsparce + an Energy, then re-triggering Run Away Draw).
- **Telepath Psychic Energy (POR 87, Special Energy, 4 copies expected)** — provides {P}; when attached from hand to a {P} Pokémon, search deck for up to 2 Basic {P} Pokémon onto the Bench. This is their Abra-line consistency piece (finds more Abra copies), not a draw card itself — noted by the user as originally missing from our card list above due to a formatting error.
- **Battle Cage (PFL 85, Stadium, 4 copies expected)** — **Prevents ALL damage counters from being placed on Benched Pokémon (both players') by effects of attacks and Abilities.** This is a hard counter to our deck's core engine: it blocks Phantom Dive's 6-damage-counter bench spread AND Munkidori's Adrena-Brain (an Ability that places damage counters) from doing anything to their Bench. **If Battle Cage is in play, treat our bench-spread/Adrena-Brain combo as completely dead for that turn** — fall back on direct Active-target damage only (Phantom Dive's 200 face damage, Jet Headbutt, Dragon Headbutt, Cruel Arrow) until we can remove the Stadium (we have no Stadium removal in this list, so plan around it rather than against it).
- **Dawn (PFL 87, Supporter)** and **Hilda (WHT 84, Supporter)** — their draw/search Supporters (search a Basic+Stage1+Stage2 for Dawn; search an Evolution Pokémon + Energy for Hilda). They run no traditional draw Supporters (no Lillie's Determination equivalent) since Psychic Draw/Dudunsparce provide their draw instead.
- **Genesect (SFA 40)** — Ability *ACE Nullifier*: **if it has a Pokémon Tool attached, we can't play Unfair Stamp (our ACE SPEC) at all.** Included specifically to blank Unfair Stamp, which the author calls "one of the scariest cards" for this deck to face.
- **Mist Energy (TEF 161) / Rock Fighting Energy (POR 88)** — both Special Energy that **prevent all effects of attacks** (not damage) done to the Pokémon they're attached to. The author notes these are common answers played by *other* decks (e.g. some Crustle lists run up to 4 Mist Energy) specifically because **Powerful Hand's damage is an effect, not direct damage, so these fully wall it.**
- **Enhanced Hammer (TWM 148)** — Discard a Special Energy from 1 of our Pokémon; this Alakazam deck's answer to us running Mist/Rock Fighting Energy ourselves, and to strip their own bad matchups' defensive Special Energy.
- Not directly relevant to us but worth knowing this deck carries answers for: Team Rocket's Articuno (blocks Powerful Hand via its own effect-immunity Ability), Fan Rotom/Togekiss/Lillie's Clefairy ex (Team-Rocket-matchup-specific techs), Handheld Fan/Yveltal (used to protect their own trapped Genesect from bad trades). **Note: Lillie's Clefairy ex (JTG 56) is specifically called out by the author as strong against Dragapult ex decks** — it's a 190 HP ex that can attack immediately without needing the Abra line set up (Full Moon Rondo: {P}●, 20 dmg + 20 more per Benched Pokémon on both sides), so if it shows up, treat it as a surprise early attacker capable of hitting Dreepy/Drakloak hard well before their main engine is online.

**Counterplay takeaways for our deck:**
- **This is a race.** Both decks are aggressive/fast with limited defensive tools — prioritize getting Phantom Dive online turn 2-3 rather than playing a slow/grindy game, since letting their hand grow uncontested is how they win.
- **Hand disruption caps their ceiling twice over**: Judge/Xerosic's Machinations don't just deny them specific cards here — since Powerful Hand's damage scales directly with hand size, thinning their hand also directly lowers the maximum damage Powerful Hand can do to us. This is unusually high-value tech in this specific matchup.
- **Watch for Battle Cage neutering our bench-spread plan** — if it's in play, don't rely on Phantom Dive's bench spread + Adrena-Brain for KOs; go for direct Active knockouts instead (200 dmg Phantom Dive alone is still enough to threaten most of their board).
- **Genesect + Tool shutting off Unfair Stamp** is a real risk here (explicitly the reason they include it) — try to use Unfair Stamp before they get a Tool onto Genesect, or plan the game as if Unfair Stamp may become unavailable.
- **Powerful Hand can one-shot a full-HP Dragapult ex (320 HP)** once their hand is large enough (16+ cards) — track their approximate hand size (via their Dudunsparce/Psychic Draw triggers) before committing your last ready Dragapult ex to the Active spot; consider holding it on the Bench (safe via Tera) until you can follow up with a KO of your own the same turn or the next.
- Since this deck has no real defensive tech of its own (glass cannon per the author), a fast, disruptive start from us (Crushing Hammer to deny their energy/Enriching-Energy tempo, early Phantom Dive) can often just outrace them before Powerful Hand reaches lethal numbers.

**Supplemental notes (source: `matchups_dump/alakazam.txt`, an image-derived quick-reference card from the deck owner; general concepts adapted below, since this note references a slightly different build with 4 live Drakloak/2 Munkidori targets):**
- Ideal board state for this matchup specifically: 4 Drakloak (all 4 copies live/used across the game, more than the usual "triple Drakloak" baseline) + 2 Munkidori (after Budew) — i.e., lean harder into the Drakloak/Munkidori engine than usual since this is a grindier matchup than the raw race framing above might suggest. **[v2] Cumulative/across-the-game counts, not a literal 6-Pokémon simultaneous Bench — see the terminology note at the top of this section. Also see review #6 on the 2-Munkidori/2-Darkness-Energy constraint above.** **[v3]** No Shaymin/Clefairy dependency in this matchup's ideal-board note — it was already framed around our actual cards.
- Prize-check priority cards specific to this matchup: Unfair Stamp, our Stadiums (Risky Ruins/Team Rocket's Watchtower), Munkidori, and Energy — check early via your first search effect whether these are stuck in prizes.
- **Phantom Dive + Risky Ruins + Munkidori's Adrena-Brain together is a strong combined play** for dealing with multiple of their Pokémon at once in a single turn.
- **Target Dudunsparce specifically once multiple Kadabra/Alakazam are already in play** — since this deck's recovery tools are limited, knocking out multiple Dudunsparce can meaningfully slow their draw engine down for several turns (this refines/confirms the general "hand disruption caps their ceiling" takeaway above with a concrete target priority).
- **Dealing with Genesect is important specifically because you need Unfair Stamp available late-game to win this matchup** — reinforces the earlier point about Genesect+Tool shutting off Unfair Stamp; treat removing Genesect (or using Stamp before it gets a Tool) as a near-must, not just a nice-to-have.
- **An early/aggressive Unfair Stamp is good if they haven't established a good board yet** — but only commit to this "snowball" line if you can actually capitalize on the resulting disruption; don't stamp early just to stamp if you can't follow up.
- They have good answers to item lock (i.e., don't rely on Budew's Itchy Pollen alone to slow them down) — attack as fast as possible instead of stalling.
- If they set up well and establish Genesect, the matchup gets sketchy — in that case, targeting Genesect directly is a good plan **only if you can simultaneously take a benched KO the same turn**, since you want to maintain a clean 2-2-2 prize map via Phantom Dive rather than spending a whole turn on a 1-prize Genesect alone.
- **If they bench Fezandipiti ex, Boss's Orders + swinging 200 (Phantom Dive) into it is a strong play** — they sometimes struggle to get Fezandipiti ex back out of the Active spot due to low energy counts, so a gusted Fezandipiti ex can end up stranded and eating a follow-up KO.
- Munkidori can pick up surprise KOs via Adrena-Brain + Mind Bend damage even outside the main Phantom Dive line — if they ever miss a KO on your side, having 2 live Munkidori is especially strong for capitalizing on the tempo swing.

### vs. Mega Lucario ex (Riolu / Mega Lucario ex / Solrock-Lunatone)

Key opposing cards: Riolu (basic), Mega Lucario ex (MEG 77, 340 HP — *Aura Jab*: {F}, 130 dmg, reattaches up to 3 discarded Fighting-type Energy to their Bench; *Mega Brave*: {F}{F}, 270 dmg, can't reuse next turn), Solrock/Lunatone (draw engine, MEG 74/75).
- **Note: the source guide's line about attaching Psychic Energy to Latias ex to set up a Crispin-into-Eon Blade knockout on Mega Lucario ex does NOT apply to us — our decklist doesn't run Latias ex.** Rely on standard Phantom Dive lines instead.
- Standard opening, tank an early hit with Munkidori. Consider Itchy Pollen turn 1 (going second) or turn 2 (going first) if their opening looks weak (missing 2nd Riolu / Mega Lucario ex / Solrock-Lunatone), then follow with Phantom Dive.
- Main plan: repeated Phantom Dive, using Unfair Stamp + Phantom Dive when possible. Knock out a Riolu, then the Mega Lucario ex next turn, then another Riolu. Mega Lucario ex is energy-constrained (its own attacks discard/require heavy Fighting Energy investment), so denying their attachments (Crushing Hammer) is valuable. If they miss a KO at any point in the mid-game, they will likely lose.

**Supplemental notes (source: `matchups_dump/lucario.txt`, image-derived quick-reference from the deck owner):**
- Ideal initial board state per this note: 4 Drakloak + 1 Budew + **1 flexible "Slakoth" slot**. **Note: Slakoth (from the Legends set, unnumbered in our database, 60 HP — Take It Easy: heal 60 dmg from itself, can't retreat next turn) is NOT in our current 60-card decklist (Section 1).** Treat this as either (a) a tech option the deck owner sometimes swaps in specifically for this matchup that we should ask about if flexibility is desired, or (b) disregard the slot and rely on our standard Budew/Munkidori/Fezandipiti ex flex slots instead. Do not assume Slakoth is in the active decklist. **[v2] Still open — see Section 9, item 9.**
- Prize-check priority for this matchup: Energy, plus our usual Crispin/Boss's Orders counts. **[v3]** The original supplemental note's prize-check priority also named Lillie's Clefairy ex; per the v3 decision (not running it), drop that from the prize-check list — there's nothing to check for.
- **This general game plan applies across all Mega Lucario ex variants** (i.e., regardless of what specific support Pokémon they're running alongside Lucario).
- If they have a slow early game, punish with Phantom Dive to KO 2x Riolu, using Risky Ruins to help (**always item-lock early** in this matchup via Budew's Itchy Pollen).
- **[v3, rewritten — no Clefairy]** Once Mega Lucario ex is set up, the correct KO line is **Phantom Dive on a favorable turn, or Boss's Orders + Jet Headbutt/Dragon Headbutt if it's below a live breakpoint** — don't swing Phantom Dive directly into an *active* Mega Lucario ex expecting a clean kill (see the direct-swing warning two bullets down); wait for Munkidori's Adrena-Brain to have pre-loaded damage from a prior Phantom Dive bench spread, or gust it in already-damaged. They'll typically respond with Hariyama (MEG 73, 150 HP — Ability *Heave-Ho Catcher*: on evolve, switch in one of opponent's Benched Pokémon; Wild Press: {F}{F}{F}, 210 dmg, 70 recoil to self); a follow-up Phantom Dive after this forces them into playing another Mega Lucario ex, which can again be answered the same way.
- This matchup is generally favorable since we trade well whenever they try to KO our Dragapult ex.
- Don't let them get too far ahead early via **Solrock/Lunatone's draw engine** (MEG 74/75 — Lunatone's *Lunar Cycle*: discard a Fighting Energy to draw 3, requires Solrock in play; Solrock's *Cosmic Beam*: {F}, 70 dmg unless Lunatone is benched, ignores Weakness/Resistance).
- When using Phantom Dive, avoid swinging it directly into an active Mega Lucario ex (it likely survives and/or sets up a bad trade) — instead, gust (Boss's Orders) and KO **Makuhita (MEG 72, 80 HP) or Lunatone** (they typically run fewer copies of these support pieces, so removing them is higher value), while leaving damage on Solrock for a future Phantom Dive to pick up a 3-prize/multi-KO turn. **[v3, rewritten — no Clefairy]** Close the game out on their last Mega Lucario ex the same way as any other: gust it in with Boss's Orders once it's below a live Phantom Dive/Adrena-Brain breakpoint (Section 10's dynamic calculator), rather than a dedicated tech attacker's one-shot.


### vs. N's Zoroark ex (Pecharunt ex / Binding Mochi package)
Key opposing cards: N's Zoroark ex (JTG 98, 280 HP — Ability *Trade*: discard 1 card, draw 2; *Night Joker*: {D}{D}, uses a benched N's Pokémon's attack as this attack), Pecharunt ex (SFA 39, 190 HP — Ability *Subjugating Chains*: swaps a benched Darkness Pokémon into Active + Poisons it; *Irritated Outburst*: {D}{D}, 60 dmg × opponent's prizes taken), Binding Mochi (SFA 55, Tool — Poisoned Pokémon's attacks do +40 dmg to Active), **N's Reshiram (JTG 116, 130 HP — *Powerful Rage*: {R}{L}, 20 dmg × damage counters already on itself; *Virtuous Flame*: {R}{R}{L}●, 170 dmg)**, **N's Darmanitan (JTG 27, 140 HP — *Back Draft*: ●●, 30 dmg × Basic Energy cards in our discard pile; *Flamebody Cannon*: {R}{R}●, discards all its own Energy + 90 dmg to Active + 90 to a Benched Pokémon)**, **Black Belt's Training (PRE 96, Supporter — this turn, your Pokémon's attacks do +40 dmg to opponent's Active Pokémon ex)**.
- Standard opening; Budew is strong going second if they only find 1 Zorua early.
- Main goal: punish a weak/slow N's Zoroark ex opening, or set up strongly before they get going.
- **Key threats to avoid feeding a big Knockout on Dragapult ex:** N's Reshiram's *Powerful Rage* scales with damage counters already on itself (so it gets more dangerous the more it's been pre-damaged/healed-and-shifted around — be careful using Munkidori's Adrena-Brain to dump damage onto a Reshiram, as this can arm its own counter-attack), and the Munkidori/Pecharunt ex + Binding Mochi combo (Pecharunt ex's Irritated Outburst scales with prizes taken, and can be boosted +40 by Binding Mochi if Poisoned via Subjugating Chains) or Black Belt's Training (+40 dmg vs. our ex Pokémon for the turn) — these can combine to knock out a full-HP Dragapult ex, so be cautious about how many prizes you've let them take before committing your only/last Dragapult ex to the Active spot. Also watch N's Darmanitan's Back Draft, which scales with how many Basic Energy cards are in OUR discard pile — avoid over-discarding our own Energy (e.g. via Ultra Ball) late game vs. this matchup if Darmanitan is in play.

- To play around their own Adrena-Brain (Munkidori) shifting damage: spread Phantom Dive's 6 damage counters evenly (e.g., 20/20/20 across 3 Benched targets) rather than stacking them, so they can't cash in a single large shift for an easy follow-up KO.
- Their limited bench space is their biggest weakness — they can't fit all their strong Pokémon (N's Zoroark ex, Pecharunt ex, tech Pokémon) into play at once. Forcing a turn where they can only take 0 or 1 prize (instead of 2) usually wins the game for us.
- Late game: Unfair Stamp is strong here since it also strips their card draw (via removing N's Zoroark ex's "Trade" fuel) as well as ours.

### vs. Cynthia's Garchomp ex (Cynthia's Roserade support)
Key opposing cards: Cynthia's Gible → Cynthia's Gabite (DRI 102/103, Ability *Champion's Call*: search a Cynthia's Pokémon) → Cynthia's Garchomp ex (DRI 104, 330 HP — *Corkscrew Dive*: {F}, 100 dmg + draw to 6; *Draconic Buster*: {F}{F}, 260 dmg, discards all its own Energy), and Cynthia's Roselia → Cynthia's Roserade (DRI 7/8, Ability *Cheer On to Glory*: Cynthia's Pokémon's attacks do +30 dmg to opponent's Active).
- Going first is a big advantage here — you can often get a Phantom Dive in before they evolve into Cynthia's Garchomp ex. **[v2, review #1]** Per the revised Section 4 note, treat "before they evolve" as realistically turn 2–3, not a guaranteed turn 2 hit — push aggressively regardless, but don't assume the fastest case as the plan.
- Note: most of these lists lack Rare Candy, so their evolution line is slow — punish this by racing.
- Mid/late game: aim to remove 2-out-of-3 of either the Cynthia's Garchomp ex line or the Cynthia's Roserade line (prioritize Garchomp ex if forced to choose, unless 2 are already in play). Your prize map is typically "4 single-prizers + 1 Garchomp ex" or "2 Garchomp ex + 2 single-prizers."
- If targeting Roserade specifically, watch for their Boss's Orders forcing a bad trade late — a well-timed Unfair Stamp can protect your Dragapult ex from an incoming KO. Boss's Orders + Jet Headbutt onto a Roserade can set up a double-KO on two Roserade the following turn while denying them a KO in return.

### vs. Crustle / Mega Kangaskhan ex (Milotic ex tech)
Key opposing cards: **Crustle (DRI 12 — confirmed printing): Ability *Mysterious Rock Inn* — prevents ALL damage from Pokémon-ex attacks, meaning Phantom Dive/Cruel Arrow do NOTHING to it; *Superb Scissors*: {G}●●, 120 dmg ignoring Active's status effects.** Mega Kangaskhan ex (MEG 104, 300 HP, 3-prize — Ability *Run Errand*: draw 2 if in Active; *Rapid-Fire Combo*: ●●●, flip until tails, 50 dmg per heads), Milotic ex (SSP 42, 270 HP — Ability *Sparkling Scales*: blocks damage/effects from our Tera Pokémon [Dragapult ex has a Tera ability!] — this means Milotic ex may resist some interactions from a benched Dragapult ex's Tera ability specifically, though this needs live testing to confirm exact interaction **[v2, review #8] — UNCONFIRMED, treat as an open question (see Section 9, item 10), not a settled ruling**; *Hypno Splash*: {W}●●, 160 dmg + Sleep), **Hero's Cape (TEF 152, ACE SPEC Tool: +100 HP to the Pokémon it's attached to)** — this is likely the "big Crustle" with extra bulk referenced in the guide (150 HP + 100 = 250 HP Crustle).

- **Important: if the opposing Crustle is the DRI 12 printing with Mysterious Rock Inn, Phantom Dive (and any of our ex attacks) does ZERO damage to it.** In that case, rely on non-ex attackers instead — **Drakloak's Dragon Headbutt** (a Stage-1, non-ex attack) is the correct tool to break through Crustle, paired with Munkidori's Adrena-Brain to finish it off. With Hero's Cape attached, a Crustle could have up to 250 HP, requiring multiple Dragon Headbutts (70 dmg each) + Adrena-Brain shifts to bring down.
- Aim for a strong 3-Dreepy opening + Risky Ruins played early (try to bench multiple of their Pokémon at once to punish with Risky Ruins' damage-on-bench trigger).
- Their deck has limited card draw and no energy acceleration — aggressively strip their Energy with Crushing Hammer since they can't easily rebuild it.
- vs. Milotic ex specifically: attack with Fezandipiti ex's Cruel Arrow + Boss's Orders to trap/pick off Mega Kangaskhan ex or Crustle, while dealing with Milotic ex separately (they typically only run 1 Switch, so a trapped Milotic ex is hard for them to save). (Confirmed: the source's "Munkidori + Cruel Arrow" phrasing was just loose/informal shorthand referring to Fezandipiti ex's Cruel Arrow attack, not an actual Munkidori interaction.)

### vs. Marnie's Grimmsnarl ex (Froslass / Munkidori package)
Key opposing cards: Marnie's Impidimp → Morgrem → Grimmsnarl ex (DRI 134/135/136, 320 HP, 2-prize — Ability *Punk Up* (on evolve): search up to 5 basic Darkness Energy, attach to Marnie's Pokémon; *Shadow Bullet*: {D}{D}, 180 dmg + 30 to a Benched Pokémon), Froslass (TWM 53 — Ability *Freezing Shroud*: during Pokémon Checkup, 1 damage counter to every Pokémon with an Ability, both sides, except Froslass itself; *Frost Smash*: {W}●, 60 dmg). Note: this opposing deck also runs its own Munkidori copies (their Adrena-Brain works the same as ours, shifting damage to set up KOs on our side).
- Standard 3-Dreepy opening; consider Budew if it disrupts their Munkidori setup.
- Watch out for losing a Drakloak to their **Shadow Bullet (180+30 bench) + their own Adrena-Brain** combo — this can snowball a KO onto your Drakloak. Play around it by not letting a Drakloak sit at a damage total their Adrena-Brain can push over the edge.
- Useful lines: Jet Headbutt + our own Adrena-Brain + Boss's Orders to pick off Froslass; Phantom Dive + Adrena-Brain + Boss's Orders to double-KO their Munkidori copies (especially if Froslass's passive damage already helped soften them). Spreading Phantom Dive's damage evenly (e.g. 20/20/20) denies them a clean 30-damage Adrena-Brain shift for a KO.
- Their biggest weakness is that they eventually run out of Munkidori/Energy-search fuel — once their Munkidori chain dries up, you can start attacking Marnie's Grimmsnarl ex directly and should be favored.

**Supplemental notes (source: `matchups_dump/grimmsnarl.txt`, image-derived quick-reference from the deck owner):**
- Ideal desired board state per this note: 3 Drakloak + 2 Munkidori (after Budew). **[v3, rewritten — no Shaymin]** The original supplemental note also called for a Shaymin here; per the v3 decision (not running it) this is dropped from the target board state — 2 Munkidori is the actual ceiling this matchup builds toward. **[v2] Cumulative/across-the-game counts, not a literal simultaneous Bench — see the terminology note at the top of this section.**
- Prize-check priority: our Munkidori/Darkness Energy, Unfair Stamp, Boss's Orders counts, Crispin counts.
- **"Winning the Munkidori war" is the core of this matchup** — since Marnie's Grimmsnarl ex decks run their own Munkidori copies too, this is described as a mirror-style battle where "they are a worse version of you when you both set up" — i.e., we should expect to out-value them if both sides play the Adrena-Brain game correctly.
- **Tactical pattern: gust their Munkidori (Boss's Orders) while spreading damage to another target** (usually to secure a KO) — i.e., use Boss's Orders to pull a damaged/vulnerable Munkidori into the Active spot specifically to finish it off with spread damage, rather than just attacking whatever is already Active.
- **Item lock (Budew's Itchy Pollen) is unusually important in this matchup** because this opposing deck depends on Rare Candy to evolve into Grimmsnarl ex early — locking Items can meaningfully delay their whole game plan, not just tempo-stall.
- **Don't leave damage on board for them to abuse with their own Munkidori** — use Jet Headbutt instead of Phantom Dive if necessary to avoid handing them a big Adrena-Brain target (this reinforces the general "don't leave exploitable damage counters" theme seen in the N's Zoroark ex and Grimmsnarl main sections above).
- No Ancient/"Turo" Pokémon exist in the current format for this matchup, so that's not a concern (a note simplifying what would otherwise be a legacy format consideration).
- They have limited card draw overall, so **a well-timed Unfair Stamp can change the game** — pairing Stamp with Boss's Orders is called out as a "crucial" combined play to swing tempo.
- **[v3, rewritten — no Shaymin]** The original supplemental note called out Shaymin as protection against Shadow Bullet's bench-splash (180 to Active + 30 to a Benched Pokémon). Without it, that 30 bench-splash is a real, unmitigated threat every time they attack: it can be the exact chip that puts one of our support Pokémon inside their own Adrena-Brain's KO range. Actual mitigation without Shaymin is **positional, not defensive** — keep bench HP totals aware of this 30-damage floor (don't let a Dreepy/Budew/Munkidori sit at ≤30 remaining HP once Grimmsnarl ex is active and threatening to attack), and treat this as one more reason (alongside the 20/20/20 spread-damage discipline already noted below) to avoid leaving exploitable low-HP targets on the bench in this matchup.
- **If their Froslass is already set up, consider leaving it alive** while picking off their Munkidori copies instead — Froslass's Freezing Shroud passively damages all Ability-having Pokémon each turn (both sides, except Froslass itself), and since Munkidori has an Ability, **we can let Froslass's own passive chip away at their remaining Munkidori for us**, effectively turning their own tech against them, before finishing Froslass off later.

### vs. Mega Starmie ex (Staryu / Mega Starmie ex, Froslass sub-package)

> Source: `matchups_dump/mega starmie.txt`, image-derived quick-reference from the deck owner. New matchup not covered in `matchup_dump`.

Key opposing cards: Staryu (POR 20, 70 HP) → **Mega Starmie ex (POR 21, 330 HP, 3-prize — Jetting Blow: {W}, 120 dmg + 50 to a Benched Pokémon; Nebula Beam: ●●●, 210 dmg, ignores Weakness/Resistance and ignores any effects on our Active)**. This deck also runs a Froslass sub-package similar to the Marnie's Grimmsnarl ex matchup (see above for Froslass's Freezing Shroud/Frost Smash stats), plus **Mega Froslass ex (ASC 47, 310 HP, 3-prize — Resentful Refrain: {W}, 50 dmg × cards in OUR hand; Absolute Snow: {W}●●, 150 dmg, Sleeps our Active)** as a scaling attacker analogous to Alakazam's Powerful Hand (scales off *our* hand size rather than theirs).
- **Deck owner's own comparison: "Similar to the Grimmsnarl matchup but arguably easier."**
- **[v3, rewritten — no Shaymin]** The original supplemental note called Shaymin very strong early here specifically to blunt Jetting Blow's bench-splash (50 dmg to a Benched Pokémon). Without it, this is a genuine early vulnerability: this deck can "run you over" before our engine is online, and 50 unmitigated bench-splash per attack is a lot of chip against our low-HP support core. Mitigate positionally instead — avoid over-committing to the bench in the first 1-2 turns of this matchup specifically (prefer setting up Drakloak/Munkidori over rushing extra low-HP support onto the bench), since this deck's own strength drops off sharply once we're set up, per the source — the goal is surviving the early window, not neutralizing it.
- **Our own Dragapult ex 2-shots their Mega Starmie ex while only getting 3-shotted back** — a favorable damage race on paper (200+200=400 beats 330 HP in 2 hits, vs. their 3 hits of ~120-210 needed to take down a 320 HP Dragapult ex) — and **multiple Munkidori copies extend this further** by healing/shifting damage off our Dragapult ex to stay ahead of their attacks while tearing apart their board. **[v2, review #6]** As elsewhere, "multiple Munkidori copies" both running Adrena-Brain at once is bounded by the deck's 2-total Darkness Energy — treat the second Munkidori as a rotation piece, not a guaranteed simultaneous double-Adrena-Brain.
- **Energy-management discipline specific to this matchup:** focus on building up Munkidori's energy first; only Crispin energy onto an already-evolved Dragapult ex (not a Drakloak), since if you attach to a Drakloak instead, they will specifically target that Drakloak down (implying their deck has some way to prioritize/snipe a loaded Drakloak — likely via Boss's Orders or the Froslass/Starmie bench-hit attacks).
- **Keep your hand size low as soon as you evolve into Dragapult ex**, because of **Mega Froslass ex's Resentful Refrain** (50 dmg per card in OUR hand) — this only becomes a real threat if they have a Snorunt on their Bench (i.e., are actually building toward Mega Froslass ex), so watch for that piece specifically. **[v3]** No Shaymin to soften this one either — hand-size discipline (play down to a lean hand once Snorunt appears) is the only lever we actually have here.
- **We can out-value them on Boss's Orders** (the note states we typically play more copies than they do), so use this edge to target their Munkidori copies more aggressively/more often than they can target ours.
- **This deck has no real draw engine**, so **Unfair Stamp will usually "brick" them** — a strong, reliable disruption tool in this matchup specifically.
- **Watch for a Wally's Compassion play** (MEG 132, Supporter — heals all damage from one of their Mega Evolution Pokémon ex and returns all its attached Energy to hand if healed) — this is described as a major win condition for them since it lets them keep a damaged Mega Starmie ex/Mega Froslass ex alive indefinitely by resetting it back to full HP while recycling the Energy investment. Plan Phantom Dive/KO timing around denying them a comfortable Wally's Compassion window (e.g., try to secure a clean KO in one turn rather than leaving a heavily-damaged-but-alive Mega Pokémon ex for them to reset).
- Ideal boardstate per the note: 3 Drakloak + Munkidori, with Budew followed by Munkidori as the early sequencing. **[v3, rewritten — no Shaymin]** The original supplemental note also included Shaymin in this target board; dropped per the v3 decision. This matchup's early-game bench-splash exposure (Jetting Blow, and Resentful Refrain if Mega Froslass ex shows up) is accordingly a real weak point of this matchup for our build, not something the ideal board state resolves — see the two rewritten counterplay bullets above.

### vs. Raging Bolt ex Box (Teal Mask Ogerpon ex energy acceleration package)

> Source: `matchups_dump/ragingbolt.txt`, image-derived quick-reference from the deck owner. New matchup not covered in `matchup_dump`. Deck owner's own note: "similar to the mega box MU" (i.e., similar to the Mega Lucario ex/Crustle-style "Mega Box" matchup below), but described as generally easier for us.

Key opposing card: **Raging Bolt (SCR 111, 130 HP, Ancient — Thunderburst Storm: {L}{F}, 30 dmg to 1 of opponent's Pokémon for EACH Energy attached to Raging Bolt itself, ignoring Weakness/Resistance on Benched targets; Dragon Headbutt: {L}{F}●, 130 dmg)**. This deck relies heavily on **Teal Mask Ogerpon ex** (see Arboliva section above for full stats — Mountain Stroll search-2-Energy attack, Teal Dance draw engine) as its energy acceleration package to power up Raging Bolt's scaling Thunderburst Storm.
- Ideal initial board state per this note: 4 Drakloak + Moltres (the card actually in our decklist). **[v3, rewritten — no Shaymin/Clefairy]** The original supplemental note also called for Clefairy and Shaymin here; dropped per the v3 decision. **[v2] Cumulative counts, not a literal simultaneous Bench — see the terminology note at the top of this section.**
- Prize-check priority: Moltres, Crispin counts, Stadium counts, Boss's Orders counts.
- **Get aggressive with Moltres early.** **[v3, rewritten — no Shaymin/Clefairy]** Without Shaymin, surviving their "bby bolt" (baby Raging Bolt, i.e., an early underpowered Thunderburst Storm before they've attached much Energy to it) comes down to racing it down before it scales, not blocking its damage — prioritize Moltres picking off Teal Mask Ogerpon ex copies (below) over defensive bench management here, since denying their energy acceleration is what actually keeps Thunderburst Storm small.
- **Target down Teal Mask Ogerpon ex copies with Moltres** — since Ogerpon ex is Grass and weak to Fire, this is the same interaction documented in Section 2's Moltres write-up, confirmed here as the primary use case in this specific matchup (removing their energy-acceleration engine, not just chip damage).
- **"Just like [Mega Starmie], you don't need [Dragapult ex] in this MU"** — Moltres alone is described as strong enough to carry significant portions of this matchup, similar to the Arboliva and Mega Starmie notes above.
- **This matchup is generally easier than the "Mega Box" matchup** (see below) because, despite superficial similarity, **we have an easier time dealing with their attackers directly** — they're heavily reliant on Teal Mask Ogerpon ex for energy acceleration, so **Moltres alone can often "solo" this matchup** by continuously removing their Ogerpon ex copies before Raging Bolt ever gets enough Energy attached to threaten real damage via Thunderburst Storm.

### vs. "Mega Box" / Mega Lucario ex support shell (Absol / Area Zero Underdepths)

> Source: `matchups_dump/slopbox.txt` (titled "Mega Box" in the source, referred to informally as "slopbox" in the filename), image-derived quick-reference from the deck owner. New matchup not covered in `matchup_dump`. Likely a variant/relative of the Mega Lucario ex matchup already documented above, but run as a more generic "box" (support-toolbox) shell rather than a dedicated Riolu/Solrock-Lunatone line — treat as related to, but distinct from, the "vs. Mega Lucario ex" section above.

Key opposing cards: **Absol (PFL 63, 110 HP — Allure: draw 2 cards; Dark Cutter: {D}●, 60 dmg)** and **Area Zero Underdepths (SCR 131, Stadium — players with any Tera Pokémon in play can have up to 8 Benched Pokémon; if a player loses all Tera Pokémon, they must discard down to 5 Bench; when this Stadium leaves play, both players discard down to 5 Bench, playing player discards first)**.
- Ideal boardstate per this note: 3 Drakloak + 2 Munkidori + 1 Dragapult ex (i.e., unlike the Moltres/Shaymin-centric matchups above, this one wants our standard core engine online, no special tech Pokémon called for). **[v2] This one is fine as a literal simultaneous Bench (3+2+1=6, within the 5-Bench-plus-Active cap) — no ambiguity here, unlike the notes above.**
- **[v3, rewritten — no Clefairy]** The original supplemental note called out Clefairy for punishing this deck's over-extended bench (up to 8 Pokémon under Area Zero Underdepths) via its Follow Me gust. Without Clefairy, **our own Boss's Orders does the same job**: an opponent bench-spread across 8 slots thanks to Area Zero Underdepths has more, not fewer, exposed low-defense targets for a standard Boss's Orders + Phantom Dive/Jet Headbutt gust-and-KO — this doesn't need a dedicated tech attacker, just treating their over-extension as more Boss's Orders value than usual. **Since Area Zero Underdepths raises the Bench limit to 8 for BOTH players while any Tera Pokémon is in play (which our own Dragapult ex satisfies), we can also make use of the larger bench limit ourselves if useful, though the note frames this as primarily a way to punish their over-extension.**
- **Item lock early is valuable here** — specifically calls out that it "prevents [Switch] and Ultra Ball," slowing their ability to reposition/search.
- **Standard plan: establish Drakloak + Munkidori, then target their weaker support Pokémon ("liabilities") with Phantom Dive + Munkidori damage** — do not leave loose damage counters in play for them to exploit (consistent with the general "don't feed their damage-shifting tech" theme across multiple matchups).
- **"Only KO when you have a good board state due to [Unfair] Stamp"** — i.e., be mindful that taking a KO opens up their Unfair-Stamp-equivalent disruption window against us too; only initiate trades when our board can absorb a subsequent hand-disruption swing.
- **The only ways they can OHKO us are via Absol or their own Clefairy** — this narrows the threat assessment considerably: as long as neither of those specific cards is set up/lined up for a one-shot, we can play more loosely without fear of a surprise knockout.
- **They are slow to develop overall** ("they take a few turns to do anything") — so we can afford to spend early turns fully establishing our board state rather than rushing, unlike several of the faster matchups above (Arboliva, Alakazam).
- **Avoid playing Risky Ruins in this matchup** — the note states their own Stadium "helps you" instead (implying they run a Stadium whose effect benefits us, or that Risky Ruins specifically works against our own interests here, e.g. by punishing our own wide bench of low-HP support Pokémon more than theirs) — default to not contesting the Stadium slot unless a clear reason arises.

### vs. Dragapult ex mirror match

> Source: `matchups_dump/dragapult.txt`, image-derived quick-reference from the deck owner. This is the mirror matchup (opponent also plays some form of Dragapult ex deck, potentially with different tech choices like Latias ex or a Dusclops/Dusknoir line per the general Section 4 notes on going second vs. Dusknoir variants).

- **Ideal board state:** 3 Drakloak, 1-2 Munkidori, Budew.
- **Prize-check priority list (in the order given by the note):** cards you need in general (so you can confirm they aren't stuck in your prizes) → Munkidori/Energy → the Dragapult ex line itself → Boss's Orders counts → Unfair Stamp.
- **Core plan: build up a strong board state first**, and in this mirror, **you'll usually want to target down opposing Drakloak** rather than immediately going after their Dragapult ex — this denies their card-selection engine (Recon Directive) and delays their ability to evolve a second/third attacker, which matters enormously in a mirror where both sides have identical tools.
- **Race-to-initiate principle: try to be the first player to attack into a Dragapult ex, or into other meaningful targets like Drakloak** — but **only do this without leaving damage in play if you have your own Munkidori set up** to capitalize afterward. In other words, don't just trade blindly; if you can't immediately follow up on left-over damage with your own Adrena-Brain, reconsider the timing.
- **Only initiate a prize trade when your board is stable enough to play around an opposing Unfair Stamp.** This is a mirror match, so the opponent has access to the exact same Unfair Stamp disruption tool we do — over-committing to an early KO without a resilient follow-up board risks getting Stamped back into a bad position.
- **[v3, rewritten — no Clefairy]** The original supplemental note called for a well-timed Lillie's Clefairy ex + Unfair Stamp combo to punish an opponent's over-aggression when they lack a follow-up Dragapult ex. Without Clefairy, the equivalent line is **Unfair Stamp followed by a standard Phantom Dive/Boss's Orders close-out**: once Stamp has thinned their hand right after they whiffed a follow-up attacker, our own board (assuming the "build a strong board state first" plan above was followed) should already be able to convert that window into prizes without needing a dedicated one-shot tech piece. **Only commit to this aggressive close-out if you're confident the opponent will struggle to return a KO** — same caveat as the original note, just executed with cards actually in the 60.
- **Avoid benching "liabilities" like Latias ex and Fezandipiti ex early.** The reasoning given: Risky Ruins (which either side may have in play) plus a Boss's Orders gust makes an exposed multi-prize Pokémon (Latias ex is 2-prize; also applies to our own Fezandipiti ex) an easy target for the opponent, **"as there is no [Tera] on it"** — i.e., unlike Dragapult ex, these support ex Pokémon have no Tera-style benched-damage-immunity, so a Risky-Ruins-damaged Fezandipiti ex sitting on the Bench is vulnerable to a gust-and-KO in a way that a benched Dragapult ex simply isn't. (Note: Latias ex itself is not in our decklist — this line is carried over from the source's original build, but the underlying principle fully applies to our own Fezandipiti ex, which we do run.) **[v2, review #7 — corrected]** To be precise about what makes it "easy": Risky Ruins itself only contributes 2 damage counters (20 damage) on entry to the Bench — nowhere near threatening a 210 HP Fezandipiti ex by itself. The actual danger is the Boss's Orders gust *followed by a real attack*; Ruins is a minor assist toward a breakpoint (or toward triggering Adrena-Brain), not the thing that makes the KO happen. Don't read "easy target" as Ruins+Boss's-Orders alone being lethal pressure.

### vs. Arboliva ex (Meganium / Teal Mask Ogerpon ex spread-and-scale)


> Source: a TCGplayer deck guide article for Arboliva ex (by Natalie Millar), provided directly by the user (not from `dump`/`matchup_dump`). Cross-referenced against our card database to confirm exact effects.

**Their full gameplan:** an aggressive, fast-setup deck built around two Grass Stage-2 lines run *without Rare Candy*, made viable by **Forest of Vitality** (Stadium — lets your Grass Pokémon evolve into Grass Pokémon the turn you play them, except during your own first turn). This lets them go from Basic to fully-evolved Stage 2 in a single turn starting their own turn 2. They lean on **Dawn** (search a Basic + Stage 1 + Stage 2 Pokémon) and **Bug Catching Set** (top 7, take up to 2 Grass Pokémon/Basic Grass Energy) alongside 4 Ultra Ball / 4 Lillie's Determination for consistency, and **always choose to go first** every game.

**Key opposing cards (confirmed against our card database):**
- **Smoliv (DRI 21) → Dolliv (DRI 22) → Arboliva ex (DRI 23)**, 60/90/310 HP. Arboliva ex is the main attacker:
  - **Oil Salvo**: cost {G} (a single Grass Energy!) — choose 1 of the opponent's Pokémon **6 times** (can repeat the same target), 20 damage each time, **unaffected by Weakness/Resistance**. This is extremely flexible: they can dump all 120 damage onto one target (e.g., nearly/fully KO a benched Dreepy [70 HP] or Drakloak [90 HP], or chip 120 off our Active), OR spread it thinly across our whole bench to snipe multiple weak support Pokémon at once. Critically cheap (1 Energy) for the damage output, and available as early as their own turn 2.
  - **Aroma Shot**: ●●● (3 colorless), 160 dmg, cures own status conditions.
- **Chikorita (MEG 8) → Bayleef (MEG 9) → Meganium (MEG 10)**, 70/110/160 HP. This is their **secondary utility Stage-2 line**, not a primary attacker — its role is the Ability:
  - **Wild Growth** (Meganium, passive Ability): each Basic Grass Energy attached to **any of their Pokémon** provides {G}{G} (counts double) instead of {G}. Does not stack with a 2nd Meganium. **This is their scaling/consistency engine** — it effectively halves their real energy investment needed for Aroma Shot's 3-cost and for pumping Myriad Leaf Shower higher. **Meganium itself is a low-HP (160) non-attacking linchpin** — see counterplay note below.
  - Bayleef's Push Down ({G}●, 50 dmg, switches opponent's Active to Bench, opponent picks) is a minor disruption tool while Bayleef is still on the way up the evolution line.
- **Teal Mask Ogerpon ex (TWM 25)**, 210 HP, Tera(Grass) — run at 4 copies, the deck's real scaling payoff:
  - **[Tera] Ability**: while benched, prevents all damage to it (same protective mechanic as our own Dragapult ex).
  - **Teal Dance Ability** (once/turn): attach a Basic Grass Energy from hand to this Pokémon; if you did, draw a card. A repeatable draw engine that also loads up its own attack.
  - **Myriad Leaf Shower**: {G}{G}{G}, base 30 dmg, **+30 more damage for each Energy attached to BOTH Active Pokémon** (their attacker's energy count AND our Active's energy count both add to this). With Wild Growth doubling each physical Grass Energy's count and several turns of Teal Dance stacking energy onto one Ogerpon ex, this scales to 300+ damage (the article's own example: 4 physical Energy on Ogerpon ex with Wild Growth active + 2 Energy on our target = 330 total damage) — **enough to one-shot a full-HP Dragapult ex (320 HP) or anything else in the format.**
- **Noctowl (Jewel Seeker Ability, printed as SCR 115 in our database, referenced as PRE-78 in the article — same effect)**: once per turn, when played from hand to evolve a Pokémon, if they have any Tera Pokémon in play (they always will, via Teal Mask Ogerpon ex), search deck for up to 2 Trainer cards into hand. Major consistency piece, can dig for their ACE SPEC or Forest of Vitality specifically.
- **Budew (ASC 16)** — same card/role as in our own deck (early stall + chip, especially valuable going second, which this deck rarely does).
- **Meowth ex / Fezandipiti ex** — same cards/roles as in our own deck (Supporter search on bench, draw-on-KO engine).
- **ACE SPEC (flex slot, article says either is reasonable):**
  - **Unfair Stamp (TWM 165)** — same card we run; disrupts our hand and draws them extra cards, especially usable right after they take a KO (which Noctowl density helps enable).
  - **Scoop Up Cyclone (TWM 162, ACE SPEC)** — "Put 1 of your Pokémon and all attached cards into your hand." Not in our own decklist; if they run this instead, it protects their Meowth ex/Fezandipiti ex/Noctowl from being trapped/gusted for a bad trade (Boss's Orders style plays lose value against this), and can also save a nearly-KO'd Meganium/Arboliva ex by returning it to hand — notably they can often replay a returned Arboliva ex/Meganium immediately thanks to Forest of Vitality's evolve-same-turn effect, effectively "healing" it back to full HP with minimal tempo loss.
- **They explicitly do not run Judge** (article: author considered it but decided it doesn't help enough against single-prize aggro decks) — this doesn't prevent *us* from using our own Judge against them, see counterplay below.

**Important self-assessment from the article's author (direct quote-derived):** *"I've found this deck to be mainly strong against Dragapult ex decks and other ex-heavy decks."* **This means the article's own author considers this matchup favorable for Arboliva ex against us — treat this as an unfavorable/uphill matchup and prioritize the specific counterplay below rather than a generic gameplan.**

**Counterplay takeaways for our deck:**
- **Don't over-extend a fragile bench early.** Since Oil Salvo costs only 1 Energy and can be online as early as their own turn 2, and it freely chooses any single target 6 times for 20 unresisted damage each, a loaded bench of Dreepy (70 HP)/Budew (30 HP)/Munkidori/Meowth ex/Fezandipiti ex is very exposed to a single early Oil Salvo either sniping one support Pokémon dead or spreading 20-damage chip across several. Weigh how many low-HP support Pokémon you truly need in play before their turn 2 against this specific matchup.
- **Meganium is the priority target, not Arboliva ex.** Meganium itself doesn't attack for real damage and has only 160 HP — a single Phantom Dive (200 dmg) or even Jet Headbutt (70) + a follow-up cleanly knocks it out. **Removing Meganium kills Wild Growth, which cripples both Aroma Shot's effective cost AND Myriad Leaf Shower's scaling ceiling** — this is a much higher-leverage KO than trading with the tankier 310 HP Arboliva ex. Use Boss's Orders to drag Meganium into the Active spot specifically for this if it's sitting safely on the Bench.
- **Watch our own energy count on our Active Pokémon.** Myriad Leaf Shower's damage scales with the combined Energy count on *both* Active Pokémon — meaning the more Energy we've attached to our own Active (e.g., a fully-loaded 2-Energy Dragapult ex ready for Phantom Dive), the harder their Myriad Leaf Shower hits us back. Since Dragapult ex's Tera ability only protects it while **benched** (not Active), a heavily-energized Active Dragapult ex is a bigger target for a one-shot than an unenergized one. Consider attacking and then retreating a spent, energy-loaded Dragapult ex back to the (safe) Bench when possible, rather than leaving it sitting Active into their next turn.
- **Crushing Hammer still has value** even though Oil Salvo only needs 1 Energy to function — it directly slows Wild Growth's scaling (fewer physical Grass Energy on board = less doubled Energy for Myriad Leaf Shower) and delays Aroma Shot's 3-cost.
- **Our own Judge is good here despite them skipping it themselves** — since this is a fast, evolution-line-dependent deck reliant on specific pieces (Forest of Vitality, Dawn, Bug Catching Set) rather than a big stocked hand, shuffling their hand away on a turn where they're missing a key setup piece can meaningfully set back their curve, especially since they have two separate Stage-2 lines to assemble without Rare Candy.
- **Race consideration:** since their fastest attacker (via either line) is online starting their own turn 2 regardless of who goes first, our own early Phantom Dive is *especially* important here — **[v2, review #1]** per the revised Section 4 note, expect this realistically on turn 2 only in a strong opening and turn 3 more often, but the earlier it lands the better here specifically, since it can deny them the bench-space/energy investment needed to make Myriad Leaf Shower threatening later.
- **Boss's Orders value is high** here beyond just Meganium — Teal Mask Ogerpon ex is only protected by Tera while *benched*; if it's ever forced Active before they're ready (e.g., a slow opening), a gusted Ogerpon ex (210 HP) is a clean 2-prize target for Phantom Dive + a follow-up.

**Supplemental notes (source: `matchups_dump/arboliva.txt`, image-derived quick-reference from the deck owner — describes a build variant that also runs Moltres and Shaymin; Moltres IS in our current decklist, Shaymin is not):**
- Ideal board state per this note: 4 Drakloak + Budew (Moltres played after). **[v3, rewritten — no Shaymin]** The original supplemental note also called for Shaymin here; per the v3 decision (not running it) this is dropped from the target board state. **This is a genuine, un-patched weakness of our build in this matchup**: our current 60 has no direct answer to Oil Salvo's bench-spread beyond raw HP and disciplined bench management (below) — that's not resolved by anything else in the list, it's just the matchup we're playing.
- Prize-check priority: Moltres, our Energy counts, Boss's Orders counts, Night Stretcher counts.
- **Moltres is confirmed here independently as a great card in this matchup** — reinforces the Section 2 note about Moltres sniping Grass-type ex's — because Arboliva needs to set up multiple Teal Mask Ogerpon ex both to power up its attackers (Myriad Leaf Shower scaling) and to draw cards (Teal Dance), giving Moltres many potential OHKO targets.
- **You often don't need to evolve into Dragapult ex much in this matchup** — Moltres alone can reportedly take up to 4 prize cards solo (i.e., OHKOing multiple ex Ogerpon over the course of a game), making it a more central win condition here than usual.
- **[v3, rewritten — no Shaymin]** The original supplemental note said Shaymin substantially blunts Arboliva ex's spread plan by blocking Oil Salvo's bench-sniping outright. Without it, **the only mitigation is not giving Oil Salvo a target worth taking**: keep the bench lean early (don't rush Munkidori/Meowth ex/Fezandipiti ex out ahead of when they're needed), and treat this matchup as one where Moltres racing down their Ogerpon ex copies matters more than usual, since every turn Oil Salvo goes unanswered is a free 20-120 damage against a bench we can't otherwise protect.
- Even when Moltres can't OHKO Arboliva ex itself, it's still a good attacker since its knockouts set up multi-prize turns for a follow-up Dragapult ex/Phantom Dive.
- **Avoid benching low-HP Pokémon mid-game** in this matchup specifically, since Arboliva ex can snipe them freely via Oil Salvo and we have no way to block it (confirms/reinforces the "don't over-extend a fragile bench" counterplay point above — this is now the primary defensive lever in this matchup, not a fallback for "if you don't have Shaymin").
- **If a Dragapult ex is damaged, retreat it to keep it safe** — this deck typically runs low counts of Boss's Orders, and critically, **Arboliva ex's Oil Salvo cannot target a Benched Dragapult ex for damage while its Tera ability is active** (Tera blocks all attack damage to Benched Pokémon, and Oil Salvo is still an attack). This is a stronger, more concrete version of the "retreat a spent Dragapult ex to the Bench" counterplay note above — it's not just safer, it's **fully immune** to their entire spread attack while benched.
- **If you have prized (lost to prizes) your own Moltres, Unfair Stamp + KO'ing Meganium is a solid backup plan** — falls back to the "Meganium is the priority target" line from the main counterplay section above when the Moltres plan isn't available.

---

## 9. Question log

**[v2]** v1 marked this section "all resolved" and carried a top-of-doc "FINAL" banner despite six live card-inclusion flags scattered through Section 8 plus a couple of other loose ends — that was a documentation-integrity problem (review finding #3), not a wording nitpick. This log now separates what's genuinely settled (1–6, unchanged from v1) from what's still open (7–10, newly tracked here instead of being left as scattered inline flags).

**[v3]** Items 7 and 8 are now resolved (decision below) and moved out of "Open."

**Resolved (from v1):**
1. **Unidentified cards from matchup_dump** — Resolved: N's Reshiram (JTG 116), N's Darmanitan (JTG 27), Black Belt's Training (PRE 96), and Hero's Cape (TEF 152) were all found and added to the relevant matchup sections above.
2. **Crustle printing** — Resolved/confirmed: DRI 12 (Mysterious Rock Inn, blocks all ex-attack damage) is the correct printing for this matchup.
3. **"Munkidori + Cruel Arrow" phrasing** — Resolved/confirmed: this was just loose/informal phrasing in the source referring to Fezandipiti ex's Cruel Arrow, not an actual Munkidori interaction.
4. **Remaining matchups in the source guide** (Ogerpon ex Box & Raging Bolt ex, Meganium Box, Mega Starmie ex, Okidogi, Festival Lead, Rocket's Honchkrow, Mega Lopunny ex/Dudunsparce, Slowking) — confirmed `matchup_dump` only contains full write-ups for the 6 matchups covered in Section 8; the source file cuts off mid-list ("Continue to next page" after Marnie's Grimmsnarl ex). Can be added later if more content becomes available.
5. **Damage breakpoints** — Resolved: dynamic/predictive calculation approach documented in Section 10.
6. **Discard sequencing guidance** — Resolved: draft reviewed and approved by user, documented in Section 11.

**Resolved in v3:**
7. **Should Shaymin be added to the decklist?** **Decided: no.** Sticking with the Section 1 decklist as-is. This means the Arboliva, Grimmsnarl, Mega Starmie, and Raging Bolt matchups genuinely lack an answer to bench-spread chip damage (Oil Salvo, Jetting Blow, Shadow Bullet's splash) beyond bench-management discipline — this is now documented as a real matchup weakness in each of those sections (Section 8), not an open question.
8. **Should Lillie's Clefairy ex (JTG 56) be added to the decklist?** **Decided: no.** Sticking with the Section 1 decklist as-is. Matchup sections that cited Clefairy as their answer (Alakazam intel aside — that reference is about a card *the opponent* might play, not our own tech; Mega Lucario ex, Mega Box, mirror match) have been rewritten in Section 8 to use Phantom Dive/Boss's Orders/Moltres/Unfair Stamp lines instead, using only cards in the actual 60.

**Still open:**
9. **Is the "Slakoth" flex slot (Mega Lucario ex supplemental) real?** Not in the current decklist; unclear whether it's an occasional tech swap or a stale reference from an older list.
10. **Does Milotic ex's Sparkling Scales actually interact with a benched Dragapult ex's Tera ability?** Flagged in the Crustle/Mega Kangaskhan ex section as needing live testing — currently speculative, should be confirmed (or the speculative sentence dropped) before anything is built assuming a specific ruling here.

**Known scope gaps (not board-legality/factual bugs, just things this doc doesn't cover — see review finding #9):** this doc doesn't specify mulligan handling, a default rule for which Basic to promote after the Active is KO'd, or a tie-break rule for turns where multiple Supporters (e.g. Lillie's Determination and Crispin) are simultaneously legal and no matchup note applies. These are reasonable to leave to a narrative strategy doc, but anyone building heuristics off this doc alone will need to supply those defaults from elsewhere — they are not hiding in a section that got missed.

---

## 10. Damage breakpoint calculation approach (confirmed by user)

**Breakpoints should be calculated dynamically, not hardcoded**, based on live HP/attack values from the card database. However, the bot should do this planning **predictively**, not just reactively:

- When the bot sees an opponent's early-game Pokémon (e.g., a Riolu), it should look ahead at what that Pokémon is likely to evolve into (e.g., Mega Lucario ex) using the opponent's likely archetype/known evolution lines, and pre-calculate whether its own current/planned attacks (Phantom Dive's 200 dmg, Jet Headbutt's 70 dmg, Dragon Headbutt's 70 dmg, Cruel Arrow's 100 dmg, plus Adrena-Brain's up-to-30 dmg shift and Phantom Dive's up-to-60 dmg bench spread) would be capable of knocking out that evolved form once it appears.
- This means the bot's planning shouldn't just be "can I KO what's in front of me right now" but "given what I know about this opponent's deck archetype (from the matchup notes in Section 8, or general meta knowledge), what is this Pokémon likely to become, and do I have/can I get enough damage output ready for when it does."
- Concretely: maintain/derive HP and attack-damage values from the card database at runtime (rather than hardcoding a fixed breakpoint table in this doc), and combine that with matchup-specific foreknowledge (Section 8) to anticipate future breakpoints rather than only reacting to the current board state.
- Special case reminders for the calculator: some opposing abilities change whether damage lands at all (e.g., Crustle's Mysterious Rock Inn blocking all ex-attack damage, Milotic ex's Sparkling Scales blocking Tera-Pokémon interactions) — dynamic breakpoint math must account for these blockers, not just raw HP math.

---

## 11. Discard-sequencing guidance for Ultra Ball / Poké Pad / Buddy-Buddy Poffin

Since only 2 Night Stretcher exist for recursion (Pokémon or Basic Energy back from discard), discards should be prioritized to preserve the deck's ability to recover its most important resources. Priority order for **what to discard first** (least costly to lose → most costly):

1. **Excess/duplicate copies of trainer cards already at their functional max for the game** (e.g., a redundant extra Buddy-Buddy Poffin/Poké Pad/Ultra Ball once the board is already fully set up) — these have no discard-pile recursion value at all in this deck (no Trainer recursion card is run), so once their utility is spent, they're the cheapest thing to discard.
2. **Excess Basic Energy beyond what's needed to fuel 2 Phantom Dives + Munkidori's Darkness requirement.** Since Fire/Psychic are needed in a 1:1 pair for Phantom Dive, and only 1 Darkness is typically needed at a time for Munkidori, discarding a 3rd+ copy of Fire or Psychic Energy is low-risk — Night Stretcher or Crispin can recover one from discard if needed later. Avoid discarding your only remaining copy of Darkness Energy if Munkidori is likely to be needed for Adrena-Brain later, since Crispin is the only other source of Darkness Energy.
3. **Non-attacker Basic Pokémon that are already "spent"** (e.g., a Budew that already used Itchy Pollen and has no further role, or a redundant extra Meowth ex copy — though this deck only runs 1) — these can be discarded via Ultra Ball if bench space or hand space is needed, since prioritize saving Night Stretcher for your attacker line rather than a spent support Pokémon.
4. **Avoid discarding Dreepy/Drakloak/Dragapult ex copies via Ultra Ball if at all possible** — these are the deck's core win condition and are hard-capped at 4/4/3 copies; losing one to an Ultra Ball discard (rather than a battlefield KO) is pure card disadvantage with no prize-trade compensation. Only discard one of these if the hand is otherwise completely dead and no other discard option exists, and even then prefer discarding a 4th Dreepy over a Drakloak or Dragapult ex.
5. **Never discard your only copy of Boss's Orders, Unfair Stamp (ACE SPEC — irreplaceable, only 1 allowed in deck), or your last Crispin** if there's any alternative — these are highly load-bearing for the deck's win condition and are far more valuable in hand than recoverable later (Night Stretcher can't retrieve Supporters/Items, only Pokémon and Basic Energy).

**General principle:** since this deck's only recursion for discarded cards is 2x Night Stretcher (Pokémon/Basic Energy only) and Crispin (Basic Energy only), anything that is NOT a Pokémon or Basic Energy discarded via Ultra Ball is gone for good — so Trainer/Item/Supporter cards used for their one-time effect (once played, not discarded via Ultra Ball) aren't a concern here; this guidance is specifically about Ultra Ball's "discard 2 other cards" cost.

---
*(v1 of this document was marked complete; v2 reopened the six card-inclusion questions in Section 9 and applied the wording/math fixes above; v3 resolves the Shaymin/Clefairy questions (Section 9, items 7–8) as "not adding either" and rewrites every dependent matchup section in Section 8 to use only decklist cards. Items 9–10 remain open. Future updates should append new sections/matchups as new information becomes available, rather than re-declaring this FINAL until Section 9's remaining open items are closed.)*
