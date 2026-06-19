"""Pure, deterministic encoders: observation dict -> fixed-length float32 vectors.

State and option dimensions are fixed module constants (asserted in tests). Rich
card/attack features (type, HP, attack damage from the catalog) are deferred to
M2; M0 uses a normalized-id + in-hand flag so the data path is exercised.
"""

from __future__ import annotations

import numpy as np

from pokemon import catalog
from pokemon.cabt_enums import AreaType, OptionType

BENCH_SLOTS = 5
N_SELECT_TYPE = 11  # SelectType 0..10
N_SELECT_CONTEXT = 49  # SelectContext 0..48
N_OPTION_TYPE = 17  # OptionType 0..16
N_AREA = 13  # AreaType 1..12, slot 0 = none

_CONDITIONS = ("poisoned", "burned", "asleep", "paralyzed", "confused")


def _onehot(idx, n: int) -> list[float]:
    v = [0.0] * n
    if idx is not None and 0 <= int(idx) < n:
        v[int(idx)] = 1.0
    return v


def _pokemon_vec(p: dict | None) -> list[float]:
    if not p:
        return [0.0, 0.0, 0.0]
    hp = p.get("hp", 0) or 0
    max_hp = p.get("maxHp", 0) or 0
    ratio = hp / max_hp if max_hp else 0.0
    n_energy = len(p.get("energies", []) or [])
    return [min(max(ratio, 0.0), 1.0), min(n_energy, 8) / 8.0, 1.0]


def _player_vec(pl: dict) -> list[float]:
    pl = pl or {}
    active = pl.get("active") or []
    vec = _pokemon_vec(active[0] if active else None)
    bench = pl.get("bench") or []
    for i in range(BENCH_SLOTS):
        vec += _pokemon_vec(bench[i] if i < len(bench) else None)
    vec += [
        min(pl.get("handCount", 0) or 0, 10) / 10.0,
        min(pl.get("deckCount", 0) or 0, 60) / 60.0,
        min(len(pl.get("discard") or []), 30) / 30.0,
        len(pl.get("prize") or []) / 6.0,
        min(len(bench), BENCH_SLOTS) / BENCH_SLOTS,
    ]
    vec += [1.0 if pl.get(k) else 0.0 for k in _CONDITIONS]
    return vec


_PLAYER_DIM = 3 + BENCH_SLOTS * 3 + 5 + len(_CONDITIONS)


def _meta_vec(obs: dict) -> list[float]:
    cur = obs.get("current") or {}
    sel = obs.get("select") or {}
    my = cur.get("yourIndex", 0)
    g = [
        min(cur.get("turn", 0) or 0, 50) / 50.0,
        1.0 if cur.get("supporterPlayed") else 0.0,
        1.0 if cur.get("stadiumPlayed") else 0.0,
        1.0 if cur.get("energyAttached") else 0.0,
        1.0 if cur.get("retreated") else 0.0,
        1.0 if cur.get("firstPlayer") == my else 0.0,
    ]
    g += _onehot(sel.get("type"), N_SELECT_TYPE)
    g += _onehot(sel.get("context"), N_SELECT_CONTEXT)
    g += [
        min(sel.get("minCount", 0) or 0, 5) / 5.0,
        min(sel.get("maxCount", 0) or 0, 5) / 5.0,
        min(sel.get("remainEnergyCost", 0) or 0, 5) / 5.0,
        min(sel.get("remainDamageCounter", 0) or 0, 20) / 20.0,
    ]
    return g


_META_DIM = 6 + N_SELECT_TYPE + N_SELECT_CONTEXT + 4
STATE_DIM = 2 * _PLAYER_DIM + _META_DIM


def encode_state(obs: dict) -> np.ndarray:
    cur = obs.get("current") or {}
    my = cur.get("yourIndex", 0)
    players = cur.get("players") or []
    me = players[my] if my < len(players) else {}
    opp = players[1 - my] if (1 - my) < len(players) else {}
    vec = _player_vec(me) + _player_vec(opp) + _meta_vec(obs)
    return np.asarray(vec, dtype=np.float32)


