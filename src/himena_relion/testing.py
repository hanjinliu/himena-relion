from typing import TypeVar, Generic
import mrcfile
import numpy as np
from himena_relion._widgets._job_widgets import JobWidgetBase
from himena_relion._job_dir import JobDirectory

_T = TypeVar("_T", bound=JobWidgetBase)


class JobWidgetTester(Generic[_T]):
    def __init__(self, widget: _T, job_dir: JobDirectory):
        self.widget = widget
        self.job_dir = job_dir
        widget.initialize(job_dir)
        self._rng = np.random.default_rng(29958293)

    def write_text(self, path: str, text: str):
        fp = self.job_dir.path / path
        fp.write_text(text)
        self.widget.on_job_updated(self.job_dir, str(fp))

    def write_mrc(self, path: str, data: np.ndarray):
        fp = self.job_dir.path / path
        with mrcfile.new(fp) as mrc:
            mrc.set_data(data)
        self.widget.on_job_updated(self.job_dir, str(fp))

    def write_random_mrc(self, path: str, shape: tuple[int, ...], dtype=np.float32):
        self.write_mrc(path, self.make_random_mrc(shape, dtype))

    def make_random_mrc(self, shape: tuple[int, ...], dtype=np.float32) -> np.ndarray:
        return self._rng.normal(loc=1.0, scale=1.0, size=shape).astype(dtype)
