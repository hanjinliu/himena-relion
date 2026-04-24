from inspect import isgenerator
from pathlib import Path
from typing import TypeVar, Generic
import mrcfile
import numpy as np
from himena_relion._widgets._job_widgets import JobWidgetBase
from himena_relion._job_dir import ExternalJobDirectory, JobDirectory
from himena_relion.external.job_class import RelionExternalJob
from himena_relion.consts import ARG_NAME_REMAP


_T = TypeVar("_T", bound=JobWidgetBase)


class JobWidgetTester(Generic[_T]):
    def __init__(self, widget: _T, job_dir: JobDirectory):
        self.widget = widget
        self.job_dir = job_dir
        widget.initialize(job_dir)
        self._rng = np.random.default_rng(29958293)

    @classmethod
    def no_widget(cls, job_dir: JobDirectory) -> "JobWidgetTester[JobWidgetBase]":
        widget = JobWidgetBase()
        return cls(widget, job_dir)

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

    def write_sphere_mrc(self, path: str, size: int, dtype=np.float32):
        xx, yy, zz = np.indices((size, size, size))
        c = (size - 1) / 2
        sphere = (xx - c) ** 2 + (yy - c) ** 2 + (zz - c) ** 2 < (c * 0.8) ** 2
        self.write_mrc(path, sphere.astype(dtype))

    def make_random_mrc(self, shape: tuple[int, ...], dtype=np.float32) -> np.ndarray:
        return self._rng.normal(loc=1.0, scale=1.0, size=shape).astype(dtype)

    def mkdir(self, name: str):
        fp = self.job_dir.path / name
        fp.mkdir(parents=True, exist_ok=True)

    def initialize(self):
        """Re-initialize the widget with the job directory."""
        self.widget.initialize(self.job_dir)

    def write_exit_with_success(self):
        self.write_text("RELION_JOB_EXIT_SUCCESS", "")


class ExternalJobTester:
    def __init__(self, job_cls: type[RelionExternalJob]):
        self._job_cls = job_cls

    def prep_job_star(self, directory: Path, **kwargs) -> str:
        txt = self._job_cls.prep_job_star(**kwargs).to_string()
        directory.joinpath("job.star").write_text(txt)
        return txt

    def provide_widget(self, directory: Path):
        job_dir = ExternalJobDirectory(directory)
        job = self._job_cls(job_dir)
        widget = job.provide_widget(job_dir)
        if widget is NotImplemented:
            raise NotImplementedError(
                f"{self._job_cls.__name__} does not provide a widget."
            )
        return widget

    def test_run(self, directory: Path, widget=None):
        job_dir = ExternalJobDirectory(directory)
        job = self._job_cls(job_dir)
        if not isinstance(job.import_path(), str):
            raise ValueError(
                f"import_path must return a string, got {job.import_path()!r}"
            )
        if not isinstance(job.job_title(), str):
            raise ValueError(f"job_title must return a string, got {job.job_title()!r}")
        args_str = job_dir.get_job_params_as_dict()
        map_inv = {k: v for v, k in ARG_NAME_REMAP}
        args_str = {map_inv.get(k, k): v for k, v in args_str.items()}
        kwargs = job._parse_args(args_str)
        out = job.run(**kwargs)

        if isgenerator(out):
            while True:
                try:
                    next(out)
                except StopIteration:
                    break

        for fname, type_label in job.output_nodes():
            if not (isinstance(fname, str) and isinstance(type_label, str)):
                raise ValueError(
                    "Output nodes must be tuples of (str, str), got "
                    f"({fname!r}, {type_label!r})"
                )
            if not (new_path := job.output_job_dir.path.joinpath(fname)).exists():
                raise FileNotFoundError(
                    f"Output file {fname} is marked as an output node but was not "
                    "created by the job."
                )
            if widget and hasattr(widget, "on_job_updated"):
                widget.on_job_updated(job.output_job_dir, str(new_path))

        if widget and hasattr(widget, "on_job_updated"):
            widget.on_job_updated(
                job.output_job_dir,
                str(job.output_job_dir.path.joinpath("RELION_JOB_EXIT_SUCCESS")),
            )

        if widget and hasattr(widget, "initialize"):
            widget.initialize(job.output_job_dir)
