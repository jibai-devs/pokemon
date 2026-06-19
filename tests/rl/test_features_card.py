import numpy as np

from pokemon.rl import features


def test_card_features_known_vs_unknown():
    known = features.card_features(21)  # Scrafty: hp 120, cardType 0 (POKEMON)
    unknown = features.card_features(-1)
    assert len(known) == features.CARD_FEAT_DIM
    assert len(unknown) == features.CARD_FEAT_DIM
    assert known[0] == 1.0  # is_known
    assert unknown[0] == 0.0
    assert all(v == 0.0 for v in unknown)
    assert all(np.isfinite(known))
    assert 0.0 < known[8] <= 1.0  # hp slot normalized (index: 1 + 7 one-hot = 8)


def test_attack_features_known_has_damage_slot():
    feats = features.attack_features(1)  # Nab 'n' Dash: damage 0
    miss = features.attack_features(-1)
    assert len(feats) == features.ATTACK_FEAT_DIM
    assert feats[0] == 1.0 and miss[0] == 0.0
    assert all(np.isfinite(feats))
