import numpy as np
from numpy.typing import NDArray
from vispy.visuals import LineVisual
from vispy.scene.visuals import create_visual_node


class MotionPathVisual(LineVisual):
    """Visual for rendering motion paths as lines."""

    def __init__(
        self,
        color=(1.0, 0.23, 0.5, 1.0),
        width=3.0,
        **kwargs,
    ):
        LineVisual.__init__(
            self,
            color=color,
            width=width,
            method="gl",
            **kwargs,
        )

    def set_data(
        self,
        points: list[NDArray[np.float32]],
        color=None,
        width=None,
    ):
        """Set the motion path data.

        Parameters
        ----------
        points : list of (N, 3)
            The 3D points representing the motion paths.
        """
        data = np.concatenate(points, axis=0)
        to_connect_list = []
        offset = 0
        for arr in points:
            length = arr.shape[0]
            to_connect = np.stack(
                [
                    np.arange(offset, offset + length - 1, dtype=np.uint32),
                    np.arange(offset + 1, offset + length, dtype=np.uint32),
                ],
                axis=1,
            )
            to_connect_list.append(to_connect)
            offset += length
        connect = np.concatenate(to_connect_list, axis=0)
        super().set_data(pos=data, connect=connect, color=color, width=width)


MotionPath = create_visual_node(MotionPathVisual)
