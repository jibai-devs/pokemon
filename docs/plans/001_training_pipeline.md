# Training Data Pipeline

How to get training data from Kaggle episode replays and turn it into (state, action) samples for behavioral cloning and RL.

---

## 1. Getting replays from Kaggle

```bash
# List episodes for your own submission
kaggle competitions episodes <submission-id>

# List episodes for any public submission (leaderboard agents)
kaggle competitions episodes <their-submission-id>

# Download a single replay
kaggle competitions replay <episode-id>
# → writes episode-<id>-replay.json to the current directory

# Download agent logs (for debugging)
kaggle competitions logs <episode-id> 0   # agent index 0 or 1
```

You can bulk-download replays from top-rated submissions by scraping their submission IDs from the leaderboard, then looping over episode IDs. Each replay is ~50–200 KB of JSON.

---

## 2. Replay JSON format

A downloaded replay is a JSON object with a `"steps"` key:

```json
{
  "steps": [
    [
      { "action": [...], "observation": {...}, "reward": null, "status": "ACTIVE" },
      { "action": [...], "observation": {...}, "reward": null, "status": "INACTIVE" }
    ],
    ...
  ],
  "info": { "EpisodeId": 12345 }
}
```

Each element of `steps` is a two-element list `[player_0_state, player_1_state]`.

After a full game runs locally via `env.run()`, the engine also attaches a richer `"visualize"` array to `steps[0][0]["visualize"]`. This array has one frame per decision point with `{obs, action}` pairs pre-extracted — prefer this format when available, since it's already aligned.

**Visualize frame structure:**
```json
{
  "<engine vis fields>": "...",
  "obs": {
    "select": { "type": 8, "context": 3, "minCount": 1, "maxCount": 1, "option": [...] },
    "logs": [...],
    "current": { "turn": 4, "yourIndex": 0, "players": [...], "result": -1, ... }
  },
  "action": [[chosen_idx_p0], [chosen_idx_p1]]
}
```

---

## 3. Extracting training samples

A training sample is a **(observation, chosen_option_indices)** pair at each decision point.

Skip steps where `obs["select"]` is `None` (deck submission phase or terminal).

```python
# Pseudocode — see scripts/parse_replay.py for the real implementation
for frame in vis_frames:
    obs = frame["obs"]
    if not obs["select"]:
        continue
    active_idx = obs["current"]["yourIndex"]
    chosen = frame["action"][active_idx]   # list of int indices into obs["select"]["option"]
    yield obs, chosen
```

The dataset from a single 10-minute game session of ~1000 episodes yields roughly **30,000–100,000 decision samples** (depending on game length).

---

## 4. Featurization

The network needs fixed-size tensors. Featurize each sample into three tensors:

### 4a. Board state vector

All floats. Normalise HP as `hp / maxHp`, counts as `count / max_possible`.

| Feature group | Fields | Size |
|---|---|---|
| Turn info | `turn/100`, `supporterPlayed`, `energyAttached`, `retreated` | 4 |
| My active | `card_id_emb` (32d), `hp_ratio`, `energy_count/10`, `has_tool` | 35 |
| My bench × 5 | same per slot (zero-pad empty slots) | 175 |
| My counts | `handCount/20`, `deckCount/20`, `prizes_left/6` | 3 |
| My status | `poisoned`, `burned`, `asleep`, `paralyzed`, `confused` | 5 |
| Opp active | `card_id_emb`, `hp_ratio`, `energy_count/10` | 34 |
| Opp bench × 5 | same (no hand visible) | 170 |
| Opp counts | `handCount/20`, `deckCount/20`, `prizes_left/6` | 3 |
| Opp status | same 5 flags | 5 |
| **Total** | | **~434** |

Card ID embedding: learnable `nn.Embedding(1267, 32)` — do not one-hot (too sparse).

### 4b. Per-option feature vector

One vector per available option. Options vary in number (typically 1–15).

