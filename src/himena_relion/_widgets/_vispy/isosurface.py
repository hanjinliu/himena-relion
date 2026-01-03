import numpy as np
from vispy.visuals import MeshVisual
from vispy.scene.visuals import create_visual_node
from vispy.color import Color, Colormap
from scipy import ndimage as ndi
from skimage.measure import marching_cubes


class IsosurfaceVisual(MeshVisual):
    """Mesh visual for rendering a isosurface colored by another scalar field."""

    def __init__(
        self,
        data=None,
        mask=None,
        level=None,
        clim: tuple[float, float] = (0.0, 1.0),
        vertex_colors=None,
        face_colors=None,
        color=(0.5, 0.5, 1, 1),
        **kwargs,
    ):
        self._data = None
        self._mask = None
        self._level = level
        self._vertex_colors = vertex_colors
        self._color_array = face_colors
        self._color = Color(color)
        self._vertices_cache = None
        self._faces_cache = None
        self._face_colors_cache = None
        self._recompute = True
        self._recolor = True
        self._update_meshvisual = True
        self._colormap = Colormap(["blue", "white", "red"])
        self._clim = clim

        MeshVisual.__init__(self, **kwargs)
        if data is not None:
            self.set_data(data, mask, color_array=face_colors, clim=clim)

    @property
    def level(self):
        """The threshold at which the isosurface is constructed from the 3D data."""
        return self._level

    @level.setter
    def level(self, level):
        self._level = level
        self._recompute = True
        self._recolor = True
        self.update()

    @property
    def clim(self) -> tuple[float, float]:
        return self._clim

    @clim.setter
    def clim(self, clim: tuple[float, float]):
        self._clim = clim
        self._recolor = True
        self.update()

    def set_data(
        self,
        data: np.ndarray | None = None,
        mask: np.ndarray | None = None,
        clim: tuple[float, float] | None = None,
        color_array: np.ndarray | None = None,
    ):
        """Set the scalar array data

        Parameters
        ----------
        data : ndarray
            A 3D array of scalar values. The isosurface is constructed to show
            all locations in the scalar field equal to ``self.level``.
        face_colors : array-like | None
            A 3D array from which the face color will be sampled.
        """
        # We only change the internal variables if they are provided
        if data is not None:
            self._data = data
            self._recompute = True
            self._recolor = True
        if clim is not None:
            self._clim = clim
            self._recolor = True
            self._update_meshvisual = True
        if color_array is not None:
            self._color_array = color_array
            self._recolor = True
            self._update_meshvisual = True
        self._mask = mask
        self.update()

    def _prepare_draw(self, view):
        if self._data is None or self._level is None:
            return False

        if self._recompute:
            self._vertices_cache, self._faces_cache, *_ = marching_cubes(
                self._data,
                self._level,
                mask=self._mask,
            )
            self._recompute = False
            self._update_meshvisual = True
        if self._recolor:
            face_centers = self._vertices_cache[self._faces_cache].mean(axis=1)
            values_face = _map_coordinates(self._color_array, face_centers)
            values_vert = _map_coordinates(self._color_array, self._vertices_cache)
            self._face_colors_cache = self._map_colors(values_face)
            self._vertex_colors = self._map_colors(values_vert)
            self._recolor = False
            self._update_meshvisual = True

        if self._update_meshvisual:
            MeshVisual.set_data(
                self,
                vertices=self._vertices_cache,
                faces=self._faces_cache,
                vertex_colors=self._vertex_colors,
                face_colors=self._face_colors_cache,
                color=self._color,
            )
            self._update_meshvisual = False

        return MeshVisual._prepare_draw(self, view)

    def _map_colors(self, values: np.ndarray) -> np.ndarray:
        """Map scalar values to colors using the colormap and clim."""
        normed = _norm_values(values, self._clim)
        colors = self._colormap.map(normed)
        return colors


def _norm_values(values, clim: tuple[float, float]) -> np.ndarray:
    """Normalize values to the range [0, 1] based on clim."""
    cmin, cmax = clim
    normed = (values - cmin) / (cmax - cmin)
    normed = np.clip(normed, 0.0, 1.0)
    return normed


def _map_coordinates(arr: np.ndarray, verts: np.ndarray) -> np.ndarray:
    return ndi.map_coordinates(
        arr, verts[:, :, np.newaxis], order=1, mode="nearest", prefilter=False
    )


IsoSurface = create_visual_node(IsosurfaceVisual)
