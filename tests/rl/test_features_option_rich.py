import numpy as np

from pokemon.rl import features


def test_option_dim_grew_with_card_and_attack_feats():
    assert features.OPTION_DIM == (
        49 + features.TARGET_BLOCK_DIM + features.CARD_FEAT_DIM + features.ATTACK_FEAT_DIM
    )


def test_attack_option_encodes_damage(main_obs):
    opt = {"type": 13, "attackId": 45}  # Blaze Blitz (260)
    vec = features.encode_option(opt, main_obs)
    assert vec.shape == (features.OPTION_DIM,)
    assert np.all(np.isfinite(vec))
    assert vec[-features.ATTACK_FEAT_DIM] == 1.0  # attack-block "known" flag


def test_play_option_encodes_card(main_obs):
    opt = {"type": 7, "index": 0}  # PLAY hand card 0 (id 2)
    vec = features.encode_option(opt, main_obs)
    card_block_start = features.OPTION_DIM - features.ATTACK_FEAT_DIM - features.CARD_FEAT_DIM
    assert vec[card_block_start] == 1.0  # card-block "known" flag