| Option type | Extra features | Total size |
|---|---|---|
| 0 (OK/NUMBER) | `number/10` | 16 |
| 1 (GO FIRST) | — | 15 |
| 2 (GO SECOND) | — | 15 |
| 7 (PLAY) | `card_id_emb` of card in hand | 47 |
| 8 (ATTACH) | `card_id_emb` of energy/tool, `target_area`, `target_index/5` | 49 |
| 9 (EVOLVE) | `card_id_emb` of evolution, `target_area`, `target_index/5` | 49 |
| 13 (ATTACK) | `attack_id_emb` (32d), `damage/300` | 48 |
| 14 (END TURN) | — | 15 |
| other | — | 15 |

Pad all to the same size (49) and prepend a one-hot option-type indicator (15 dims) → **64d per option**.

Attack ID embedding: `nn.Embedding(1556, 32)`.

### 4c. Label

Integer index (or list of indices if `maxCount > 1`) into the option list.

---

## 5. Network architecture

The key constraint: option lists are variable length, so the output head must score each option independently rather than use a fixed-size softmax.

```
board_state (434d)
    │
    ▼
BoardEncoder (MLP or small transformer)
    │
    board_vec (256d)
    │
    ├──────────────────────────────────────┐
    │                                      │
    │  for each option_i (64d):            │
    │    OptionEncoder(option_i) → 64d     │
    │    score_i = MLP(cat(board_vec,      │
    │                      option_vec_i))  │
    │    → scalar logit                    │
    │                                      │
    ▼                                      ▼
policy = softmax(scores)           value = MLP(board_vec) → scalar
```

Training:
- **Behavioral cloning phase:** cross-entropy loss on chosen index vs. all options
- **RL fine-tuning phase:** PPO with `value` head; reward = game outcome (+1 / -1 / 0)

Self-play opponent for RL: start with the rule-based agent (faster convergence than random).

---

## 6. Tooling

| Script | Purpose |
|---|---|
| `scripts/parse_replay.py` | Parse a replay file or run a local game; print each step human-readably |
| `scripts/featurize.py` *(todo)* | Convert replay JSON → numpy arrays ready for training |
| `scripts/train_bc.py` *(todo)* | Behavioral cloning training loop |
| `scripts/train_rl.py` *(todo)* | PPO fine-tuning loop |

### parse_replay.py quick reference

Parsing a replay file is pure Python — run it anywhere (PowerShell, WSL, doesn't matter):

```powershell
# Parse a downloaded Kaggle replay (prints first 20 decision steps)
uv run python scripts/parse_replay.py episode-12345-replay.json

# Show more steps
uv run python scripts/parse_replay.py episode-12345-replay.json --max-steps 50

# Dump full obs JSON for a specific step index (useful for debugging featurization)
uv run python scripts/parse_replay.py episode-12345-replay.json --dump-step 7
```

`--local` spins up the game engine (`libcg.so`) so it **requires WSL**:

```bash
# In a WSL terminal
~/.local/bin/uv run python scripts/parse_replay.py --local

# Or from PowerShell
wsl -e bash -c "cd /mnt/c/Users/Luqman/Desktop/projects/pokemon && ~/.local/bin/uv run python scripts/parse_replay.py --local"
```

Output marks chosen options with `»`.

---

## 7. Open questions / things to verify

- **Replay format confirmation:** download one real Kaggle replay and run `parse_replay.py` on it to confirm the `steps` structure matches what's documented here. The `visualize` key may or may not be present in downloaded replays (it's written by `cabt.py`'s `finish()` locally — Kaggle may or may not include it).
- **Opponent hand visibility:** in the active player's observation, `players[opp]["hand"]` is `None` — only `handCount` is visible. Featurize opponent hand as count only.
- **select.type vs. OptionType enum:** the DOCS.md option type table in AGENTS.md was derived from live observation; validate against `docs/plans/000_plan_engine_enum_extraction.md` before finalising the option encoder.
- **maxCount > 1:** some select contexts allow picking multiple options (e.g., discarding multiple cards). The current architecture handles this by scoring all options and taking the top-k by logit; verify this matches the engine's expectations.
