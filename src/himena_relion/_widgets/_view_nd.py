from __future__ import annotations
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Literal, NamedTuple
from himena import StandardType, WidgetDataModel
import numpy as np
from numpy.typing import NDArray
from qtpy import QtWidgets as QtW, QtCore
from superqt import ensure_main_thread
from vispy.color import ColorArray
from scipy.spatial.transform import Rotation
from himena.qt._qlineedit import QIntLineEdit, QDoubleLineEdit
from himena.plugins import validate_protocol
from himena_builtins.qt.widgets._shared import labeled
from himena_builtins.qt.widgets._image_components import (
    QHistogramView,
    QAutoContrastButton,
)

from himena_relion._image_readers import ArrayFilteredView
from himena_relion._widgets._spinbox import QIntWidget
from himena_relion._widgets._vispy import Vispy2DViewer, Vispy3DViewer, IsoSurface
from himena_relion import _utils


class SliceResult(NamedTuple):
    image: NDArray[np.float32]
    clim: tuple[float, float]
    points: NDArray[np.float32]
    sizes: NDArray[np.float32]
    face_colors: NDArray[np.float32]
    edge_colors: NDArray[np.float32]


class QViewer(QtW.QWidget):
    _always_force_sync: bool = False


class Q2DViewer(QViewer):
    _executor = ThreadPoolExecutor(max_workers=2)

    def __init__(self, zlabel: str = "z", parent=None):
        super().__init__(parent)
        self._last_future: Future[SliceResult] | None = None
        self._last_clim: tuple[float, float] | None = None
        self._canvas = Vispy2DViewer(self)
        self._canvas.native.setMinimumSize(200, 200)
        self._canvas._scene.bgcolor = "#242424"
        self._canvas._viewbox.border_color = "#4A4A4A"
        layout = QtW.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._canvas.native)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)
        self._array_view = None
        self._points = np.empty((0, 3), dtype=np.float32)
        self._point_size = 12.0
        self._face_colors = np.zeros((0, 4), dtype=np.float32)
        self._edge_colors = np.zeros((0, 4), dtype=np.float32)
        self._dims_slider = QtW.QSlider(QtCore.Qt.Orientation.Horizontal, self)
        self._dims_slider.setMaximum(0)
        self._dims_slider.setMinimumWidth(150)
        self._histogram_view = QHistogramView()
        self._histogram_view.clim_changed.connect(self._on_clim_changed)
        self._histogram_view.setFixedHeight(32)
        self._histogram_view.setValueFormat(".2f", always_show=True)
        self._auto_contrast_btn = QAutoContrastButton(self._auto_contrast)
        self._auto_contrast_btn.qminmax = (0.0001, 0.9999)
        self._zpos_box = QIntWidget("", label_width=0)
        self._zpos_box.valueChanged.connect(self._on_zpos_box_changed)
        self._zpos_box.setFixedWidth(90)
        self._zpos_box.setMaximum(0)
        self._auto_contrast_btn.update_color("gray")
        self._dims_slider_widget = labeled(zlabel, self._dims_slider, self._zpos_box)
        layout.addWidget(self._dims_slider_widget)
        hlayout = QtW.QHBoxLayout()
        hlayout.addWidget(self._auto_contrast_btn)
        hlayout.addWidget(self._histogram_view)
        hlayout.setContentsMargins(8, 0, 8, 0)
        layout.addLayout(hlayout)
        self._dims_slider.valueChanged.connect(self._on_slider_changed)
        self._out_of_slice = True

    def clear(self):
        self._array_view = None
        self._points = np.empty((0, 3), dtype=np.float32)
        self.redraw()

    @property
    def has_image(self) -> bool:
        return self._array_view is not None

    def set_array_view(
        self,
        image: np.ndarray | ArrayFilteredView,
        clim: tuple[float, float] | None = None,
    ):
        """Set the 3D image to be displayed."""
        had_image = self.has_image
        if isinstance(image, np.ndarray):
            self._array_view = ArrayFilteredView.from_array(image)
        elif isinstance(image, ArrayFilteredView):
            self._array_view = image
        else:
            raise TypeError("image must be a numpy array or ArrayFilteredView.")
        self._last_clim = clim
        num_slices = self._array_view.num_slices()
        self._dims_slider.blockSignals(True)
        self._dims_slider_widget.setVisible(bool(num_slices > 1))
        try:
            self._dims_slider.setRange(0, num_slices - 1)
            self._dims_slider.setValue(num_slices // 2)
            self._zpos_box.setRange(0, num_slices - 1)
            self.redraw()
        finally:
            self._dims_slider.blockSignals(False)
        if not had_image:
            self._auto_contrast(force_update_view_range=True)
            self.auto_fit()
            m0, m1 = self._histogram_view._minmax
            fmt = _format_for_minmax(m0, m1)
            self._histogram_view.setValueFormat(fmt, always_show=True)

    def set_points(
        self,
        points: np.ndarray,
        out_of_slice: bool = True,
        size: float | None = None,
        face_color: NDArray[np.float32] = [0, 0, 0, 0],
        edge_color: NDArray[np.float32] = "lime",
    ):
        """Set the 3D points to be displayed."""
        self._points = points
        self._out_of_slice = out_of_slice
        self._face_colors = _norm_color(face_color, len(points))
        self._edge_colors = _norm_color(edge_color, len(points))
        if size is not None:
            self._point_size = size

    def redraw(self):
        self._on_slider_changed(self._dims_slider.value(), force_sync=True)

    def _on_zpos_box_changed(self, value: int):
        """Update the slider when the z position box changes."""
        self._zpos_box.blockSignals(True)
        try:
            self._dims_slider.setValue(value)
        finally:
            self._zpos_box.blockSignals(False)

    def _on_slider_changed(self, value: int, *, force_sync: bool = False):
        """Update the displayed slice based on the slider value."""
        self._zpos_box.setValue(value)
        if self._last_future:
            self._last_future.cancel()  # cancel last task
        if self._array_view is not None:
            if force_sync or self._always_force_sync:
                val = self._get_image_slice(value)
                future = Future()
                future.set_result(val)
                self._on_calc_slice_done(future)
            else:
                self._last_future = self._executor.submit(self._get_image_slice, value)
                self._last_future.add_done_callback(self._on_calc_slice_done)
        else:
            self._canvas.image = np.zeros((0, 0), dtype=np.float32)
            self._histogram_view.set_hist_for_array(
                np.zeros((2, 2), dtype=np.float32), (0.0, 1.0)
            )

    def _get_image_slice(self, slider_value: int) -> SliceResult:
        slice_image = np.asarray(self._array_view.get_slice(slider_value))
        if self._last_clim is None:
            min_ = slice_image.min()
            max_ = slice_image.max()
            self._last_clim = (min_, max_)
        else:
            min_, max_ = self._last_clim
        zs = self._points[:, 0]
        thickness = self._point_size_normed() if self._out_of_slice else 0.01
        zdiff = zs - slider_value
        mask = np.abs(zdiff) < thickness / 2
        sizes = np.sqrt((thickness) ** 2 - (zdiff[mask] * 2) ** 2)
        return SliceResult(
            slice_image,
            (min_, max_),
            points=self._points[mask],
            sizes=sizes,
            face_colors=self._face_colors[mask],
            edge_colors=self._edge_colors[mask],
        )

    @ensure_main_thread
    def _on_calc_slice_done(self, future: Future[SliceResult]):
        self._last_future = None
        if future.cancelled():
            return
        result = future.result()
        self._histogram_view.set_hist_for_array(result.image, result.clim)
        self._canvas.image = result.image
        self._canvas.contrast_limits = result.clim
        self._last_clim = result.clim
        if result.points.shape[0] > 0:
            self._canvas.markers_visual.set_data(
                result.points[:, [2, 1]],
                face_color=result.face_colors,
                edge_color=result.edge_colors,
                edge_width_rel=0.1 * self.devicePixelRatioF(),
                size=result.sizes,
            )
            self._canvas.markers_visual.visible = True
        else:
            self._canvas.markers_visual.set_data(
                np.ones((1, 2), dtype=np.float32),
                face_color=np.zeros(4),
                edge_color=np.zeros(4),
                size=self._point_size_normed(),
            )
            self._canvas.markers_visual.visible = False
        self._canvas.update_canvas()

    def _point_size_normed(self) -> float:
        # vispy point size is not scaled by device pixel ratio.
        return self._point_size / self.devicePixelRatioF()

    def _auto_contrast(self, *, force_update_view_range: bool = False):
        """Automatically adjust the contrast based on the histogram."""
        range_min, range_max = self._histogram_view._view_range
        minmax = self._histogram_view.calc_contrast_limits(
            *self._auto_contrast_btn.qminmax
        )
        if minmax is None:
            return
        min_new, max_new = minmax

        min_old, max_old = self._histogram_view.clim()
        self._histogram_view.set_clim((min_new, max_new))

        # ensure both end is visible
        changed = False
        if min_new < min_old:
            range_min = min_new
            changed = True
        if max_new > max_old:
            range_max = max_new
            changed = True
        if changed or force_update_view_range:
            self._histogram_view.set_view_range(range_min, range_max)

    def _on_clim_changed(self, clim: tuple[float, float]):
        """Update the contrast limits based on the histogram view."""
        self._canvas.contrast_limits = clim
        self._last_clim = clim
        self._canvas.update_canvas()

    def auto_fit(self):
        """Automatically fit the camera to the image."""
        self._canvas.auto_fit()
        self._canvas.update_canvas()


class Q3DViewerBase(QViewer):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._canvas = Vispy3DViewer(self)
        self._canvas._scene.bgcolor = "#242424"
        self._canvas._viewbox.border_color = "#4A4A4A"
        self._canvas.native.setMaximumSize(400, 400)
        self._canvas.native.setMinimumSize(300, 300)
        self.setSizePolicy(
            QtW.QSizePolicy.Policy.Expanding,
            QtW.QSizePolicy.Policy.Expanding,
        )


class Q3DViewer(Q3DViewerBase):
    __himena_widget_id__ = "himena-relion:Q3DViewer"
    __himena_display_name__ = "3D volume viewer"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rendering = QtW.QComboBox()
        self._rendering.addItems(["Surface", "Maximum"])
        self._rendering.setCurrentIndex(0)
        self._rendering.currentTextChanged.connect(self.set_rendering_mode)
        self._hist_view = QHistogramView(mode="thresh")
        self._hist_view.set_hist_scale("log")
        self._hist_view.setFixedHeight(32)
        self._hist_view.setValueFormat(".2f", always_show=True)
        self._hist_view.threshold_changed.connect(self._on_iso_changed)
        self._hist_view.clim_changed.connect(self._on_clim_changed)
        self._auto_thresh_btn = QtW.QPushButton("Auto")
        self._auto_thresh_btn.setFixedWidth(40)
        self._auto_thresh_btn.clicked.connect(lambda: self.auto_threshold())
        self._auto_thresh_btn.setToolTip("Automatically set the iso-surface threshold")
        self._has_image = False
        _thresh = QtW.QWidget()
        _thresh_layout = QtW.QHBoxLayout(_thresh)
        _thresh_layout.setContentsMargins(0, 0, 0, 0)
        _thresh_layout.addWidget(self._rendering)
        _thresh_layout.addWidget(self._hist_view)
        _thresh_layout.addWidget(self._auto_thresh_btn)
        _thresh.setMaximumWidth(400)
        _thresh.setMinimumWidth(300)

        layout = QtW.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._canvas.native)
        layout.addWidget(_thresh)

    @property
    def has_image(self) -> bool:
        return self._has_image

    def set_image(self, image: np.ndarray | None, update_now: bool = True):
        """Set the 3D image to be displayed."""
        had_image = self.has_image
        if image is None:
            self._canvas.image = image = np.zeros((2, 2, 2))
            self._canvas.image_visual.visible = False
            self._has_image = False
        else:
            self._canvas.image = image
            self._canvas.image_visual.visible = True
            self._has_image = True
        view_min, view_max = self._canvas._lims
        if not had_image:
            self.auto_threshold(update_now=False)
            self.auto_fit(update_now=False)
            th_min, th_max = view_min, view_max
        else:
            th_min, th_max = image.min(), image.max()
            cur_th = self._hist_view.threshold()
            if cur_th < view_min or cur_th > view_max:
                self._hist_view.set_threshold((view_min + view_max) / 2)
        fmt = _format_for_minmax(th_min, th_max)
        self._hist_view.setValueFormat(fmt, always_show=True)

        if self._has_image:
            self._hist_view.set_view_range(view_min, view_max)

        self._hist_view.set_hist_for_array(image, (view_min, view_max))
        self._hist_view.set_minmax((th_min, th_max))

        self._canvas.set_iso_threshold(self._hist_view.threshold())
        if update_now:
            self._canvas.update_canvas()

    def set_rendering_mode(self, mode: Literal["Surface", "Maximum"]):
        """Set the rendering mode of the 3D viewer."""
        if mode not in ["Surface", "Maximum"]:
            raise ValueError("mode must be 'Surface' or 'Maximum'.")
        if self._rendering.currentText() != mode:
            self._rendering.setCurrentText(mode)
        self._canvas.set_rendering_mode(mode)
        self._hist_view.set_mode("thresh" if mode == "Surface" else "clim")
        self._canvas.update_canvas()

    def auto_threshold(self, thresh: float | None = None, update_now: bool = True):
        """Automatically set the threshold based on the image data."""
        img = self._canvas.image
        if self._canvas.image_visual.visible:
            if thresh is None:
                thresh = _utils.threshold_yen(_utils.bin_image(img, 4))
            self._hist_view.set_threshold(thresh)
            self._hist_view.set_minmax(self._canvas._lims)
        if update_now:
            self._canvas.update_canvas()

    def auto_fit(self, update_now: bool = True):
        """Automatically fit the camera to the image."""
        img = self._canvas.image
        self._canvas.camera.center = np.array(img.shape) / 2
        self._canvas.camera.scale_factor = max(img.shape)
        self._canvas.camera.update()
        if update_now:
            self._canvas.update_canvas()

    def _on_iso_changed(self, value: float):
        self._canvas.set_iso_threshold(value)
        self._canvas.update_canvas()

    def _on_clim_changed(self, clim: tuple[float, float]):
        self._canvas.contrast_limits = clim
        self._canvas.update_canvas()

    @validate_protocol
    def update_model(self, model: WidgetDataModel):
        arr = np.asarray(model.value, dtype=np.float32)
        if arr.ndim != 3:
            raise ValueError("Input array must be 3D.")
        self.set_image(arr, update_now=True)

    @validate_protocol
    def model_type(self) -> str:
        return StandardType.IMAGE

    @validate_protocol
    def to_model(self) -> WidgetDataModel:
        return WidgetDataModel(
            value=self._canvas.image,
            type=StandardType.IMAGE,
        )

    @validate_protocol
    def size_hint(self):
        return 330, 350