def _option_card_id(opt: dict, obs: dict) -> int:
    # PLAY options omit `area`; their index is implicitly into the hand.
    default_area = AreaType.HAND if opt.get("type") == OptionType.PLAY else None
    if opt.get("area", default_area) != AreaType.HAND:
        return -1
    cur = obs.get("current") or {}
    my = cur.get("yourIndex", 0)
    players = cur.get("players") or []
    me = players[my] if my < len(players) else {}
    hand = me.get("hand") or []
    idx = opt.get("index", -1)
    if 0 <= idx < len(hand):
        return hand[idx].get("id", -1)
    return -1


N_ENERGY_TYPE = 12  # EnergyType 0..11
N_CARD_TYPE = 7  # CardType 0..6
CARD_FEAT_DIM = 1 + N_CARD_TYPE + 1 + 1 + N_ENERGY_TYPE + 4  # known,type,hp,retreat,nrgtype,stages
ATTACK_FEAT_DIM = 1 + 1 + 1 + N_ENERGY_TYPE  # known,damage,cost-count,cost-type multi-hot


def card_features(card_id: int) -> list[float]:
    rec = catalog.card_record(card_id)
    if rec is None:
        return [0.0] * CARD_FEAT_DIM
    vec = [1.0]
    vec += _onehot(rec.get("cardType"), N_CARD_TYPE)
    vec += [min(rec.get("hp") or 0, 380) / 380.0]
    vec += [min(rec.get("retreatCost") or 0, 4) / 4.0]
    vec += _onehot(rec.get("energyType"), N_ENERGY_TYPE)
    vec += [
        1.0 if rec.get("basic") else 0.0,
        1.0 if rec.get("stage1") else 0.0,
        1.0 if rec.get("stage2") else 0.0,
        1.0 if rec.get("ex") else 0.0,
    ]
    return vec


def attack_features(attack_id: int) -> list[float]:
    rec = catalog.attack_record(attack_id)
    if rec is None:
        return [0.0] * ATTACK_FEAT_DIM
    energies = rec.get("energies") or []
    vec = [1.0, min(rec.get("damage") or 0, 350) / 350.0, min(len(energies), 5) / 5.0]
    types = [0.0] * N_ENERGY_TYPE
    for e in energies:
        if isinstance(e, int) and 0 <= e < N_ENERGY_TYPE:
            types[e] = 1.0
    vec += types
    return vec


def encode_option(opt: dict, obs: dict) -> np.ndarray:
    vec = _onehot(opt.get("type"), N_OPTION_TYPE)
    vec += _onehot(opt.get("area"), N_AREA)
    vec += _onehot(opt.get("inPlayArea"), N_AREA)
    vec += [
        min(opt.get("number", 0) or 0, 10) / 10.0,
        min(opt.get("count", 0) or 0, 4) / 4.0,
        1.0 if "attackId" in opt else 0.0,
        1.0 if "cardId" in opt else 0.0,
    ]
    card_id = _option_card_id(opt, obs)
    vec += [1.0 if card_id >= 0 else 0.0, (card_id % 2000) / 2000.0 if card_id >= 0 else 0.0]
    # Semantic blocks (M2): what the referenced card / attack actually does.
    vec += card_features(card_id)
    vec += attack_features(opt.get("attackId", -1) if "attackId" in opt else -1)
    return np.asarray(vec, dtype=np.float32)


OPTION_DIM = N_OPTION_TYPE + 2 * N_AREA + 4 + 2 + CARD_FEAT_DIM + ATTACK_FEAT_DIM


def encode_decision(obs: dict) -> tuple[np.ndarray, np.ndarray, int]:
    opts = obs["select"]["option"]
    state = encode_state(obs)
    options = np.stack([encode_option(o, obs) for o in opts]).astype(np.float32)
    return state, options, len(opts)
