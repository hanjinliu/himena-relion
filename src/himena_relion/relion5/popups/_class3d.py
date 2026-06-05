from __future__ import annotations

from qtpy import QtWidgets as QtW, QtCore
from enum import StrEnum
from cmap import Colormap
from starfile_rs import read_star
import numpy as np
import mrcfile
from superqt import QFlowLayout, QLabeledSlider
from himena.qt.magicgui import ToggleButtons
from himena_relion._job_dir import JobDirectory
from himena_relion._widgets import Q2DSimpleViewer
from himena_relion._widgets import QIntWidget


class ProjectionMode(StrEnum):
    MAX = "max"
    MEAN = "mean"
    SLICE = "slice"


class IntensityMode(StrEnum):
    ORIGINAL = "original"
    DIFF = "diff"


class Direction(StrEnum):
    XY = "xy"
    XZ = "xz"
    YZ = "yz"


class Class3DPopup(QtW.QWidget):
    def __init__(
        self,
        job_dir: JobDirectory,
    ):
        super().__init__()
        layout = QtW.QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignTop | QtCore.Qt.AlignmentFlag.AlignHCenter
        )

        if nr_classes := job_dir.get_job_param("nr_classes"):
            num_classes = int(nr_classes)
        else:
            raise ValueError("nr_classes parameter not found in job directory")

        # load latest iterations
        niter_choices: list[int] = []
        for star_path in job_dir.path.glob("run_it*_model.star"):
            niter = int(star_path.stem.split("_")[1][2:])
            if niter > 0:
                niter_choices.append(niter)
        if len(niter_choices) == 0:
            raise ValueError("No iteration found.")

        self._viewers = [Q2DSimpleViewer() for _ in range(num_classes)]
        self._images: list[np.ndarray] = []
        self._image_consensus: np.ndarray = np.array([])
        self._job_dir = job_dir

        self._mode_projection = ProjectionMode.SLICE
        self._mode_intensity = IntensityMode.DIFF
        self._direction = Direction.XY

        self._dim_slider = QLabeledSlider(QtCore.Qt.Orientation.Horizontal)

        self._viewer_container = QtW.QWidget()
        flow_layout = QFlowLayout(self._viewer_container)
        flow_layout.setVerticalSpacing(4)
        flow_layout.setHorizontalSpacing(4)
        for viewer in self._viewers:
            viewer.setFixedSize(180, 180)
            flow_layout.addWidget(viewer)

        self._iter_choice = QIntWidget("Iteration", label_width=60)
        self._iter_choice.setValue(max(niter_choices))
        self._iter_choice.setRange(min(niter_choices), max(niter_choices))
        self._mode_projection_mgui = ToggleButtons(
            value=self._mode_projection, choices=ProjectionMode
        )
        self._mode_intensity_mgui = ToggleButtons(
            value=self._mode_intensity, choices=IntensityMode
        )
        self._direction_mgui = ToggleButtons(value=self._direction, choices=Direction)

        mode_controls = QtW.QHBoxLayout()
        mode_controls.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        mode_controls.setContentsMargins(0, 0, 0, 0)
        mode_controls.addWidget(self._mode_projection_mgui.native)
        mode_controls.addWidget(self._mode_intensity_mgui.native)
        mode_controls.addWidget(self._direction_mgui.native)
        layout.addLayout(mode_controls)

        data_controls = QtW.QHBoxLayout()
        data_controls.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        data_controls.setContentsMargins(0, 0, 0, 0)
        data_controls.addWidget(self._iter_choice)
        data_controls.addWidget(self._dim_slider)
        layout.addLayout(data_controls)

        layout.addWidget(self._viewer_container)

        self._iter_choice.valueChanged.connect(self._on_iter_changed)
        self._mode_projection_mgui.changed.connect(self._on_mode_projection_changed)
        self._mode_intensity_mgui.changed.connect(self._on_mode_intensity_changed)
        self._direction_mgui.changed.connect(self._on_direction_changed)
        self._dim_slider.valueChanged.connect(self._on_slider_changed)

        self.load_maps(max(niter_choices))

    def load_maps(self, niter: int):
        imgs: list[np.ndarray] = []
        star = read_star(self._job_dir.path / f"run_it{niter:0>3}_model.star")
        df = star["model_classes"].to_polars()
        for map_path in df["rlnReferenceImage"]:
            with mrcfile.open(self._job_dir.resolve_path(map_path)) as mrc:
                img = np.asarray(mrc.data)
                imgs.append(img)
        img_consensus = sum(
            img * dist for img, dist in zip(imgs, df["rlnClassDistribution"])
        )
        self._images = imgs
        self._image_consensus = img_consensus
        self._dim_slider.setMaximum(imgs[0].shape[0] - 1)
        self._dim_slider.setValue(imgs[0].shape[0] // 2)
        self.update_images()

    def update_images(self):
        input_images = []
        for img in self._images:
            match self._direction:
                case Direction.XY:
                    axis = 0
                case Direction.XZ:
                    axis = 1
                case Direction.YZ:
                    axis = 2
            match self._mode_projection:
                case ProjectionMode.MAX:
                    fn = np.max
                case ProjectionMode.MEAN:
                    fn = np.mean
                case ProjectionMode.SLICE:
                    fn = self._slice_image
            match self._mode_intensity:
                case IntensityMode.ORIGINAL:
                    img_input = img
                case IntensityMode.DIFF:
                    img_input = img - self._image_consensus
            img_proj = fn(img_input, axis=axis)
            input_images.append(img_proj)
        input_images = np.stack(input_images)
        # prep LUT
        min0, max0 = np.quantile(input_images, [0.02, 0.98])
        match self._mode_intensity:
            case IntensityMode.ORIGINAL:
                _cmap = "gray"
                _clim = (min0, max0)
            case IntensityMode.DIFF:
                _cmap = Colormap(["blue", "white", "red"]).to_vispy()
                abs_max = max(abs(min0), abs(max0))
                _clim = (-abs_max, abs_max)
        for img_proj, viewer in zip(input_images, self._viewers):
            viewer.set_image(img_proj, cmap=_cmap, clim=_clim)
            viewer.auto_fit()

    def _slice_image(self, img: np.ndarray, axis: int) -> np.ndarray:
        sl = [slice(None)] * img.ndim
        sl[axis] = self._dim_slider.value()
        return img[tuple(sl)]

    def _on_iter_changed(self, value: int):
        self.load_maps(self._job_dir, value)

    def _on_mode_changed(self):
        self.update_images()
        self._dim_slider.setEnabled(self._mode_projection is ProjectionMode.SLICE)

    def _on_mode_projection_changed(self, value: ProjectionMode):
        self._mode_projection = value
        self._on_mode_changed()

    def _on_mode_intensity_changed(self, value: IntensityMode):
        self._mode_intensity = value
        self._on_mode_changed()

    def _on_direction_changed(self, value: Direction):
        self._direction = value
        self._on_mode_changed()

    def _on_slider_changed(self, value: int):
        self.update_images()
