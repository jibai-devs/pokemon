"""Parse a CABT episode replay JSON and print each decision step in human-readable form.

Two replay formats are supported:

  Kaggle format (ver=2) — downloaded via `kaggle competitions replay <id>`:
    - String enums: opt.type='Play'/'Attack'/'End'/..., select.type='Main'/'Card'/'YesNo'
    - `selected` field holds the chosen indices (training label)
    - Both players' hands are fully visible (post-game record)
    - Card objects carry inline `name` field
    - `current` board state is at the top level of each vis frame

  Local format (ver=1) — produced by env.run() via --local:
    - Integer enums: opt.type=7/8/13/14/...
    - `action` field holds [p0_action, p1_action]; active player from current.yourIndex
    - Opponent hand is hidden (live observation)
    - Board state is inside obs["current"]

Usage:
    # Parse a downloaded Kaggle replay (pure Python, run in PowerShell or WSL)
    uv run python scripts/parse_replay.py episode-12345-replay.json

    # Limit output to first N steps
    uv run python scripts/parse_replay.py episode-12345-replay.json --max-steps 10

    # Dump full obs JSON for a specific step (debug featurization)
    uv run python scripts/parse_replay.py episode-12345-replay.json --dump-step 5

    # Run a local game and parse it (requires WSL — spins up libcg.so)
    uv run python scripts/parse_replay.py --local
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pokemon.catalog import atk_name as _catalog_atk_name
from pokemon.catalog import card_name as _catalog_card_name


# ---------------------------------------------------------------------------
# Area codes (Kaggle replay format)
# ---------------------------------------------------------------------------

_AREA = {
    2: "hand",
    5: "bench",
    6: "prize",
}


def _resolve_card(area: int, index: int, player_idx: int, players: list, select: dict) -> str:
    """Try to resolve a Card option's name from the board state."""
    if not players or player_idx >= len(players):
        return f"area={area}[{index}]"

    p = players[player_idx]
    if area == 2:
        cards = p.get("hand") or []
    elif area == 5:
        cards = p.get("bench") or []
    elif area == 6:
        cards = [c for c in (p.get("prize") or []) if c]
    else:
        # area 1/3 = deck search results (stored in select.deck if present)
        deck_cards = select.get("deck") or []
        if deck_cards and index < len(deck_cards):
            c = deck_cards[index]
            return c.get("name") or _catalog_card_name(c.get("id", -1))
        return f"area={area}[{index}]"

    if index < len(cards) and cards[index]:
        c = cards[index]
        return c.get("name") or _catalog_card_name(c.get("id", -1))
    return f"{_AREA.get(area, f'area={area}')}[{index}]"


# ---------------------------------------------------------------------------
# Option formatting — Kaggle (string enums)
# ---------------------------------------------------------------------------

def _fmt_option_kaggle(opt: dict, select: dict, players: list, active_idx: int) -> str:
    t = opt.get("type", "?")
    ctx = select.get("context", "")

    if t == "Play":
        idx = opt.get("index", -1)
        name = _resolve_card(2, idx, active_idx, players, select)
        return f"PLAY {name}"

    if t == "Attach":
        return "ATTACH energy"

    if t == "Evolve":
        idx = opt.get("index", -1)
        name = _resolve_card(2, idx, active_idx, players, select)
        return f"EVOLVE {name}"

    if t == "Retreat":
        return "RETREAT"

    if t == "Attack":
        atk_id = opt.get("attackId", -1)
        a = _catalog_atk_name(atk_id)
        return f"ATTACK {a}"

    if t == "End":
        return "END TURN"

    if t == "Yes":
        return f"YES ({ctx})"

    if t == "No":
        return f"NO ({ctx})"

    if t == "Card":
        area = opt.get("area", -1)
        idx = opt.get("index", -1)
        pidx = opt.get("playerIndex", active_idx)
        name = _resolve_card(area, idx, pidx, players, select)
        label = _AREA.get(area, f"area={area}")
        return f"CARD[{ctx}] {name} (p{pidx} {label}[{idx}])"

    return f"?{t}"


# ---------------------------------------------------------------------------
# Option formatting — local (int enums)
# ---------------------------------------------------------------------------

def _fmt_option_local(opt: dict, hand: list) -> str:
    from pokemon.catalog import format_option
    return format_option(opt, hand)


# ---------------------------------------------------------------------------
# Board display helpers
# ---------------------------------------------------------------------------

def _card_line(card: dict) -> str:
    name = card.get("name") or _catalog_card_name(card.get("id", -1))
    hp = card.get("hp", "?")
    max_hp = card.get("maxHp", "?")
    nrg = len(card.get("energies") or [])
    return f"{name} HP={hp}/{max_hp} E={nrg}"


