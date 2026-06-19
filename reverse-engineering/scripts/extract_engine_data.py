#!/usr/bin/env python3
"""Extract all data from libcg.so — card database, attack database, and more."""

import ctypes
import json
import os

# ─── Load the library ────────────────────────────────────────────────────────
lib_dir = os.path.join(os.path.dirname(__file__), "..", "data", "sample_submission", "cg")
lib_path = os.path.join(lib_dir, "libcg.so")
lib = ctypes.cdll.LoadLibrary(lib_path)

# ─── Initialize ──────────────────────────────────────────────────────────────
lib.GameInitialize()
print("[+] GameInitialize() done")

# ─── Set return types ────────────────────────────────────────────────────────
lib.AllCard.restype = ctypes.c_char_p
lib.AllAttack.restype = ctypes.c_char_p
lib.AgentStart.restype = ctypes.c_void_p

# ─── 1. Dump ALL CARDS ──────────────────────────────────────────────────────
print("[*] Calling AllCard()...")
raw_cards = lib.AllCard()
cards_json = raw_cards.decode("utf-8")
cards = json.loads(cards_json)

out_cards = os.path.join(os.path.dirname(__file__), "..", "data", "all_cards.json")
with open(out_cards, "w") as f:
    json.dump(cards, f, indent=2)
print(f"[+] Wrote {len(cards)} cards to {out_cards}")

# Show a sample card to understand the schema
print("\n=== SAMPLE CARD (first entry) ===")
print(json.dumps(cards[0], indent=2))

# ─── 2. Dump ALL ATTACKS ────────────────────────────────────────────────────
print("\n[*] Calling AllAttack()...")
raw_attacks = lib.AllAttack()
attacks_json = raw_attacks.decode("utf-8")
attacks = json.loads(attacks_json)

out_attacks = os.path.join(os.path.dirname(__file__), "..", "data", "all_attacks.json")
with open(out_attacks, "w") as f:
    json.dump(attacks, f, indent=2)
print(f"[+] Wrote {len(attacks)} attacks to {out_attacks}")

# Show a sample attack
print("\n=== SAMPLE ATTACK (first entry) ===")
print(json.dumps(attacks[0], indent=2))

# ─── 3. Enumerate card types, energy types, etc. from the data ──────────────
print("\n=== CARD TYPE BREAKDOWN ===")
type_counts = {}
for c in cards:
    ct = c.get("cardType", c.get("type", "UNKNOWN"))
    type_counts[ct] = type_counts.get(ct, 0) + 1
for t, count in sorted(type_counts.items(), key=lambda x: -x[1]):
    print(f"  {t}: {count}")

print("\n=== ALL CARD KEYS (from first card) ===")
print(sorted(cards[0].keys()))

print("\n=== ALL ATTACK KEYS (from first attack) ===")
print(sorted(attacks[0].keys()))

# ─── 4. Extract unique energy types ─────────────────────────────────────────
energy_types = set()
for a in attacks:
    for e in a.get("cost", a.get("energyCost", [])):
        if isinstance(e, str):
            energy_types.add(e)
        elif isinstance(e, dict):
            energy_types.add(e.get("type", str(e)))
print("\n=== ENERGY TYPES (from attack costs) ===")
print(sorted(energy_types))

# ─── 5. Extract unique attack names ─────────────────────────────────────────
attack_names = sorted({a.get("name", "") for a in attacks if a.get("name")})
print(f"\n=== UNIQUE ATTACK NAMES ({len(attack_names)} total) ===")
for name in attack_names[:50]:
    print(f"  {name}")
if len(attack_names) > 50:
    print(f"  ... and {len(attack_names) - 50} more")

# ─── 6. Count Pokémon vs Trainer vs Energy cards ────────────────────────────
print("\n=== POKÉMON BREAKDOWN BY STAGE ===")
stage_counts = {}
for c in cards:
    stage = c.get("stage", c.get("evolutionStage", "Basic"))
    stage_counts[stage] = stage_counts.get(stage, 0) + 1
for s, count in sorted(stage_counts.items()):
    print(f"  {s}: {count}")

# ─── 7. Extract ability text if present ──────────────────────────────────────
abilities = []
for c in cards:
    if c.get("ability"):
        abilities.append({"pokemon": c.get("name", "?"), "ability": c["ability"]})
if abilities:
    print(f"\n=== ABILITIES ({len(abilities)} found) ===")
    out_abilities = os.path.join(os.path.dirname(__file__), "..", "data", "all_abilities.json")
    with open(out_abilities, "w") as f:
        json.dump(abilities, f, indent=2)
    print(f"  Wrote to {out_abilities}")
    print(f"  Sample: {json.dumps(abilities[0], indent=2)}")
else:
    print("\n=== ABILITIES: not a top-level field, check attack/effect text ===")

# ─── 8. Summary stats ───────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
print(f"  Total cards:    {len(cards)}")
print(f"  Total attacks:  {len(attacks)}")
print(f"  Energy types:   {sorted(energy_types)}")
print(f"  Card types:     {sorted(type_counts.keys())}")
print(f"  Unique attacks: {len(attack_names)}")
print("=" * 60)
