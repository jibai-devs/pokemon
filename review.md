# Dragapult/Munkidori Agent Heuristics Review Brief

## Purpose

This document is an implementation-review brief for an autonomous Pokemon TCG agent piloting the current Dragapult ex / Munkidori list.

The goal is **not** to blindly implement every proposed module. The goal is to compare the proposed architecture against the existing heuristics implementation, then decide what to:

- implement now,
- modify to fit the current codebase,
- defer,
- ignore,
- or replace with a simpler heuristic.

The reviewing agent should make pragmatic decisions based on expected gameplay improvement, implementation complexity, latency impact, and compatibility with the existing system.

---

## Deck Context

This deck is **not Dragapult/Dusknoir**.

It is a **Dragapult ex / Munkidori tempo-control deck**.

Key list features:

- 4 Dreepy
- 4 Drakloak
- 3 Dragapult ex
- 2 Munkidori
- 2 Budew
- 1 Moltres
- 1 Fezandipiti ex
- 1 Meowth ex
- 4 Lillie's Determination
- 3 Crispin
- 3 Boss's Orders
- 4 Crushing Hammer
- 4 Poke Pad
- 4 Ultra Ball
- 4 Buddy-Buddy Poffin
- 2 Night Stretcher
- 1 Unfair Stamp
- 1 Risky Ruins
- 1 Team Rocket's Watchtower
- 4 Fire Energy
- 3 Psychic Energy
- 2 Darkness Energy

The deck's stated win condition is:

1. Set up 2-3 Dragapult ex.
2. Chain **Phantom Dive**.
3. Convert bench spread into knockouts using **Munkidori's Adrena-Brain**.
4. Use **Boss's Orders** and prize mapping to reach 6 prizes first.

This means the implementation should treat the deck as a **tempo-control and prize-mapping deck**, not a burst-combo deck.

---

## Big Picture Strategic Model

The agent should evaluate the deck through this lens:

```text
Primary plan:
Maintain a continuous Dragapult ex attack chain.

Secondary plan:
Use Phantom Dive spread to create future knockout thresholds.

Conversion plan:
Use Munkidori to move damage counters into exact KO math or prevent return KOs.

Control plan:
Use Budew, Crushing Hammer, Judge, Xerosic, Unfair Stamp, and Stadiums to slow the opponent.

Closing plan:
Use Boss's Orders to convert damaged targets into prizes.
```

The core question each turn is:

```text
Can I preserve tempo while converting spread damage into exact prize math over multiple turns?
```

The agent should **not** optimize only for immediate prizes. This deck often wins by preserving pressure and making the opponent's next board state worse.

---

## Non-Negotiable Strategic Rule

The most important rule for this deck:

```text
Do not sacrifice the Dragapult attack chain for a low-value tactical play.
```

Many bad autonomous decisions will come from choosing an attractive immediate action, such as Boss or disruption, while failing to maintain next-turn Phantom Dive.

Examples of bad trades:

- Boss a damaged one-prizer but fail to prepare the next Dragapult.
- Use a disruption Supporter when Crispin is required to attack next turn.
- Attach Darkness to the wrong Pokemon and fail to power the next Dragapult.
- Use Munkidori for irrelevant damage instead of preserving a defensive heal or future threshold.

The reviewer should check whether existing heuristics already enforce this principle. If not, this should be one of the first additions.

---

## Proposed Architecture

Recommended architecture:

```text
GameState
  -> Derived State Evaluation
  -> Tactical Checks
  -> Deck-Specific Heuristic Modules
  -> Optional Shallow Search
  -> Best Action Sequence
```

Recommended module order:

```text
1. Lethal Line Finder
2. Opponent Lethal Prevention
3. Dragapult Chain Planner
4. Prize Conversion Finder
5. Phantom Dive Damage Allocator
6. Munkidori Adrena-Brain Evaluator
7. Boss's Orders Selector
8. Tempo Disruption Evaluator
9. Energy Sequencing Planner
10. Recovery Planner
11. Optional Shallow Beam Search
```

The reviewer should compare this list against the current implementation and classify each module as:

