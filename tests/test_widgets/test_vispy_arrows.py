import numpy as np
from pytestqt.qtbot import QtBot
from himena_relion._impl_objects import TubeObject
from himena_relion._widgets import Q3DViewer


def _tubes(n: int) -> list[TubeObject]:
    rng = np.random.default_rng(0)
    return [
        TubeObject(
            start=rng.uniform(0, 10, 3),
            end=rng.uniform(0, 10, 3),
            radius=1.0,
            color=(0.2, 0.0, 0.8),
        )
        for _ in range(n)
    ]


def test_arrows_hidden_while_empty(qtbot: QtBot):
    # vispy fails to draw an arrow visual without data, which made the whole canvas
    # invisible when the angle distribution was shown for a map without arrows.
    viewer = Q3DViewer()
    qtbot.addWidget(viewer)
    canvas = viewer._canvas
    viewer.set_image(np.ones((6, 6, 6), dtype=np.float32))

    viewer.set_arrows_visible(True)
    assert canvas.arrows_visible
    assert not canvas.arrow_visual.visible  # no data yet

    viewer.set_arrows(_tubes(3))
    assert canvas.arrow_visual.visible
    assert canvas.arrow_visual._pos.shape == (6, 3)
    assert canvas.arrow_visual.arrows.shape == (3, 6)

    viewer.set_arrows([])
    assert canvas.arrows_visible
    assert not canvas.arrow_visual.visible

    viewer.set_arrows(_tubes(1))
    assert canvas.arrow_visual.visible

    viewer.set_arrows_visible(False)
    assert not canvas.arrow_visual.visible
    viewer.set_arrows(_tubes(2))
    assert not canvas.arrow_visual.visible
    viewer.set_arrows_visible(True)
    assert canvas.arrow_visual.visible
