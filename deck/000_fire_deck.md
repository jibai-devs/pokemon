# 000 Fire Deck

Fire-type deck built around Gouging Fire ex and Magcargo ex.

## Deck List

| Count | Card ID | Name | Type |
|-------|---------|------|------|
| 2 | 46 | Gouging Fire ex | Pokemon (Basic) |
| 4 | 76 | Slugma | Pokemon (Basic) |
| 4 | 30 | Magcargo ex | Pokemon (Stage 1) |
| 1 | 1092 | Secret Box | Item (ACE SPEC) |
| 2 | 1121 | Ultra Ball | Item |
| 2 | 1145 | Mega Signal | Item |
| 2 | 1163 | Powerglass | Tool |
| 4 | 1219 | Team Rocket's Petrel | Supporter |
| 4 | 1227 | Lillie's Determination | Supporter |
| 2 | 1245 | Festival Grounds | Stadium |
| 33 | 2 | Basic Fire Energy | Energy |

**Total: 60 cards**

## Card IDs (for agent use)

```python
deck = (
    [46]*2 +      # Gouging Fire ex
    [76]*4 +      # Slugma
    [30]*4 +      # Magcargo ex
    [1092] +      # Secret Box
    [1121]*2 +    # Ultra Ball
    [1145]*2 +    # Mega Signal
    [1163]*2 +    # Powerglass
    [1219]*4 +    # Team Rocket's Petrel
    [1227]*4 +    # Lillie's Determination
    [1245]*2 +    # Festival Grounds
    [2]*33        # Basic Fire Energy
)
```

## Key Attacks

- **Gouging Fire ex** — Heat Blast (60 for {R}{C}), Blaze Blitz (260 for {R}{R}{C})
- **Magcargo ex** — Hot Magma (70 for {R}{C}), Ground Burn (140+ for {R}{R}{C})

## Strategy

1. Lead with Slugma or Gouging Fire ex
2. Evolve Slugma into Magcargo ex
3. Attach Fire Energy and attack
4. Use trainers to search and draw into evolutions/energy
5. Gouging Fire ex is the main damage dealer (260 dmg)

## Performance

- 50% win rate vs random agent (always-pick-first strategy)
- A smarter decision-making agent would improve results significantly