```text
IMPLEMENT_NOW
MODIFY_EXISTING
DEFER
IGNORE
ALREADY_COVERED
```

---

## Recommended Review Output

After reviewing the current heuristics, produce a decision table like this:

| Proposed Module | Current Coverage | Recommendation | Reason | Expected Impact | Latency Risk |
|---|---|---|---|---|---|
| Dragapult Chain Planner | Partial / None / Good | Implement / Modify / Defer | ... | High / Med / Low | High / Med / Low |
| Phantom Dive Allocator | ... | ... | ... | ... | ... |
| Munkidori Evaluator | ... | ... | ... | ... | ... |
| Boss Selector | ... | ... | ... | ... | ... |
| Shallow Search | ... | ... | ... | ... | ... |

Then produce a first implementation plan:

```text
First PR:
- ...
- ...
- ...

Second PR:
- ...
- ...
- ...

Deferred:
- ...
- ...
```

---

# Module Details

## 1. Dragapult Chain Planner

### Purpose

Ensure the deck can keep attacking with Phantom Dive every turn.

This should be one of the highest-priority modules.

### Why It Matters

This deck does not have the same burst comeback potential as Dusknoir variants. If the Dragapult chain breaks, the deck loses pressure and may fall behind permanently.

### The Agent Should Ask

```text
Can I Phantom Dive this turn?
Can I Phantom Dive next turn?
If this Dragapult is KO'd, do I have another attacker ready?
Do I have Fire + Psychic access?
Do I need Crispin this turn?
Do I need to recover a Dragapult line piece?
```

### Suggested Evaluation

```python
def dragapult_chain_score(state):
    score = 0

    if can_phantom_dive_this_turn(state):
        score += 1000

    if has_backup_dragapult_ready(state):
        score += 700

    if has_backup_dreepy_or_drakloak_path(state):
        score += 350

    if has_energy_for_next_dragapult(state):
        score += 450

    if has_crispin_or_energy_access(state):
        score += 300

    if has_night_stretcher_for_recovery(state):
        score += 150

    if only_one_dragapult_and_opponent_can_ko_it(state):
        score -= 900

    if energy_attachment_breaks_future_attack_chain(state):
        score -= 600

    return score
```

### Review Guidance

Implement or strengthen this if the current agent:

- uses Boss too aggressively,
- uses disruption instead of setup,
- fails to prepare a backup Dragapult,
- attaches energy to low-value targets,
- or attacks once but cannot continue pressure.

### Recommendation Bias

This module should usually be **IMPLEMENT_NOW** unless the existing implementation already handles it well.

---

## 2. Phantom Dive Damage Allocator

### Purpose

Choose where to place the 6 bench damage counters from Phantom Dive.

### Strategic Difference From Dusknoir

This deck does not use Dusknoir burst math. Instead, damage should create:

- Munkidori KO thresholds,
- future Boss targets,
- next-turn Phantom Dive KOs,
- softened future attackers,
- or pressure on support engines.

### Important Thresholds

```text
30 HP remaining  = one Adrena-Brain can finish.
60 HP remaining  = Phantom Dive bench damage can finish.
90 HP remaining  = repeated Munkidori / spread can finish.
200 HP remaining = Phantom Dive active hit can finish.
230 HP remaining = Phantom Dive + one Munkidori correction.
260 HP remaining = Phantom Dive + two Munkidori corrections.
```

### Suggested Scoring

```python
def score_phantom_allocation(state, allocation):
    after = apply_phantom_dive_bench_damage(state, allocation)

    score = 0
    score += 100000 * wins_game(after)
    score += 800 * immediate_bench_ko_count(after)
    score += 500 * creates_boss_ko_target(after)
    score += 420 * creates_munkidori_ko_target(after)
    score += 320 * creates_next_turn_phantom_ko(after)
    score += 280 * damages_likely_next_attacker(after)
    score += 250 * damages_engine_piece(after)
    score += 180 * creates_multiple_threats(after)
    score -= 250 * wasted_overkill_damage(after)
    score -= 150 * damage_on_low_priority_target(after)

    return score
```

### Search Note

This space is small.

If there are 5 opposing Benched Pokemon, distributing 6 counters across them has only 210 possible allocations.

