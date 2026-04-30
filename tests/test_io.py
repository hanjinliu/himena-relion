import mrcfile
from pathlib import Path
from himena import StandardType
from himena.widgets import MainWindow
from himena_relion._widgets import Q3DViewer
import numpy as np

def test_read_mrc_file(himena_ui: MainWindow, tmpdir):
    tmpdir = Path(tmpdir)
    rng = np.random.default_rng(402)

    with mrcfile.new(mrc_path := tmpdir.joinpath("test.mrc")) as mrc:
        mrc.set_data(rng.standard_normal((30, 30, 30), dtype=np.float32).astype(np.float16))
        mrc.voxel_size = (1.4, 1.4, 1.4)
    win = himena_ui.read_file(mrc_path)
    assert win.model_type() == StandardType.IMAGE
    assert isinstance(win.widget, Q3DViewer)  # density map should be opened in 3D viewer

    with mrcfile.new(mrc_path := tmpdir.joinpath("test.mrcs")) as mrc:
        mrc.set_data(rng.standard_normal((30, 30, 30), dtype=np.float32).astype(np.float16))
        mrc.voxel_size = (1.4, 1.4, 1.4)
    win = himena_ui.read_file(mrc_path)
    assert win.model_type() == StandardType.IMAGE
    assert not isinstance(win.widget, Q3DViewer)

    with mrcfile.new(mrc_path := tmpdir.joinpath("tomo.mrc")) as mrc:
        mrc.set_data(rng.standard_normal((10, 800, 600), dtype=np.float32).astype(np.float16))
        mrc.voxel_size = (1.4, 1.4, 1.4)
    win = himena_ui.read_file(mrc_path)
    assert win.model_type() == StandardType.IMAGE
    assert not isinstance(win.widget, Q3DViewer)
