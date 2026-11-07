"""Interactive class selection (relion.select.interactive) in the himena main window.

This replaces `relion_display --gui --i <optimiser.star> --allow_save ...` that RELION
runs for the "Subset selection" job with an optimiser/model STAR file as the input.
While the job is running, the classes are selected in the Results tab of the job
window. The output files are the same as those of `relion_display`:

- `backup_selection.star`: rlnSelected (1 or 0) of all the classes, in the class order.
- `class_averages.star`: rows of the selected classes in the model_classes table (only
  for 2D classes). If recentering is requested, images are recentered and saved in
  `class_averages.mrcs`.
- `particles.star`: particles that belong to the selected classes, with the general
  and optics blocks of the input data.star.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from pathlib import Path
from typing import Callable, Iterator

import mrcfile
import numpy as np
from numpy.typing import NDArray
import polars as pl
from starfile_rs import LoopDataBlock, as_star, empty_star, read_star
from starfile_rs.core import StarDict

from himena_relion._job_dir import JobDirectory
from himena_relion.hijack._base import HijackedJob

BACKUP_SELECTION = "backup_selection.star"
CLASS_AVERAGES = "class_averages.star"
PARTICLES = "particles.star"
_STAR_HEADER = "\n# version 50001\n"

# These columns are converted to numbers. Others are kept as strings so that the
# values are written back exactly as they were.
_CLASS_NUMBER = "rlnClassNumber"
_NUMERIC_PARTICLE_COLUMNS = (_CLASS_NUMBER, "rlnGroupNumber", "rlnOpticsGroup")
_NUMERIC_CLASS_COLUMNS = (
    _CLASS_NUMBER,
    "rlnClassDistribution",
    "rlnEstimatedResolution",
)


@dataclass
class ClassSelectionInput:
    """Input of the class selection loaded from an optimiser.star or model.star."""

    rln_dir: Path
    fn_model: str
    model_star: Path
    data_star: Path
    classes: pl.DataFrame
    """The model_classes table, with rlnClassNumber."""
    data: StarDict
    """The whole data.star."""
    particles: pl.DataFrame
    groups: pl.DataFrame | None = None
    """The model_groups table, used for regrouping."""
    _counts: NDArray[np.int64] | None = field(default=None, repr=False)

    @classmethod
    def from_fn_model(cls, fn_model: str, rln_dir: str | Path) -> ClassSelectionInput:
        """Load the input, in the same way as `relion_display` does."""
        rln_dir = Path(rln_dir)
        fn_data, fn_model_star = _data_and_model_star_path(fn_model, rln_dir)
        model_star = _resolve(rln_dir, fn_model_star)
        data_star = _resolve(rln_dir, fn_data)
        star_model = read_star(model_star)
        if "model_classes" not in star_model:
            raise ValueError(f"model_classes table not found in {model_star}.")
        block_classes = star_model["model_classes"].trust_loop()
        classes = block_classes.to_polars(
            string_columns=_string_columns(block_classes, _NUMERIC_CLASS_COLUMNS)
        )
        if _CLASS_NUMBER not in classes.columns:
            classes = classes.with_columns(
                pl.int_range(1, classes.height + 1, dtype=pl.Int64).alias(_CLASS_NUMBER)
            )
        groups = None
        if (blk := star_model.get("model_groups")) is not None:
            groups = blk.trust_loop().to_polars()

        data = read_star(data_star)
        if "particles" in data:
            block_particles = data["particles"].trust_loop()
        else:
            # backward compatibility
            block_particles = data.first().trust_loop()
        particles = block_particles.to_polars(
            string_columns=_string_columns(block_particles, _NUMERIC_PARTICLE_COLUMNS)
        )
        if _CLASS_NUMBER not in particles.columns:
            raise ValueError(f"{_CLASS_NUMBER} not found in {data_star}.")
        return cls(
            rln_dir=rln_dir,
            fn_model=fn_model,
            model_star=model_star,
            data_star=data_star,
            classes=classes,
            data=data,
            particles=particles,
            groups=groups,
        )

    @property
    def num_classes(self) -> int:
        return self.classes.height

    @property
    def class_numbers(self) -> NDArray[np.int64]:
        return self.classes[_CLASS_NUMBER].to_numpy().astype(np.int64)

    @property
    def num_particles(self) -> int:
        return self.particles.height

    def particle_counts(self) -> NDArray[np.int64]:
        """Number of particles assigned to each class."""
        if self._counts is None:
            counts = self.particles[_CLASS_NUMBER].value_counts()
            count_map = dict(zip(counts[_CLASS_NUMBER], counts["count"]))
            self._counts = np.array(
                [count_map.get(int(n), 0) for n in self.class_numbers],
                dtype=np.int64,
            )
        return self._counts

    def class_distributions(self) -> NDArray[np.float64]:
        if "rlnClassDistribution" in self.classes.columns:
            return self.classes["rlnClassDistribution"].to_numpy().astype(np.float64)
        counts = self.particle_counts()
        return counts / max(counts.sum(), 1)

    def resolutions(self) -> NDArray[np.float64]:
        if "rlnEstimatedResolution" in self.classes.columns:
            return self.classes["rlnEstimatedResolution"].to_numpy().astype(np.float64)
        return np.full(self.num_classes, np.nan)

    def reference_images(self) -> list[str]:
        return list(self.classes["rlnReferenceImage"])

    def is_3d(self) -> bool:
        """True if the class references are 3D maps."""
        ref = self.reference_images()[0]
        if "@" in ref:
            return False
        path = _resolve(self.rln_dir, ref)
        with mrcfile.open(path, header_only=True, permissive=True) as mrc:
            return int(mrc.header.nz) > 1

    def iter_class_images(self) -> Iterator[NDArray[np.float32] | None]:
        """Iterate over the reference images (2D or 3D) of all the classes."""
        stacks: dict[Path, np.ndarray] = {}
        for ref in self.reference_images():
            if "@" in ref:
                num, path_str = ref.split("@", 1)
                path = _resolve(self.rln_dir, path_str)
                if path not in stacks:
                    if not path.exists():
                        yield None
                        continue
                    with mrcfile.open(path, permissive=True) as mrc:
                        arr = np.asarray(mrc.data, dtype=np.float32)
                    stacks[path] = arr if arr.ndim == 3 else arr[np.newaxis]
                stack = stacks[path]
                idx = int(num) - 1
                yield stack[idx] if 0 <= idx < stack.shape[0] else None
            else:
                path = _resolve(self.rln_dir, ref)
                if not path.exists():
                    yield None
                    continue
                with mrcfile.open(path, permissive=True) as mrc:
                    yield np.asarray(mrc.data, dtype=np.float32)

    def pixel_size(self) -> float:
        """Pixel size of the reference images."""
        ref = self.reference_images()[0]
        path = _resolve(self.rln_dir, ref.split("@", 1)[-1])
        with mrcfile.open(path, header_only=True, permissive=True) as mrc:
            return float(mrc.voxel_size.x)


@dataclass
class SelectionResult:
    num_classes: int
    num_particles: int
    files: list[Path]

    def message(self) -> str:
        return (
            f"Saved {self.num_classes} selected classes with {self.num_particles} "
            "particles."
        )


def write_selection(
    job_dir: JobDirectory,
    source: ClassSelectionInput,
    selected: NDArray[np.bool_],
    *,
    write_class_averages: bool,
    do_recenter: bool = False,
    nr_regroups: int = -1,
    log: Callable[[str], None] = print,
) -> SelectionResult:
    """Write the output files of the class selection.

    Files are written in the same order as `relion_display`: backup_selection.star,
    class_averages.star and particles.star.
    """
    selected = np.asarray(selected, dtype=bool)
    if selected.shape != (source.num_classes,):
        raise ValueError(
            f"Selection must have {source.num_classes} elements, got {selected.shape}."
        )
    if not selected.any():
        raise ValueError("No classes selected. Please select one or more classes.")
    selected_numbers = source.class_numbers[selected].tolist()
    particles = source.particles.filter(pl.col(_CLASS_NUMBER).is_in(selected_numbers))
    if particles.height == 0:
        raise ValueError("The selected classes do not contain any particles.")
    if nr_regroups > 0:
        if source.groups is None:
            raise ValueError("model_groups table is needed for regrouping.")
        particles = regroup_particles(particles, source.groups, nr_regroups, log=log)

    files: list[Path] = []
    # backup_selection.star
    path = job_dir.path / BACKUP_SELECTION
    df_backup = pl.DataFrame({"rlnSelected": selected.astype(np.int64)})
    _write_star(path, as_star({"": df_backup}))
    log(f" Written out {_rel(job_dir, path)}")
    files.append(path)

    # class_averages.star
    if write_class_averages:
        df_classes = source.classes.filter(pl.Series(selected))
        if do_recenter:
            df_classes = _write_recentered_images(job_dir, source, selected, df_classes)
        path = job_dir.path / CLASS_AVERAGES
        _write_star(path, as_star({"": df_classes}))
        log(f" Saved {_rel(job_dir, path)} with {df_classes.height} selected images.")
        files.append(path)

    # particles.star
    star_out = empty_star()
    for name in ["general", "optics"]:
        if (blk := source.data.get(name)) is not None:
            star_out.with_block(blk)
    star_out.with_block(LoopDataBlock.from_polars("particles", particles))
    path = job_dir.path / PARTICLES
    _write_star(path, star_out)
    log(f" Saved {_rel(job_dir, path)} with {particles.height} selected particles.")
    files.append(path)
    return SelectionResult(int(selected.sum()), particles.height, files)


def read_backup_selection(
    job_dir: JobDirectory, num_classes: int
) -> NDArray[np.bool_] | None:
    """Read backup_selection.star, as relion_display does when it starts."""
    path = job_dir.path / BACKUP_SELECTION
    if not path.exists():
        return None
    try:
        df = read_star(path).first().trust_loop().to_polars()
        selected = df["rlnSelected"].to_numpy() > 0
    except Exception:
        return None
    if selected.size != num_classes:
        print(
            f" Warning: ignoring {BACKUP_SELECTION} with unexpected number of entries..."
        )
        return None
    return selected


def expects_class_averages(job_dir: JobDirectory, fn_model: str) -> bool:
    """Whether class_averages.star is an output node of this job.

    RELION registers class_averages.star only for 2D classes. The output nodes in
    job_pipeline.star are respected if available.
    """
    try:
        pipeline = job_dir.parse_job_pipeline()
    except Exception:
        pass
    else:
        if names := [node.path.name for node in pipeline.outputs]:
            return CLASS_AVERAGES in names
    # same condition as RelionJob::getCommandsSelectJob
    return "Class2D/" in fn_model or (
        "Select/" in fn_model and "run_optimiser.star" in fn_model
    )


def recenter_image(img: NDArray[np.floating]) -> NDArray[np.float32]:
    """Translate the center of mass of the positive pixels to the image center.

    Same as `selfTranslateCenterOfMassToCenter` of RELION (origin at size // 2, linear
    interpolation and wrapping).
    """
    from scipy import ndimage as ndi

    img = np.asarray(img, dtype=np.float32)
    positive = img > 0
    mass = float(img[positive].sum())
    if mass == 0:
        return img.copy()
    coords = np.indices(img.shape, dtype=np.float64)
    com = [
        float((coord[positive] - size // 2).dot(img[positive])) / mass
        for coord, size in zip(coords, img.shape)
    ]
    return ndi.shift(img, [-c for c in com], order=1, mode="grid-wrap").astype(
        np.float32
    )


def regroup_particles(
    particles: pl.DataFrame,
    groups: pl.DataFrame,
    nr_regroups: int,
    log: Callable[[str], None] = print,
) -> pl.DataFrame:
    """Regroup the particles into about `nr_regroups` groups.

    Python port of `regroupSelectedParticles` in RELION displayer.cpp. Groups are sorted
    by the intensity scale correction and merged until each new group contains more
    than (number of particles) / nr_regroups particles.
    """
    if nr_regroups <= 0:
        return particles
    for col in ["rlnGroupNumber", "rlnOpticsGroup"]:
        if col not in particles.columns:
            raise ValueError(f"{col} is needed in the particles for regrouping.")
    if "rlnGroupScaleCorrection" not in groups.columns:
        raise ValueError("rlnGroupScaleCorrection is needed in model_groups.")
    ngroups = groups.height
    group_optics = np.full(ngroups, -1, dtype=np.int64)
    group_nparts = np.zeros(ngroups, dtype=np.int64)
    max_optics_group = -1
    for group_id, optics_id in zip(
        particles["rlnGroupNumber"].to_list(), particles["rlnOpticsGroup"].to_list()
    ):
        idx = int(group_id) - 1  # 1-indexed
        if group_optics[idx] == -1:
            group_optics[idx] = optics_id
            max_optics_group = max(max_optics_group, int(optics_id))
        elif group_optics[idx] != optics_id:
            log(
                f"WARNING: group_no {group_id} contains particles from multiple optics "
                "groups."
            )
        group_nparts[idx] += 1

    scale = groups["rlnGroupScaleCorrection"].cast(pl.Float64).to_numpy()
    if "rlnGroupNumber" in groups.columns:
        group_numbers = groups["rlnGroupNumber"].cast(pl.Int64).to_numpy()
    else:
        group_numbers = np.arange(1, ngroups + 1)
    order = np.argsort(scale, kind="stable")

    nr_parts = particles.height
    average_group_size = nr_parts // nr_regroups
    if average_group_size < 10:
        raise ValueError("Each group should have at least 10 particles")
    nchars = int(math.floor(math.log10(nr_regroups))) + 1

    new_group_names: dict[int, str] = {}
    new_group_id = 0
    for optics_group_id in range(1, max_optics_group + 1):
        nr_parts_in_new_group = 0
        new_group_id += 1
        for idx in order:
            if group_optics[idx] != optics_group_id:
                continue
            nr_parts_in_new_group += group_nparts[idx]
            if nr_parts_in_new_group > average_group_size:
                # This group is now full: start a new one
                new_group_id += 1
                nr_parts_in_new_group = 0
            new_group_names[int(group_numbers[idx])] = (
                f"group_{new_group_id:0{nchars}d}"
            )

    group_no = particles["rlnGroupNumber"].cast(pl.Int64)
    if missing := set(group_no.unique().to_list()) - set(new_group_names):
        raise ValueError(f"Cannot find group_id {sorted(missing)} during remapping.")
    names = group_no.replace_strict(new_group_names, return_dtype=pl.String)
    log(f" Regrouped particles into {new_group_id} groups")
    return particles.with_columns(names.alias("rlnGroupName")).drop("rlnGroupNumber")


class SelectClassesInteractive(HijackedJob):
    """Interactive selection of 2D/3D classes, replacing `relion_display`."""

    @classmethod
    def type_label(cls) -> str:
        return "relion.select.interactive"

    @classmethod
    def matches(cls, job_params: dict[str, str]) -> bool:
        # Interactive selection of micrographs or particles is not supported.
        return job_params.get("fn_model", "").strip() not in ("", '""')

    @classmethod
    def create_widget(cls, job_dir: JobDirectory):
        from himena_relion.hijack._select_gui import QClassSelectionJobWidget

        return QClassSelectionJobWidget(job_dir)


@dataclass
class SelectionParams:
    """Parameters of the Select job used for the interactive class selection."""

    fn_model: str
    write_class_averages: bool
    do_recenter: bool = False
    nr_regroups: int = -1

    @classmethod
    def from_job_dir(cls, job_dir: JobDirectory) -> SelectionParams:
        params = job_dir.get_job_params_as_dict()
        fn_model = str(params.get("fn_model", ""))
        write_class_averages = expects_class_averages(job_dir, fn_model)
        # same as RELION: recentering is only for 2D class averages
        do_recenter = _is_yes(params.get("do_recenter")) and write_class_averages
        if _is_yes(params.get("do_regroup")):
            nr_regroups = int(float(params.get("nr_groups", 1)))
        else:
            nr_regroups = -1
        return cls(fn_model, write_class_averages, do_recenter, nr_regroups)


def _is_yes(value) -> bool:
    return str(value).strip().lower() in ("yes", "true", "1")


def _data_and_model_star_path(fn_model: str, rln_dir: Path) -> tuple[str, str]:
    """Return (data.star, model.star) for the input, same as Displayer::initialise."""
    for suffix in ["_half1_model.star", "_half2_model.star", "_model.star"]:
        if suffix in fn_model:
            return fn_model.replace(suffix, "_data.star", 1), fn_model
    if "_optimiser.star" in fn_model:
        fn_data = fn_model.replace("_optimiser.star", "_data.star", 1)
        star = read_star(_resolve(rln_dir, fn_model))
        if (block := star.get("optimiser_general")) is None:
            block = star.first()
        fn_model_star = block.trust_single().to_dict()["rlnModelStarFile"]
        return fn_data, str(fn_model_star)
    raise ValueError(
        f"Input {fn_model!r} must be an optimiser.star or model.star file of a "
        "classification job."
    )


def _resolve(rln_dir: Path, path: str | Path) -> Path:
    p = Path(path)
    if p.is_absolute():
        return p
    return rln_dir / p


def _rel(job_dir: JobDirectory, path: Path) -> str:
    return job_dir.make_relative_path(path).as_posix()


def _string_columns(block: LoopDataBlock, numeric: tuple[str, ...]) -> list[str]:
    return [c for c in block.columns if c not in numeric]


def _write_star(path: Path, star: StarDict):
    """Write a STAR file atomically, so that readers never see a partial file."""
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(_STAR_HEADER + star.to_string(), newline="\n")
    tmp.replace(path)


def _write_recentered_images(
    job_dir: JobDirectory,
    source: ClassSelectionInput,
    selected: NDArray[np.bool_],
    df_classes: pl.DataFrame,
) -> pl.DataFrame:
    stack_path = job_dir.path / CLASS_AVERAGES.replace(".star", ".mrcs")
    images = [
        recenter_image(img)
        for img, sel in zip(source.iter_class_images(), selected)
        if sel
    ]
    tmp = stack_path.with_name(stack_path.name + ".tmp")
    with mrcfile.new(tmp, overwrite=True) as mrc:
        mrc.set_data(np.stack(images).astype(np.float32))
        mrc.set_image_stack()
        mrc.voxel_size = source.pixel_size()
    tmp.replace(stack_path)
    stack_rel = _rel(job_dir, stack_path)
    names = [f"{i + 1:06d}@{stack_rel}" for i in range(len(images))]
    return df_classes.with_columns(pl.Series("rlnReferenceImage", names))