That means this module can usually be brute-forced exactly without meaningful latency cost.

### Review Guidance

Implement or modify this if the current agent:

- spreads damage randomly,
- always stacks all 60 damage on one target,
- ignores future Boss lines,
- ignores Munkidori thresholds,
- or fails to damage the future attacker.

### Recommendation Bias

Usually **IMPLEMENT_NOW**.

This is high impact and low latency.

---

## 3. Munkidori Adrena-Brain Evaluator

### Purpose

Evaluate when and where to use Munkidori's Adrena-Brain.

### Strategic Model

Munkidori should be treated as:

```text
Move 30 damage from my board to their board.
```

This can be offensive or defensive.

### Offensive Uses

- Finish a low-HP Pokemon.
- Put a Pokemon into Phantom Dive range.
- Put a Pokemon into Boss + attack range.
- Remove a support engine.
- Damage the likely next attacker.

### Defensive Uses

- Remove damage from Dragapult.
- Prevent opponent's return KO.
- Preserve the only available attacker.
- Remove damage from a two-prize liability.

### Suggested Evaluation

```python
def evaluate_adrena_brain_use(state, source, target):
    after = apply_adrena_brain(state, source, target)

    offensive = 0
    offensive += 100000 * wins_game(after)
    offensive += 700 * takes_prize(after)
    offensive += 500 * creates_boss_target(after)
    offensive += 400 * puts_target_in_phantom_dive_range(after)
    offensive += 300 * removes_engine_piece(after)
    offensive += 300 * removes_future_attacker(after)

    defensive = 0
    defensive += 600 * prevents_my_dragapult_ko(after)
    defensive += 350 * preserves_only_attacker(after)
    defensive += 250 * removes_damage_from_two_prize_liability(after)

    cost = 0
    cost += 200 * wastes_movable_damage(after)
    cost += 250 * targets_low_value_pokemon(after)

    return offensive + defensive - cost
```

### Hard Rules

```text
Do not use Adrena-Brain if it does not:
- take a KO,
- create a threshold,
- remove or damage an important threat,
- or prevent a meaningful KO on your board.
```

```text
If moving 30 damage off Dragapult changes the opponent's next attack from KO to non-KO, heavily prioritize it.
```

### Review Guidance

Implement or strengthen this if the current agent:

- uses Adrena-Brain just because it is available,
- ignores defensive healing,
- fails to finish low-HP bench targets,
- or moves damage to low-value Pokemon.

### Recommendation Bias

Usually **IMPLEMENT_NOW**.

This is one of the deck's most important skill-testing modules.

---

## 4. Boss's Orders Selector

### Purpose

Use Boss's Orders to convert spread damage into prizes or tempo.

### Strategic Model

Boss is not just gust.

In this deck, Boss is a **prize-map conversion card**.

### Good Boss Targets

- Damaged two-prize Pokemon.
- Opponent's likely next attacker.
- Support engine Pokemon that enables the opponent's comeback.
- Final prize target.
- High-retreat Pokemon that can be stranded.

### Bad Boss Targets

- Random damaged one-prizer.
- A Pokemon that cannot be KO'd or stranded.
- A target that does not affect the prize map.
- A target that forces the agent to skip Crispin and break the attack chain.

### Suggested Evaluation

```python
def evaluate_boss_target(state, target):
    after_boss = simulate_boss_to_active(state, target)

    score = 0
    score += 100000 * wins_game_with_attack(after_boss)
    score += 900 * can_ko_target_this_turn(after_boss)
    score += 700 * removes_likely_next_attacker(after_boss)
    score += 600 * takes_two_prizes(after_boss)
    score += 400 * strands_high_retreat_pokemon(after_boss)
    score += 350 * denies_engine(after_boss)
    score += 300 * creates_clean_next_turn_prize_map(after_boss)

    score -= 500 * breaks_dragapult_chain_due_to_not_using_crispin_or_lillie(state)
    score -= 300 * boss_without_ko_or_disruption(after_boss)
    score -= 250 * boss_on_low_value_one_prizer(after_boss)

    return score
```

### Review Guidance

Implement or modify this if the current agent:

