import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pokemon.catalog import card_name

path, step = sys.argv[1], int(sys.argv[2])
data = json.loads(Path(path).read_text(encoding="utf-8"))
vis = data["steps"][0][0]["visualize"]

def dump_player(p, label):
    print(f"  {label}: yourIndex context")
    active = p.get("active") or []
    for c in active:
        print(f"    ACTIVE: {card_name(c.get('id'))} hp={c.get('remainingHp', c.get('hp'))}/{c.get('maxHp')} energy={[e.get('id') for e in (c.get('energyCards') or [])]}")
    for i, c in enumerate(p.get("bench") or []):
        print(f"    BENCH[{i}]: {card_name(c.get('id'))} hp={c.get('remainingHp', c.get('hp'))}/{c.get('maxHp')} energy={[e.get('id') for e in (c.get('energyCards') or [])]}")
    print(f"    HAND: {[card_name(c.get('id')) for c in (p.get('hand') or [])]}")

frame = vis[step]
sel = frame.get("select")
cur = frame.get("current") or {}
players = cur.get("players") or []
print(f"step {step} turn={cur.get('turn')} ctx={sel.get('context') if sel else None} yourIndex={cur.get('yourIndex')}")
for idx, p in enumerate(players):
    dump_player(p, f"player[{idx}]")
if sel:
    print("OPTIONS:")
    for i, opt in enumerate(sel.get("option") or []):
        print(f"  [{i}] {opt}")
print("selected on next frame:", vis[step+1].get("selected") if step+1 < len(vis) else None)
