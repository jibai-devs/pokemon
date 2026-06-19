import jax
import numpy as np

from pokemon.rl import checkpoint, features, net


def test_checkpoint_roundtrip(tmp_path):
    model = net.QNet(hidden=(32,))
    params = net.init_params(model, jax.random.PRNGKey(0), features.STATE_DIM, features.OPTION_DIM)
    path = tmp_path / "params.msgpack"
    checkpoint.save_params(str(path), params)

    template = net.init_params(model, jax.random.PRNGKey(1), features.STATE_DIM, features.OPTION_DIM)
    loaded = checkpoint.load_params(template, str(path))

    a = jax.tree_util.tree_leaves(params)
    b = jax.tree_util.tree_leaves(loaded)
    assert len(a) == len(b)
    assert all(np.allclose(np.asarray(x), np.asarray(y)) for x, y in zip(a, b))