- Bosses damaged Pokemon without clear purpose,
- ignores the next attacker,
- uses Boss when Crispin is needed,
- or fails to close games with Boss.

### Recommendation Bias

Usually **IMPLEMENT_NOW** if Boss mistakes are common.

---

## 5. Tempo Disruption Evaluator

### Purpose

Use disruption to buy extra Phantom Dive turns.

Relevant cards:

- Crushing Hammer
- Budew
- Judge
- Xerosic's Machinations
- Unfair Stamp
- Risky Ruins
- Team Rocket's Watchtower

### Strategic Model

Disruption is valuable when it reduces the opponent's next-turn quality while your own Dragapult chain remains intact.

The agent should not disrupt randomly.

### Crushing Hammer

Hammer should be evaluated by expected value.

```python
def evaluate_crushing_hammer_target(state, energy_target):
    heads_state = remove_energy(state, energy_target)

    heads_value = evaluate_opponent_threat_reduction(heads_state)
    tails_value = 0

    expected_value = 0.5 * heads_value + 0.5 * tails_value

    if energy_target.enables_next_attack:
        expected_value += 250

    if energy_target.on_only_attacker:
        expected_value += 300

    if energy_target.is_hard_to_replace:
        expected_value += 200

    return expected_value
```

Hard rule:

```text
Never choose a line that is only good if Crushing Hammer hits unless the current position is otherwise losing.
```

### Budew

Budew should usually be used as a bridge before Dragapult is online.

```text
Use Budew when:
- Dragapult is not ready,
- opponent is Item-dependent,
- and Budew buys a setup turn.

Do not use Budew when:
- Dragapult can Phantom Dive,
- opponent is already established,
- or the prize race demands immediate damage.
```

### Judge / Xerosic / Unfair Stamp

Use hand disruption when:

- the opponent is likely to have a strong response,
- your own attack chain is secure,
- and the disruption compounds existing board pressure.

Avoid hand disruption when:

- you need Crispin or Lillie's Determination to maintain your own chain,
- the opponent is already weak,
- or the disruption does not change the next-turn threat.

### Review Guidance

Implement or strengthen this if the current agent:

- fires off disruption with no timing,
- uses Budew after Dragapult is online,
- uses Hammer on irrelevant energy,
- or uses Judge/Stamp when it needs setup.

### Recommendation Bias

Usually **MODIFY_EXISTING** or **DEFER** unless disruption mistakes are a major issue.

This module is useful, but secondary to Dragapult chain, damage allocation, Munkidori, and Boss.

---

## 6. Energy Sequencing Planner

### Purpose

Correctly attach and search energy for Dragapult and Munkidori.

### Strategic Model

Energy has different jobs:

```text
Fire + Psychic = Dragapult attack chain.
Darkness = Munkidori activation.
```

The agent must not waste Darkness attachments or mis-sequence Crispin.

### Suggested Evaluation

```python
def evaluate_energy_attachment(state, target, energy):
    score = 0

    if attachment_enables_phantom_dive_this_turn(state, target, energy):
        score += 1000

    if attachment_enables_next_turn_dragapult(state, target, energy):
        score += 700

    if attachment_enables_munkidori_adrena_brain(state, target, energy):
        score += 500

    if attachment_to_backup_dragapult_preserves_chain(state, target, energy):
        score += 450

    if attachment_strands_energy_on_low_value_pokemon(state, target, energy):
        score -= 400

    if attachment_consumes_last_darkness_without_munkidori_need(state, energy):
        score -= 350

    return score
```

### Crispin Guidance

Crispin should be valued highly when it:

- enables Phantom Dive this turn,
- sets up next-turn Phantom Dive,
- builds a backup Dragapult,
- or fixes mixed-energy requirements.

Crispin should usually beat Boss if Boss does not take important prizes or deny the opponent's next attack.

### Review Guidance

Implement or strengthen this if the current agent:

- attaches Darkness incorrectly,
- fails to prepare Fire/Psychic for Dragapult,
- uses Boss when Crispin is required,
- or strands energy on low-value Pokemon.

### Recommendation Bias

Usually **IMPLEMENT_NOW** if energy mistakes are common. Otherwise **MODIFY_EXISTING**.

