from __future__ import annotations
from typing import Literal
from vispy.visuals.filters import WireframeFilter, Alpha, ShadingFilter
import numpy as np
from vispy.visuals import MeshVisual
from vispy.scene.visuals import create_visual_node
from skimage.measure import marching_cubes


class MaskMeshVisual(MeshVisual):
    def __init__(
        self,
        data=None,
        level=None,
        **kwargs,
    ):
        kwargs["color"] = [1, 0.5, 0.5, 1]
        self._data = None
        self._level = level
        self._step_size = 1
        self._vertices_cache = None
        self._faces_cache = None
        self._recompute = True
        self._update_meshvisual = True
        self._shading_filter = ShadingFilter(shading="smooth", shininess=100)
        self._wireframe = WireframeFilter(
            color=[0.2, 0.82, 0.4, 1], wireframe_only=True
        )
        self._alpha_filter = Alpha(0.4)

        MeshVisual.__init__(self, **kwargs)

        if data is not None:
            self.set_data(data)
        self.attach(self._wireframe)
        self.attach(self._alpha_filter)
        self.set_gl_state(preset="additive")

    @property
    def level(self):
        """The threshold at which the isosurface is constructed from the 3D data."""
        return self._level

    @level.setter
    def level(self, level):
        self._level = level
        self._recompute = True
        self.update()

    @property
    def step_size(self):
        """The step size for the marching cubes algorithm."""
        return self._step_size

    @step_size.setter
    def step_size(self, step):
        self._step_size = step
        self._recompute = True
        self.update()

    def set_mode(self, mode: Literal["surface", "wireframe"]):
        """Set the rendering mode of the mesh."""
        mode = mode.lower()
        match mode:
            case "surface":
                self._wireframe.enabled = False
                self._shading_filter.enabled = True
                self._alpha_filter.alpha = 0.4
            case "wireframe":
                self._wireframe.enabled = True
                self._shading_filter.enabled = False
                self._alpha_filter.alpha = 0.6
            case _:
                raise ValueError(f"Invalid mode: {mode}")
        self.update()

    def set_data(
        self,
        data: np.ndarray | None = None,
        level: float | None = None,
        step: int | None = None,
    ):
        # We only change the internal variables if they are provided
        if data is not None:
            self._data = data
            self._recompute = True
        if level is not None:
            self._level = level
            self._recompute = True
        if step is not None:
            self._step_size = step
            self._recompute = True
        self.update()

    def _prepare_draw(self, view):
        if self._data is None or self._level is None:
            return False

        if self._recompute:
            self._vertices_cache, self._faces_cache, *_ = marching_cubes(
                self._data,
                self._level,
                step_size=self._step_size,
            )
            self._recompute = False
            self._update_meshvisual = True

        if self._update_meshvisual:
            MeshVisual.set_data(
                self,
                vertices=self._vertices_cache[:, ::-1],
                faces=self._faces_cache,
            )
            self._update_meshvisual = False
            self.attach(self._shading_filter)

        return MeshVisual._prepare_draw(self, view)


MaskMesh = create_visual_node(MaskMeshVisual)