class Q3DLocalResViewer(Q3DViewerBase):
    """A 3D viewer for displaying local resolution maps with iso-surface."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._iso_slider = QHistogramView(mode="thresh")
        self._iso_slider.setFixedHeight(32)
        self._iso_slider.threshold_changed.connect(self._on_iso_changed)
        self._iso_slider.set_hist_scale("log")
        self._auto_threshold_btn = QtW.QPushButton("Auto")
        self._auto_threshold_btn.setFixedWidth(40)
        self._auto_threshold_btn.clicked.connect(lambda: self.auto_threshold())
        self._clim_slider = QHistogramView(mode="clim")
        self._clim_slider.setFixedHeight(32)
        self._clim_slider.clim_changed.connect(self._on_clim_changed)

        self._surface = IsoSurface(parent=self._canvas._viewbox.scene)
        _thresh = labeled("Threshold", self._iso_slider, self._auto_threshold_btn)
        _thresh.setMaximumWidth(400)
        _thresh.setMinimumWidth(300)
        clim_slider = labeled("Resolution (A)", self._clim_slider)
        clim_slider.setMaximumWidth(400)
        clim_slider.setMinimumWidth(300)
        self._shading = QtW.QComboBox()
        self._shading.setSizePolicy(
            QtW.QSizePolicy.Policy.Expanding,
            QtW.QSizePolicy.Policy.Fixed,
        )
        self._shading.addItems(["none", "flat", "smooth"])
        self._shading.setCurrentText("smooth")
        self._shading.currentTextChanged.connect(self._on_shading_changed)

        shading_widget = labeled("Shading", self._shading)
        shading_widget.setMinimumWidth(300)
        shading_widget.setMaximumWidth(400)

        layout = QtW.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._canvas.native)
        layout.addWidget(_thresh)
        layout.addWidget(clim_slider)
        layout.addWidget(shading_widget)

        self._iso_slider.setValueFormat(".2f", always_show=True)

        # mesh lighting
        self._canvas.camera.changed.connect(self._on_camera_change)

    def _on_camera_change(self):
        quat = self._canvas._camera.quaternion
        x, y, z, w = quat.x, quat.y, quat.z, quat.w
        # Calculate forward vector from quaternion
        rot = Rotation.from_quat([x, y, z, w])
        vec = rot.apply([1, 0, 0])
        if self._surface.shading_filter is not None:
            self._surface.shading_filter.light_dir = vec

    def auto_threshold(self, thresh: float | None = None, update_now: bool = True):
        """Automatically set the threshold based on the image data."""
        img = self._surface._data
        mask = self._surface._mask
        if self._surface.visible:
            if thresh is None:
                if mask is not None:
                    sample_data = img[mask]
                else:
                    sample_data = img
                thresh = _utils.threshold_yen(sample_data)
            self._iso_slider.set_threshold(thresh)
            self._iso_slider.set_minmax(self._canvas._lims)
        if update_now:
            self._canvas.update_canvas()

    def auto_fit(self, update_now: bool = True):
        """Automatically fit the camera to the image."""
        img = self._surface._data
        self._canvas.camera.center = np.array(img.shape) / 2
        self._canvas.camera.scale_factor = max(img.shape)
        self._canvas.camera.update()
        if update_now:
            self._canvas.update_canvas()

    def set_images(
        self,
        image: NDArray[np.float32],
        locres: NDArray[np.float32],
        mask: NDArray[np.bool_] | None = None,
        *,
        update_now: bool = True,
    ):
        if mask is None:
            mask_sl = slice(None)
        else:
            mask_sl = mask
        image_masked = image[mask_sl]
        im_min0, im_max0 = np.min(image_masked), np.max(image_masked)
        self._iso_slider.set_minmax((im_min0, im_max0))
        self._iso_slider.set_threshold((im_min0 + im_max0) / 2)
        fmt = _format_for_minmax(im_min0, im_max0)
        self._iso_slider.setValueFormat(fmt, always_show=True)

        locres_masked = locres[mask_sl]
        locres_masked = locres_masked[locres_masked > 0.001]
        self._surface.set_data(image, mask, clim=None, color_array=locres)
        self._surface.init_surface()
        self._clim_slider.blockSignals(True)
        try:
            self._clim_slider.set_clim(self._surface.clim)
        finally:
            self._clim_slider.blockSignals(False)
        self._on_shading_changed(self._shading.currentText())
        self._iso_slider.set_hist_for_array(image, (im_min0, im_max0))
        self._iso_slider.set_view_range(im_min0, im_max0)

        min0, max0 = np.min(locres_masked), np.max(locres_masked)
        self._clim_slider.set_minmax((min0, max0))
        self._clim_slider.set_hist_for_array(locres, (min0, max0))
        self._clim_slider.set_view_range(min0, max0)
        self._clim_slider.setValueFormat(".2f", always_show=True)

        if update_now:
            self._canvas.update_canvas()

    def _on_iso_changed(self, value: float):
        self._surface.level = value
        self._canvas.update_canvas()

    def _on_clim_changed(self, clim: tuple[float, float]):
        self._surface.clim = clim
        self._canvas.update_canvas()

    def _on_shading_changed(self, shading: str):
        if shading == "none":
            shading = None
        self._surface.shading = shading
        self._surface.update()
        self._canvas.update_canvas()


class Q2DFilterWidget(QtW.QWidget):
    value_changed = QtCore.Signal()

    def __init__(self, parent=None, bin_default: int = 4, lowpass_default: float = 10):
        super().__init__(parent)
        layout = QtW.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        self._bin_factor = QIntLineEdit(str(bin_default))
        self._bin_factor.setFixedWidth(60)
        self._bin_factor.setMinimum(1)
        self._bin_factor.setMaximum(20)
        self._lowpass_cutoff = QDoubleLineEdit(str(lowpass_default))
        self._lowpass_cutoff.setMinimum(0.0)
        self._lowpass_cutoff.setMaximum(200.0)
        self._lowpass_cutoff.setFixedWidth(80)
        layout.addWidget(labeled("Binning factor:", self._bin_factor))
        layout.addWidget(labeled("Lowpass cutoff (Å):", self._lowpass_cutoff))
        self._image_scale = 1.0
        self._bin_factor.textChanged.connect(self.value_changed)
        self._lowpass_cutoff.textChanged.connect(self.value_changed)

    def set_image_scale(self, scale: float):
        """Set the image scale in Å/pixel."""
        self._image_scale = scale

    def bin_factor(self) -> int:
        """Get the binning factor from the input."""
        return int(self._bin_factor.text())

    def lowpass_cutoff(self) -> float:
        """Get the lowpass cutoff frequency from the input."""
        return float(self._lowpass_cutoff.text())

    def apply(self, img: np.ndarray, index=None) -> np.ndarray:
        """Apply the binning and lowpass filter to the input image."""
        # Binning
        factor = self.bin_factor()
        cutoff = self.lowpass_cutoff()
        if factor > 1:
            img = _utils.bin_image(img, factor)
        if cutoff > 0.0:
            cutoff_rel = self._image_scale / cutoff * factor
            img = _utils.lowpass_filter(img, cutoff_rel)

        return img

    def set_params(self, bin_factor: int, lowpass_cutoff: float):
        """Set the binning factor and lowpass cutoff frequency."""
        self._bin_factor.setText(str(bin_factor))
        self._lowpass_cutoff.setText(str(lowpass_cutoff))


def _norm_color(color, num: int) -> NDArray[np.float32]:
    """Normalize color input to an array of RGBA colors."""
    carr = ColorArray(color)
    if len(carr) == 1:
        carr = np.tile(carr.rgba, (num, 1))
    else:
        if len(carr) != num:
            raise ValueError("Color array length does not match number of points.")
        carr = carr.rgba
    return carr.astype(np.float32, copy=False)


def _format_for_minmax(m0, m1):
    prec = np.log10(m1 - m0 + 1e-8)
    n_decimals = max(0, -int(np.floor(prec)) + 3)
    return f".{n_decimals}f"