---

## 7. Recovery Planner

### Purpose

Use Night Stretcher only when it restores a concrete line.

### Priority

Recover in this order:

```text
1. Dragapult ex line pieces needed to continue the chain.
2. Dreepy or Drakloak if the board was cleared.
3. Munkidori if Adrena-Brain is central to the endgame.
4. Fezandipiti ex / utility Pokemon only if immediately relevant.
```

### Suggested Evaluation

```python
def evaluate_night_stretcher_use(state, target_card):
    score = 0

    if target_card_restores_dragapult_chain(state):
        score += 900

    if target_card_enables_attack_this_or_next_turn(state):
        score += 700

    if target_card_enables_munkidori_prize_conversion(state):
        score += 500

    if target_card_is_not_needed_this_game(state):
        score -= 300

    return score
```

### Hard Rule

```text
Do not use Night Stretcher just because a Pokemon is in discard.
Use it when it restores a concrete line.
```

### Review Guidance

This is likely lower priority unless current play logs show recovery mistakes.

### Recommendation Bias

Usually **DEFER** or **MODIFY_EXISTING**.

---

# Shallow Search Guidance

## Should This Deck Use Shallow Search?

Yes, but selectively.

A full search over all legal actions is probably unnecessary and may be too slow.

However, this deck benefits significantly from shallow search in three areas:

```text
1. Lethal and prize-conversion checks.
2. Phantom Dive damage allocation.
3. Boss + Munkidori + attack sequencing.
```

The reviewer should determine whether the current implementation already handles these through rules. If not, shallow search may be worth adding.

---

## Where Shallow Search Is Worth It

### A. Lethal Finder

This should be exact if possible.

Search combinations of:

- Boss target
- Adrena-Brain usage
- attack choice
- Phantom Dive bench counter allocation
- Stadium-related damage if applicable

Pseudo-code:

```python
def find_lethal_line(state):
    lines = []

    for pre_actions in generate_pre_attack_tactical_actions(state):
        s1 = simulate_actions(state, pre_actions)

        for boss_target in possible_boss_targets(s1):
            s2 = simulate_optional_boss(s1, boss_target)

            for adrena_line in possible_adrena_brain_lines(s2):
                s3 = simulate_actions(s2, adrena_line)

                for attack in legal_attacks(s3):
                    for allocation in legal_damage_allocations(attack, s3):
                        s4 = simulate_attack(s3, attack, allocation)

                        if my_prizes_taken_this_turn(s4) >= state.prizes_remaining:
                            lines.append((pre_actions, boss_target, adrena_line, attack, allocation))

    return best_line(lines)
```

Recommended decision:

```text
IMPLEMENT_NOW if not already present.
```

---

### B. Phantom Dive Allocation

This should be brute-forced.

The action space is small enough that this is better than hand-written rules alone.

Recommended decision:

```text
IMPLEMENT_NOW.
```

---

### C. Boss + Munkidori + Attack Prize Conversion

This is where many autonomous agents make mistakes.

Search only meaningful branches:

```text
Optional Boss
Optional Adrena-Brain lines
Attack
Damage allocation
End-of-turn evaluation
```

Do not search every setup card here. This should be a tactical search, not a full-turn general search.

Recommended decision:

```text
IMPLEMENT_NOW or MODIFY_EXISTING.
```

---

## Where Shallow Search May Not Be Worth It

Avoid or defer shallow search for:

```text
- Every possible Ultra Ball discard combination.
- Every possible Poke Pad outcome.
- Every possible Lillie's Determination branch.
- Long opponent simulations.
- Full multi-turn game trees.
- Coin-flip-dependent Hammer lines.
```

These are likely to create latency or complexity without enough benefit.

Use heuristics instead.

---

## Optional Beam Search

A small beam search can be useful after tactical modules fail.

Recommended shape:

