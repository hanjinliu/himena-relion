import argparse
import numpy as np
import napari
import mrcfile
from scipy import ndimage as ndi
from qtpy import QtWidgets as QtW
from pathlib import Path


class QNapariActions(QtW.QWidget):
    def __init__(self):
        super().__init__()
        self._layout = QtW.QVBoxLayout(self)

    def add_action(self, label: str):
        def _inner(cb):
            btn = QtW.QPushButton(label)
            btn.clicked.connect(cb)
            self._layout.addWidget(btn)
            btn.setToolTip(cb.__doc__ or "")

        return _inner

    def add_float_edit(
        self,
        label: str,
        min: float = 0.0,
        max: float = 100.0,
        step: float = 0.1,
        default: float = 0.0,
        tooltip: str = "",
    ) -> QtW.QDoubleSpinBox:
        layout = QtW.QHBoxLayout()
        layout.addWidget(QtW.QLabel(label))
        spinbox = QtW.QDoubleSpinBox()
        spinbox.setRange(min, max)
        spinbox.setValue(default)
        spinbox.setSingleStep(step)
        spinbox.setToolTip(tooltip)
        layout.addWidget(spinbox)
        self._layout.addLayout(layout)
        return spinbox


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Draw a mask in napari.")
    parser.add_argument("map_path", help="Map to draw the mask on.")
    parser.add_argument("output_job_dir", help="mask_base.mrc is saved here.")
    parser.add_argument(
        "--mask", default=None, help="Mask to start from, such as mask_base.mrc."
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.5,
        help="Threshold to binarize the mask given by --mask.",
    )
    return parser.parse_args(argv)


def initial_labels(
    data: np.ndarray, mask_path: str | None, threshold: float
) -> np.ndarray:
    """Labels to start from: the binarized mask, or zeros."""
    if mask_path is not None:
        with mrcfile.open(mask_path) as mrc:
            mask = np.asarray(mrc.data)
        if mask.shape == data.shape:
            return (mask > threshold).astype(np.uint8)
        print(
            f"Shape of {mask_path} {mask.shape} does not match the map {data.shape}. "
            "Starting from no mask."
        )
    return np.zeros_like(data, dtype=np.uint8)


def main():
    args = parse_args()
    output_job_dir = args.output_job_dir
    viewer = napari.Viewer()

    with mrcfile.open(args.map_path) as mrc:
        data = mrc.data
        scale = mrc.voxel_size.x
    layer_image = viewer.add_image(data, name="Map", scale=(scale, scale, scale))
    layer_label = viewer.add_labels(
        initial_labels(data, args.mask, args.threshold),
        name="Mask",
        scale=(scale, scale, scale),
    )
    layer_label.n_edit_dimensions = 3
    layer_label.mode = "paint"

    def _set_data(new_data: np.ndarray):
        # TODO: better to update with undo support.
        layer_label.data = new_data.astype(np.uint8)

    dock = QNapariActions()

    @dock.add_action("Morphological Erode")
    def morphological_erode():
        """Apply morphological erosion to the current mask."""
        mask_data = np.asarray(layer_label.data > 0, dtype=np.uint8)
        opened_mask = ndi.binary_erosion(
            mask_data, structure=_make_circular_footprint(param_morph.value())
        )
        _set_data(opened_mask.astype(np.uint8))

    @dock.add_action("Morphological Dilate")
    def morphological_dilate():
        """Apply morphological dilation to the current mask."""
        mask_data = np.asarray(layer_label.data > 0, dtype=np.uint8)
        closed_mask = ndi.binary_dilation(
            mask_data, structure=_make_circular_footprint(param_morph.value())
        )
        _set_data(closed_mask.astype(np.uint8))

    param_morph = dock.add_float_edit(
        "with radius",
        min=1.0,
        max=50.0,
        step=0.1,
        default=1.0,
        tooltip="Radius for morphological operations.",
    )

    @dock.add_action("Map To Mask")
    def map_to_mask():
        """Paint the map region above lower contrast limit."""
        c0 = layer_image.contrast_limits[0]
        mask_data = layer_image.data >= c0
        _set_data(mask_data.astype(np.uint8))

    @dock.add_action("Save Mask")
    def save_mask():
        """Save the current mask to the output path specified by the job."""
        mask_data = np.asarray(layer_label.data > 0, dtype=np.uint8)
        with mrcfile.new(Path(output_job_dir) / "mask_base.mrc", overwrite=True) as mrc:
            mrc.set_data(mask_data)
            mrc.voxel_size = (scale, scale, scale)
        viewer.close()

    viewer.window.add_dock_widget(dock, area="right")
    viewer.title = f"Draw mask ({Path(output_job_dir).name})"
    napari.run()


def _make_circular_footprint(radius: float):
    size = int(np.ceil(radius) * 2) + 1
    zz, yy, xx = np.indices((size, size, size), dtype=np.float32)
    center = size // 2
    dist2 = (zz - center) ** 2 + (yy - center) ** 2 + (xx - center) ** 2
    return dist2 <= radius**2


if __name__ == "__main__":
    main()