def _status_flags(player: dict) -> str:
    flags = [k for k in ("poisoned", "burned", "asleep", "paralyzed", "confused") if player.get(k)]
    return f" [{','.join(flags)}]" if flags else ""


def _player_line(player: dict, label: str, show_hand: bool = True) -> str:
    active = player.get("active") or []
    bench = player.get("bench") or []
    hand = player.get("hand")

    active_str = _card_line(active[0]) if active and active[0] else "—"
    bench_str = ", ".join(
        (c.get("name") or _catalog_card_name(c.get("id", -1))) for c in bench if c
    ) or "—"
    prizes_left = sum(1 for p in (player.get("prize") or []) if p is not None)
    status = _status_flags(player)

    if hand is not None and show_hand:
        hand_str = f"{len(hand)} [{', '.join((c.get('name') or _catalog_card_name(c.get('id', -1))) for c in hand)}]"
    else:
        hand_str = f"{player.get('handCount', '?')} (hidden)"

    return (
        f"  {label}: active={active_str}{status}\n"
        f"        bench=[{bench_str}]\n"
        f"        hand={hand_str} | deck={player.get('deckCount', '?')} | prizes_left={prizes_left}"
    )


# ---------------------------------------------------------------------------
# Sample extraction
# ---------------------------------------------------------------------------

def _detect_format(vis_frames: list) -> str:
    """Return 'kaggle' or 'local' based on vis frame structure."""
    if not vis_frames:
        return "local"
    v0 = vis_frames[0]
    # Kaggle format has 'ver' key and string-typed select options
    if "ver" in v0 or isinstance((v0.get("select") or {}).get("type"), str):
        return "kaggle"
    return "local"


def _extract_kaggle(vis_frames: list) -> list[dict]:
    samples = []
    for i, frame in enumerate(vis_frames):
        select = frame.get("select")
        selected = frame.get("selected")
        # Skip frames with no decision (deck submission, terminal)
        if not select or selected is None:
            continue
        current = frame.get("current") or {}
        active_idx = current.get("yourIndex", 0)
        n_opts = len(select.get("option") or [])

        # Validate: selected values must be valid option-list indices.
        # Some frames encode card serials or area-indices instead — these
        # cannot be used as training labels and are marked invalid.
        # Observed causes (~7% of frames in one replay):
        #   - Card/Switch, Card/SetupActivePokemon: selected = promoted card's serial
        #   - Card/ToHand (Night Stretcher): selected = retrieved card's serial
        #   - Card/AttachFrom: selected has one extra value beyond n_opts
        valid = bool(selected) and all(0 <= sel < n_opts for sel in selected)

        samples.append({
            "step_idx": i,
            "player": active_idx,
            "current": current,
            "select": select,
            "action": selected,
            "format": "kaggle",
            "valid": valid,
        })
    return samples


def _extract_local(vis_frames: list) -> list[dict]:
    samples = []
    for i, frame in enumerate(vis_frames):
        obs = frame.get("obs") or {}
        select = obs.get("select")
        if not select:
            continue
        raw_action = frame.get("action") or []
        current = obs.get("current") or {}
        active_idx = current.get("yourIndex", 0)
        chosen = raw_action[active_idx] if len(raw_action) > active_idx else []
        samples.append({
            "step_idx": i,
            "player": active_idx,
            "current": current,
            "select": select,
            "action": chosen,
            "format": "local",
        })
    return samples


def extract_samples(steps: list) -> tuple[list[dict], str]:
    """Extract (board_state, options, chosen) samples from env steps. Returns (samples, format)."""
    vis = None
    if steps and isinstance(steps[0], list):
        first = steps[0][0]
        vis = first.get("visualize") if isinstance(first, dict) else getattr(first, "visualize", None)

    if not vis:
        return [], "no-vis"

    fmt = _detect_format(vis)
    if fmt == "kaggle":
        return _extract_kaggle(vis), "kaggle"
    return _extract_local(vis), "local"


# ---------------------------------------------------------------------------
# Printing
# ---------------------------------------------------------------------------