```python
def beam_search_general_turn(state, deadline, beam_width=8, max_depth=12):
    beam = [(evaluate_partial_state(state), state, [])]

    for depth in range(max_depth):
        if time_now() > deadline:
            break

        candidates = []

        for score, s, line in beam:
            actions = generate_relevant_actions(s)

            for action in actions:
                if not is_legal(action, s):
                    continue

                s2 = apply_action(s, action)
                score2 = evaluate_partial_state(s2)
                candidates.append((score2, s2, line + [action]))

        if not candidates:
            break

        candidates.sort(key=lambda x: x[0], reverse=True)
        beam = candidates[:beam_width]

    return max(beam, key=lambda x: evaluate_end_of_turn(x[1]))
```

Recommended use:

```text
Use beam search only after:
1. no lethal is found,
2. no obvious prize-conversion line is found,
3. chain preservation is not forced,
4. and disruption/setup choices remain ambiguous.
```

Recommended decision:

```text
DEFER unless current rules frequently fail in mid-turn sequencing.
```

If implemented, keep it small:

```text
beam_width = 8 to 12
max_depth = 10 to 16
strict deadline
fallback policy always available
```

---

# Board Evaluation

If the implementation uses scoring, prefer a table-driven evaluator.

Example:

```json
{
  "win_game": 100000,
  "can_phantom_this_turn": 1200,
  "next_attack_secure": 900,
  "backup_dragapult_ready": 700,
  "munkidori_thresholds": 250,
  "boss_targets": 300,
  "phantom_bench_thresholds": 180,
  "adrena_available": 250,
  "movable_damage": 80,
  "opponent_attack_denied": 700,
  "opponent_engine_damaged": 250,
  "opponent_can_ko_dragapult": 800,
  "opponent_can_win_next_turn": 5000,
  "supporter_access": 120,
  "energy_access": 180,
  "recovery_available": 100
}
```

The reviewer should not copy these weights blindly.

Instead:

1. Compare with current heuristic weights.
2. Identify missing concepts.
3. Add the smallest number of new terms that fix observed bad decisions.
4. Tune based on game logs and regression tests.

---

# Opponent Threat Abstraction

Do not fully simulate the opponent unless the existing code already supports it cheaply.

Use a fast approximation:

```python
def estimate_opponent_threat(state):
    return {
        "likely_next_attacker": identify_likely_next_attacker(state),
        "can_attack_next_turn": estimate_energy_attack_readiness(state),
        "can_ko_dragapult_next_turn": estimate_damage_output_vs_dragapult(state),
        "can_win_next_turn": estimate_prize_lethal(state),
        "energy_dependency_score": estimate_energy_bottleneck(state),
        "engine_dependency_score": estimate_engine_bottleneck(state)
    }
```

Use this threat model to inform:

- Boss target selection,
- Crushing Hammer target selection,
- Judge / Xerosic / Stamp timing,
- Munkidori defensive healing,
- whether to preserve a backup Dragapult.

Recommended decision:

```text
MODIFY_EXISTING or DEFER.
```

This is valuable, but only after the agent has solid internal deck heuristics.

---

# Regression Tests

Regression tests are likely the highest ROI improvement.

Every bad game decision should become a board-state test.

## Must-Have Tests

```text
1. Do not Boss if it breaks the Dragapult chain.
2. Use Crispin over Boss when no major prize conversion exists.
3. Use Boss when it takes a damaged two-prizer.
4. Use Adrena-Brain to prevent Dragapult KO.
5. Use Adrena-Brain to finish a Bench support Pokemon.
6. Do not waste Adrena-Brain on irrelevant damage.
7. Use Budew only when Dragapult is not ready and opponent is Item-dependent.
8. Hammer the only powered attacker before random energy.
9. Place Phantom Dive counters to create Munkidori thresholds.
10. Preserve Night Stretcher for Dragapult chain recovery.
11. Attach Darkness to Munkidori only when Adrena-Brain matters.
12. Use Unfair Stamp / Judge only when own attack chain is secure.
```

Example:

```python
def test_crispin_over_boss_when_chain_at_risk():
    state = load_state("chain_at_risk_boss_low_value.json")
    line = choose_turn_plan(state, deadline=100)

    assert contains_action(line, "Crispin")
    assert not contains_action(line, "Boss's Orders")
```

