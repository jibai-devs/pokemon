# Fire Deck — Game Walkthrough

## How the Agent Plays

`pokemon-play` (a.k.a. `python -m pokemon`) runs the fire deck against a random agent.

### Game Flow

```
Step   1: P0 — COIN FLIP -> go first
Step   2: P0 — PLAY Gouging Fire ex
Step   5: P0 — END TURN                          [Gouging Fire ex HP=230 E=1]
Step  10: P0 — ATTACH Energy                     [Gouging Fire ex HP=210 E=2]
Step  14: P0 — PLAY Festival Grounds
RESULT: WIN (16 steps)
```

### What the Agent Does Each Turn

1. **Coin flip** — Always goes first
2. **Play Pokemon** — Put basics (Gouging Fire ex, Slugma) on bench
3. **Evolve** — Slugma → Magcargo ex when possible
4. **Attach energy** — One Fire Energy per turn to active Pokemon
5. **Attack** — Use strongest available attack
6. **Use trainers** — Search cards, draw cards, play tools
7. **End turn** — When no more actions available

### Decision Priority

| Priority | Action | Score |
|----------|--------|-------|
| 1 | Evolve Slugma → Magcargo ex | 95 |
| 2 | Attach energy (0 on active) | 95 |
| 3 | Play Gouging Fire ex | 90 |
| 4 | Play Slugma | 85 |
| 5 | Use Lillie's Determination (draw) | 85 |
| 6 | Attach energy (<3 on active) | 80 |
| 7 | Use Team Rocket's Petrel (search) | 80 |
| 8 | Use Secret Box | 75 |
| 9 | Use Ultra Ball (search) | 70 |
| 10 | Select target | 70 |
| 11 | Use Mega Signal | 65 |
| 12 | Select prize | 65 |
| 13 | Attach energy (3+ on active) | 60 |
| 14 | Play Festival Grounds | 60 |
| 15 | Use Powerglass (tool) | 55 |
| 16 | End turn | 10 |

### Example Game States

**Early game (Step 2):**
```
Active: Gouging Fire ex HP=230 Energy=0
Bench: 0 Pokemon
Hand: 7 cards
```

**Mid game (Step 10):**
```
Active: Gouging Fire ex HP=210 Energy=2
Bench: 1 Pokemon (Slugma)
Hand: 6 cards
```

**Late game (Step 14):**
```
Active: Gouging Fire ex HP=210 Energy=2
Bench: 1 Pokemon
Hand: 7 cards
Playing: Festival Grounds (Stadium)
```

### Performance

- **Win rate**: 50% vs random agent
- **Avg game length**: ~40 steps
- **Strategy**: Simple priority-based scoring
- **Weakness**: Doesn't adapt to opponent's board state

## Running the Game

```bash
# Run the agent
uv run pokemon-play -g 5 -v        # or: uv run python -m pokemon -g 5 -v

# Output:
# === FIRE DECK AGENT ===
# Deck: 60 cards
#
# Game: 21 steps, result=WIN
# Game: 33 steps, result=WIN
# Game: 40 steps, result=LOSS
# ...
#
# === RESULTS (20 games) ===
# Wins: 10 (50%)
# Losses: 10 (50%)
```

## Code Structure

```python
# src/pokemon/agent.py (+ decks.py, catalog.py)

FIRE_DECK = [46]*2 + [76]*4 + [30]*4 + ...  # 60 cards (pokemon.decks)

def fire_agent(obs):
    if obs['select'] is None:
        return DECK  # Submit deck
    
    # Score each option
    for opt in options:
        if opt['type'] == 3:   # Play Pokemon → score 85-95
        if opt['type'] == 7:   # Attach energy → score 60-95
        if opt['type'] == 13:  # Attack → score by damage
        if opt['type'] == 14:  # End turn → score 10
    
    return best_options
```