def print_sample(sample: dict, dump_obs: bool = False) -> None:
    current = sample["current"]
    select = sample["select"]
    action = sample["action"] or []
    fmt = sample["format"]

    active_idx = current.get("yourIndex", 0)
    players = current.get("players") or []
    me = players[active_idx] if active_idx < len(players) else {}
    opp = players[1 - active_idx] if (1 - active_idx) < len(players) else {}

    flags = [k for k in ("supporterPlayed", "energyAttached", "retreated") if current.get(k)]
    flag_str = f" | {' '.join(flags)}" if flags else ""
    valid = sample.get("valid", True)
    invalid_str = " | !! INVALID selected (skipped in training) !!" if not valid else ""

    print(f"\n{'=' * 72}")
    print(
        f"Step {sample['step_idx']:4d} | Player {sample['player']} | "
        f"Turn {current.get('turn', '?'):3} | "
        f"type={select.get('type')} ctx={select.get('context')} max={select.get('maxCount')}"
        + flag_str + invalid_str
    )

    # In Kaggle format both hands are visible; in local format only active player's hand is shown
    print(_player_line(me, "ME ", show_hand=True))
    print(_player_line(opp, "OPP", show_hand=(fmt == "kaggle")))

    options = select.get("option") or []
    hand = me.get("hand") or []
    print(f"  Options ({len(options)}):")
    for i, opt in enumerate(options):
        marker = "»" if i in action else " "
        if fmt == "kaggle":
            label = _fmt_option_kaggle(opt, select, players, active_idx)
        else:
            label = _fmt_option_local(opt, hand)
        print(f"    {marker} [{i}] {label}")

    print(f"  Chose: {action}")

    if dump_obs:
        print("\n  --- select JSON ---")
        print(json.dumps(select, indent=4))
        print("  --- current JSON (truncated) ---")
        safe = {k: v for k, v in current.items() if k != "players"}
        print(json.dumps(safe, indent=4))


def print_summary(samples: list[dict], fmt: str, data: dict) -> None:
    rewards = data.get("rewards", [])
    agents = [a.get("Name", f"P{i}") for i, a in enumerate(data.get("info", {}).get("Agents", []))]
    result_str = "unknown"
    if len(rewards) == 2:
        if rewards[0] == 1:
            result_str = f"{agents[0] if agents else 'P0'} wins"
        elif rewards[1] == 1:
            result_str = f"{agents[1] if len(agents) > 1 else 'P1'} wins"
        elif rewards[0] == 0 and rewards[1] == 0:
            result_str = "Draw"

    type_counts: dict = {}
    for s in samples:
        key = f"{s['select'].get('type')}/{s['select'].get('context')}"
        type_counts[key] = type_counts.get(key, 0) + 1

    n_valid = sum(1 for s in samples if s.get("valid", True))
    n_invalid = len(samples) - n_valid

    print(f"\n{'=' * 72}")
    print(f"Format: {fmt} | Steps: {len(samples)} | Valid (usable for training): {n_valid} | Invalid: {n_invalid} | Result: {result_str}")
    if agents:
        print(f"Agents: {agents[0]} vs {agents[1]}" if len(agents) > 1 else f"Agent: {agents[0]}")
    print("Select type/context breakdown:")
    for k, v in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"  {v:3d}x  {k}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def load_steps_from_file(path: Path) -> tuple[list, dict]:
    data = json.loads(path.read_text())
    if isinstance(data, dict):
        return data.get("steps", []), data
    return data, {}


def run_local_game() -> tuple[list, dict]:
    print("Running local game (random_agent vs first_agent)…")
    import kaggle_environments as kaggle
    from kaggle_environments.envs.cabt.cabt import first_agent, random_agent

    env = kaggle.make("cabt", debug=True)
    env.reset()
    env.run([random_agent, first_agent])
    return env.steps, {}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Parse a CABT replay and print decision steps.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("file", nargs="?", help="Path to replay JSON file")
    parser.add_argument("--local", action="store_true", help="Run a local game (requires WSL)")
    parser.add_argument("--max-steps", type=int, default=20, metavar="N")
    parser.add_argument("--dump-step", type=int, default=None, metavar="N",
                        help="Dump select+current JSON for this step index")
    args = parser.parse_args()

    if args.local or not args.file:
        steps, meta = run_local_game()
    else:
        steps, meta = load_steps_from_file(Path(args.file))

    samples, fmt = extract_samples(steps)
    print(f"Loaded {len(samples)} decision steps ({fmt} format)")

    shown = 0
    for sample in samples:
        if shown >= args.max_steps:
            break
        dump = args.dump_step is not None and sample["step_idx"] == args.dump_step
        print_sample(sample, dump_obs=dump)
        shown += 1

    if len(samples) > args.max_steps:
        print(f"\n… {len(samples) - args.max_steps} more steps not shown (--max-steps to increase)")

    print_summary(samples, fmt, meta)


if __name__ == "__main__":
    main()