```python
def test_adrena_brain_defensive_heal_prevents_ko():
    state = load_state("dragapult_damaged_by_30_over_ko_threshold.json")
    line = choose_turn_plan(state, deadline=100)

    assert contains_action(line, "Adrena-Brain")
    assert adrena_source_is_dragapult(line)
```

```python
def test_phantom_dive_sets_munkidori_threshold():
    state = load_state("bench_target_can_be_set_to_30_remaining.json")
    line = choose_turn_plan(state, deadline=100)

    allocation = extract_phantom_allocation(line)
    assert creates_munkidori_ko_threshold(state, allocation)
```

Recommended decision:

```text
IMPLEMENT_NOW.
```

Regression tests should be used to decide whether a proposed heuristic is actually helping.

---

# Implementation Priority

If time is limited, prioritize:

```text
1. Dragapult Chain Planner
2. Phantom Dive Damage Allocator
3. Munkidori Evaluator
4. Boss Selector
5. Regression Tests
```

Then add:

```text
6. Energy Sequencing Planner
7. Tempo Disruption Evaluator
8. Lethal / Prize Conversion Shallow Search
9. Recovery Planner
10. Opponent Threat Abstraction
11. Optional Beam Search
```

Recommended first PR:

```text
First PR:
- Add derived state fields for Dragapult chain status.
- Add Phantom Dive allocation scoring using Munkidori/Boss thresholds.
- Add Adrena-Brain offensive/defensive evaluator.
- Add regression tests for the most common bad decisions.
```

Recommended second PR:

```text
Second PR:
- Add Boss target scoring.
- Add Crispin vs Boss vs Lillie Supporter priority.
- Add energy sequencing rules for Fire/Psychic/Darkness.
- Add more regression tests from logs.
```

Recommended third PR:

```text
Third PR:
- Add exact lethal finder.
- Add tactical Boss + Munkidori + attack search.
- Add lightweight opponent threat abstraction.
```

Recommended deferred work:

```text
Deferred:
- General beam search.
- Deep opponent simulation.
- Complex probabilistic modeling of draw outcomes.
- Full matchup-specific profiles.
- Exhaustive Ultra Ball discard search.
```

---

# What To Ignore Or Avoid

The reviewing agent should be skeptical of overengineering.

Avoid:

```text
1. Full-game tree search.
2. Long opponent simulations.
3. Searching every possible card sequencing branch.
4. Overfitting to one matchup before core heuristics are stable.
5. Treating Crushing Hammer heads as guaranteed.
6. Treating Munkidori like Dusknoir burst.
7. Using disruption when the Dragapult chain is not secure.
8. Adding many weights without regression tests.
```

If a proposed module does not fix an observed bad decision or improve a major strategic weakness, defer it.

---

# Final Checklist For The Reviewing Agent

When reviewing the current implementation, answer these questions:

```text
1. Does the current agent preserve the Dragapult attack chain?
2. Does it correctly value Crispin when energy continuity matters?
3. Does it place Phantom Dive counters to create Munkidori/Boss thresholds?
4. Does it use Adrena-Brain both offensively and defensively?
5. Does it avoid wasting Adrena-Brain?
6. Does it use Boss to convert damage into prizes or tempo, not just because a target is damaged?
7. Does it avoid Budew when Dragapult can already attack?
8. Does it target Crushing Hammer at energy that matters?
9. Does it preserve Night Stretcher for concrete recovery lines?
10. Does it have regression tests for known bad decisions?
11. Is shallow search used only where the tactical space is small and valuable?
12. Does every new heuristic have a measurable reason to exist?
```

The implementation should be judged by whether it makes fewer strategically bad decisions, not by whether it looks sophisticated.

---

# Recommended Final Agent Philosophy

```text
No LLM.
No open-ended reasoning.
No full-game search unless absolutely necessary.

Use:
- exact legality,
- strong derived state features,
- threshold-based damage math,
- Dragapult chain preservation,
- Munkidori offensive/defensive conversion,
- Boss-based prize mapping,
- selective shallow search,
- and regression tests from real mistakes.
```

In one sentence:

```text
Build the agent around continuity of Phantom Dive pressure, then use Munkidori, Boss, and disruption to convert that pressure into a clean prize map.
```
