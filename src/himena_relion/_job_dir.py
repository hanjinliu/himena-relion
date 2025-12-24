from __future__ import annotations

from contextlib import contextmanager
import logging
from dataclasses import dataclass, field
from pathlib import Path
import shutil
from typing import Callable, Iterator, Literal, TYPE_CHECKING
import numpy as np
from numpy.typing import NDArray
import pandas as pd
from starfile_rs import read_star, read_star_block
import mrcfile
from himena_relion._image_readers._array import ArrayFilteredView
from himena_relion._utils import change_name_for_tomo
from himena_relion.consts import (
    JOB_IMPORT_PATH_FILE,
    RelionJobState,
    JOB_ID_MAP,
    Type,
)
from himena_relion._pipeline import RelionPipeline, RelionOptimisationSet

if TYPE_CHECKING:
    from typing import Self
    from himena_relion.external.job_class import RelionExternalJob, RelionJob

_LOGGER = logging.getLogger(__name__)


class JobDirectory:
    """Base class for handling job directories in RELION."""

    _type_map = {}

    def __init__(self, path: str | Path):
        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(f"Job directory {self.path} does not exist.")

    def __init_subclass__(cls):
        """Register the subclass in the type map."""
        super().__init_subclass__()
        if hasattr(cls, "_job_type"):
            cls._type_map[cls._job_type] = cls

    def __repr__(self):
        return f"{self.__class__.__name__}(path={self.path.as_posix()})"

    @staticmethod
    def from_job_star(path: str | Path) -> JobDirectory:
        fp = Path(path)
        if fp.name != "job.star" or not fp.exists():
            raise ValueError(f"Expected an existing job.star file, got {fp}")
        job_block = read_star_block(fp, block_name="job").trust_single()
        job_type = job_block["rlnJobTypeLabel"]
        cls = JobDirectory._type_map.get(job_type, JobDirectory)
        job_dir = fp.parent
        return cls(job_dir)

    def is_tomo(self) -> bool:
        """Return whether this job is a tomography job."""
        job_block = read_star_block(self.job_star(), block_name="job").trust_single()
        return bool(int(job_block["rlnJobIsTomo"]))

    @property
    def job_id(self) -> str:
        """Return the job ID based on the directory name."""
        _id = self.path.stem
        if _id.startswith("job"):
            return _id[3:]
        return _id

    def job_title(self) -> str:
        """Get the job title (human readable name of this job)."""
        if label := getattr(self, "_job_type", None):
            return JOB_ID_MAP.get(label, label)
        if job_cls := self._to_job_class():
            return job_cls.job_title()
        return "Unknown"

    def himena_model_type(self) -> str:
        """Model type string specific to this job."""
        if label := getattr(self, "_job_type", None):
            subtype = label
            if self.is_tomo():
                subtype = change_name_for_tomo(subtype)
        elif job_cls := self._to_job_class():
            subtype = job_cls.himena_model_type()
        else:
            subtype = "unknown"
        return Type.RELION_JOB + "." + subtype

    @property
    def relion_project_dir(self) -> Path:
        """Return the path to the RELION project directory."""
        return self.path.parent.parent

    def job_alias(self) -> str | None:
        """Return the job alias if exists."""
        pipeline = self.parse_job_pipeline()
        return pipeline.process_alias

    def can_abort(self) -> bool:
        """Check if the job can be aborted."""
        return len(list(self.path.glob("RELION_JOB_*"))) == 0

    def job_star(self) -> Path:
        """Return the path to the job.star file."""
        return self.path / "job.star"

    def job_pipeline(self) -> Path:
        """Return the path to the job's pipeline control file."""
        return self.path / "job_pipeline.star"

    def parse_job_pipeline(self) -> RelionPipeline:
        """Read the job_pipeline.star file under this job directory."""
        return RelionPipeline.from_star(self.job_pipeline())

    def _to_job_class(self) -> type[RelionJob] | None:
        from himena_relion._job_class import iter_relion_jobs

        star = read_star(self.job_star())
        job_block = star["job"].trust_single()

        job_type = job_block["rlnJobTypeLabel"]
        is_tomo = bool(int(job_block["rlnJobIsTomo"]))
        df = star["joboptions_values"].to_pandas()
        job_star_params = dict(zip(df["rlnJobOptionVariable"], df["rlnJobOptionValue"]))

        for subcls in iter_relion_jobs():
            if (
                subcls.type_label() == job_type
                and subcls.job_is_tomo() == is_tomo
                and subcls.param_matches(job_star_params)
            ):
                return subcls
        return None

    @contextmanager
    def edit_job_pipeline(self):
        """Edit job_pipeline.star in this context.

        Examples
        --------
        with job_dir.edit_job_pipeline() as pipeline:
            # modify pipeline
            pipeline.append_output("particles.star", "ParticleGroupMetadata.star")
        """
        pipeline = self.parse_job_pipeline()
        yield pipeline
        pipeline.write_star(self.job_pipeline())

    def state(self) -> RelionJobState:
        """Return the state of the job based on the existence of certain files."""
        if self.path.joinpath("RELION_JOB_EXIT_SUCCESS").exists():
            return RelionJobState.EXIT_SUCCESS
        elif self.path.joinpath("RELION_JOB_EXIT_FAILURE").exists():
            return RelionJobState.EXIT_FAILURE
        elif self.path.joinpath("RELION_JOB_EXIT_ABORTED").exists():
            return RelionJobState.EXIT_ABORTED
        elif self.path.joinpath("RELION_JOB_ABORT_NOW").exists():
            return RelionJobState.ABORT_NOW
        else:
            # TODO: how to deal with preparing state?
            return RelionJobState.RUNNING

    def get_job_param(self, param: str) -> str:
        return self.get_job_params_as_dict()[param]

    def get_job_params_as_dict(self) -> dict[str, str]:
        df = read_star_block(self.job_star(), "joboptions_values").to_pandas()
        return dict(zip(df["rlnJobOptionVariable"], df["rlnJobOptionValue"]))

    def iter_tilt_series(self) -> Iterator[TiltSeriesInfo]:
        """Iterate over all tilt series info."""
        raise NotImplementedError(
            f"iter_tilt_series not implemented for {self.__class__.__name__}"
        )

    def clear_job(self):
        for item in self.path.iterdir():
            if item.is_file():
                if item.name not in MINIMUM_FILES_TO_KEEP:
                    item.unlink()
            else:
                shutil.rmtree(item)


class HasFrameJobDirectory(JobDirectory):
    def iter_frames(self, pattern: str) -> Iterator[Path]:
        """Iterate over all motion correction info as DataFrames."""
        frames_dir = self.path / "frames"
        yield from frames_dir.glob(pattern)


class HasTiltSeriesJobDirectory(JobDirectory):
    def iter_tilt_series_path(self) -> Iterator[Path]:
        """Iterate over all motion correction info as DataFrames."""
        ts_dir = self.path / "tilt_series"
        yield from ts_dir.glob("*.star")


class HasTomogramsJobDirectory(JobDirectory):
    def iter_tomograms(self) -> Iterator[Path]:
        """Iterate over all tomogram info as DataFrames."""
        tomo_dir = self.path / "tomograms"
        yield from tomo_dir.glob("*.mrc")


MINIMUM_FILES_TO_KEEP = ["job.star", "job_pipeline.star", "note.txt"]


class ExternalJobDirectory(JobDirectory):
    """External job directories in RELION."""

    _job_type = "relion.external"

    def _to_job_class(self) -> type[RelionExternalJob] | None:
        from himena_relion.external.job_class import pick_job_class

        if import_path := self.job_import_path():
            job_cls = pick_job_class(import_path)
            return job_cls
        return None

    def job_title(self) -> str:
        """Get the job title (human readable name of this job)."""
        if job_cls := self._to_job_class():
            return job_cls.job_title()
        return super().job_title()

    def himena_model_type(self) -> str:
        """Model type string specific to this job."""
        if import_path := self.job_import_path():
            subtype = import_path.replace(".", "-").replace("/", "-").replace(":", "-")
        else:
            subtype = "unknown"
        return Type.RELION_JOB + "." + subtype

    def job_import_path(self) -> str | None:
        """Import path for the external job class object."""
        if (f := self.path.joinpath(JOB_IMPORT_PATH_FILE)).exists():
            return f.read_text(encoding="utf-8").strip()
        fn_exe = self.get_job_param("fn_exe")
        if fn_exe.startswith("himena-relion "):
            import_path = fn_exe[len("himena-relion ") :].strip()
            return import_path
        return None

    def get_job_params_as_dict(self) -> dict[str, str]:
        param_dict = super().get_job_params_as_dict()
        out = {}
        for k in [
            "fn_exe", "do_queue", "in_3dref", "in_coords", "in_mask", "in_mic",
            "in_mov", "in_part", "min_dedicated", "nr_threads", "other_args",
        ]:  # fmt: skip
            if k in param_dict:
                out[k] = param_dict[k]
        for ith in range(1, 11):
            label_key = f"param{ith}_label"
            value_key = f"param{ith}_value"
            if label_key in param_dict and value_key in param_dict:
                out[param_dict[label_key]] = param_dict[value_key]
        out.pop("", None)  # when there are empty param labels
        return out


@dataclass
class TiltSeriesInfo:
    tomo_name: str
    tomo_tilt_series_star_file: Path
    voltage: float = -1.0
    spherical_abberation: float = -1.0
    amplitude_contrast: float = -1.0
    micrograph_original_pixel_size: float = -1.0
    tomo_hand: Literal[1, -1] = 1
    tomo_tilt_series_pixel_size: float = -1.0

    @classmethod
    def from_series(cls, series: pd.Series) -> Self:
        """Create a TiltSeriesInfo instance from a pandas Series."""
        return cls(
            tomo_name=series.get("rlnTomoName", ""),
            tomo_tilt_series_star_file=Path(
                series.get("rlnTomoTiltSeriesStarFile", "")
            ),
            voltage=series.get("rlnVoltage", -1.0),
            spherical_abberation=series.get("rlnSphericalAberration", -1.0),
            amplitude_contrast=series.get("rlnAmplitudeContrast", -1.0),
            micrograph_original_pixel_size=series.get(
                "rlnMicrographOriginalPixelSize", -1.0
            ),
            tomo_hand=series.get("rlnTomoHand", 1),
        )

    def read_tilt_series_star(self, job_dir: Path) -> pd.DataFrame:
        """Read the tilt series star file."""
        rln_job_dir = job_dir.parent.parent
        df = _read_star_as_df(rln_job_dir / self.tomo_tilt_series_star_file)
        return df

    def read_tilt_series(self, rln_dir: Path) -> ArrayFilteredView:
        """Read the tilt series from the file."""
        return self._read_image_series(rln_dir, "rlnMicrographName")

    def _read_image_series(self, rln_dir: Path, column_name: str) -> ArrayFilteredView:
        """Read the image series from the specified column in the star file."""
        df = _read_star_as_df(rln_dir / self.tomo_tilt_series_star_file)
        paths = [rln_dir / p for p in df[column_name]]
        if "rlnTomoNominalStageTiltAngle" in df:
            tilt_angles = df["rlnTomoNominalStageTiltAngle"]
            order = np.argsort(tilt_angles)
            paths = [paths[i] for i in order]
            df = df.iloc[order].reset_index(drop=True)
        view = ArrayFilteredView.from_mrcs(paths)
        view.dataframe = df
        return view


class ImportJobDirectory(HasFrameJobDirectory):
    """Class for handling import job directories in RELION."""

    _job_type = "relion.importtomo"

    def tilt_series_star(self) -> Path:
        """Return the path to the tilt series star file."""
        return self.path / "tilt_series.star"

    def iter_tilt_series(self) -> Iterator[TiltSeriesInfo]:
        """Iterate over all tilt series info."""
        for _, row in _read_star_as_df(self.tilt_series_star()).iterrows():
            yield TiltSeriesInfo.from_series(row)

    # def tilt_series_paths(self) -> list[Path]:
    #     df = _read_star_as_df(self.tilt_series_star())


@dataclass
class CorrectedTiltSeriesInfo(TiltSeriesInfo):
    @classmethod
    def from_series(cls, series: pd.Series) -> Self:
        """Create a CorrectedTiltSeriesInfo instance from a pandas Series."""
        out = super().from_series(series)
        out.tomo_tilt_series_pixel_size = series.get("rlnTomoTiltSeriesPixelSize", -1.0)
        return out


class MotionCorrectionJobDirectory(HasFrameJobDirectory):
    """Class for handling motion correction job directories in RELION."""

    _job_type = "relion.motioncorr.own"

    def corrected_tilt_series_star(self) -> Path:
        """Return the path to the motion-corrected tilt series star file."""
        return self.path / "corrected_tilt_series.star"

    def iter_tilt_series(self) -> Iterator[CorrectedTiltSeriesInfo]:
        """Iterate over all motion correction info."""
        fp = self.corrected_tilt_series_star()
        star = read_star(fp).first().trust_loop().to_pandas()
        for _, row in star.iterrows():
            yield CorrectedTiltSeriesInfo.from_series(row)

    def corrected_tilt_series(self, tomoname: str) -> CorrectedTiltSeriesInfo:
        """Return the first corrected tilt series info."""
        fp = self.corrected_tilt_series_star()
        star = read_star(fp).first().trust_loop().to_pandas()
        star_filt = star[star["rlnTomoName"] == tomoname]
        if len(star_filt) == 0:
            raise ValueError(f"Tilt series {tomoname} not found in star file.")
        row = star_filt.iloc[0]
        return CorrectedTiltSeriesInfo.from_series(row)


class CtfCorrectedTiltSeriesInfo(CorrectedTiltSeriesInfo):
    """Data class for CTF-corrected tilt series information."""

    tomo_tilt_series_ctf_image: Path = Path("")

    @classmethod
    def from_series(cls, series: pd.Series) -> Self:
        """Create a CtfCorrectedTiltSeriesInfo instance from a pandas Series."""
        out = super().from_series(series)
        out.tomo_tilt_series_ctf_image = Path(
            series.get("rlnTomoTiltSeriesCtfImage", "")
        )
        return out

    def read_ctf_series(self, rln_dir: Path) -> ArrayFilteredView:
        """Read the tilt series from the file."""
        return self._read_image_series(rln_dir, "rlnCtfImage")


class CtfCorrectionJobDirectory(HasTiltSeriesJobDirectory):
    """Class for handling CTF correction job directories in RELION."""

    _job_type = "relion.ctffind.ctffind4"

    def tilt_series_ctf_star(self) -> Path:
        """Return the path to the CTF-corrected tilt series star file."""
        return self.path / "tilt_series_ctf.star"

    def iter_tilt_series(self) -> Iterator[CtfCorrectedTiltSeriesInfo]:
        """Iterate over all CTF-corrected tilt series info."""
        fp = self.tilt_series_ctf_star()
        star = read_star(fp).first().trust_loop().to_pandas()
        for _, row in star.iterrows():
            yield CtfCorrectedTiltSeriesInfo.from_series(row)


@dataclass
class SelectedTiltSeriesInfo(CorrectedTiltSeriesInfo):
    tilt_series_star_file: Path = Path("")

    @classmethod
    def from_series(cls, series: pd.Series) -> Self:
        """Create a SelectedTiltSeriesInfo instance from a pandas Series."""
        out = super().from_series(series)
        out.tilt_series_star_file = Path(series.get("rlnTomoTiltSeriesStarFile", ""))
        return out


class ExcludeTiltSeriesJobDirectory(HasTiltSeriesJobDirectory):
    """Class for handling exclude tilt series job directories in RELION."""

    _job_type = "relion.excludetilts"

    def selected_tilt_series_star(self) -> Path:
        """Return the path to the selected tilt series star file."""
        return self.path / "selected_tilt_series.star"

    def iter_tilt_series(self) -> Iterator[SelectedTiltSeriesInfo]:
        """Iterate over all excluded tilt series info."""
        if (path := self.selected_tilt_series_star()).exists():
            star = read_star(path).first().trust_loop().to_pandas()
            for _, row in star.iterrows():
                yield SelectedTiltSeriesInfo.from_series(row)


@dataclass
class AlignedTiltSeriesInfo(SelectedTiltSeriesInfo):
    """Data class for aligned tilt series information."""

    etomo_directive_file: Path = Path("")
    imod_residual_error_mean: float = -1.0
    imod_residual_error_stddev: float = -1.0
    imod_leave_out_error: float = -1.0

    @classmethod
    def from_series(cls, series: pd.Series) -> Self:
        """Create an ALignedTiltSeriesInfo instance from a pandas Series."""
        out = super().from_series(series)
        out.etomo_directive_file = Path(series.get("rlnEtomoDirectiveFile", ""))
        out.imod_residual_error_mean = series.get("rlnImodResidualErrorMean", -1.0)
        out.imod_residual_error_stddev = series.get("rlnImodResidualErrorStddev", -1.0)
        out.imod_leave_out_error = series.get("rlnImodLeaveOutError", -1.0)
        return out


class AlignTiltSeriesJobDirectory(HasTiltSeriesJobDirectory):
    """Class for handling align tilt series job directories in RELION."""

    _job_type = "relion.aligntiltseries"

    def aligned_tilt_series_star(self) -> Path:
        """Return the path to the aligned tilt series star file."""
        return self.path / "aligned_tilt_series.star"

    def iter_aligned_tilt_series(self) -> Iterator[AlignedTiltSeriesInfo]:
        """Iterate over all aligned tilt series info."""
        fp = self.aligned_tilt_series_star()
        star = read_star(fp).first().trust_loop().to_pandas()
        for _, row in star.iterrows():
            yield AlignedTiltSeriesInfo.from_series(row)

    def xf_file(self, tomoname: str) -> Path:
        """Return the path to the .xf file for a given tomogram name."""
        return self.path / "external" / tomoname / f"{tomoname}.xf"

    def fid_file(self, tomoname: str) -> Path:
        """Return the path to the .fid file for a given tomogram name."""
        # this is the mod file of tracked fiducials
        return self.path / "external" / tomoname / f"{tomoname}.fid"

    def preali_file(self, tomoname: str) -> Path:
        """Return the path to the .preali file for a given tomogram name."""
        return self.path / "external" / tomoname / f"{tomoname}_preali.mrc"

    def image_shape_params(self, tomoname: str) -> tuple[int, int, int] | None:
        path_prenewst = self.path / "external" / tomoname / "prenewst.com"
        path_tilt = self.path / "external" / tomoname / "tilt.com"
        nbin_fid = ny = nx = -1
        with path_prenewst.open("r") as f:
            for line in f:
                if line.startswith("BinByFactor	"):
                    nbin_fid = int(line.split()[1])
                    break

        with path_tilt.open("r") as f:
            # FULLIMAGE 3838 3710
            for line in f:
                if line.startswith("FULLIMAGE "):
                    nx, ny = map(int, line.split()[1:3])
        if nbin_fid > 0 and ny > 0 and nx > 0:
            return (nbin_fid, ny, nx)
        return None

    def aligned_tilt_series(self, tomoname: str) -> AlignedTiltSeriesInfo:
        """Return the first corrected tilt series info."""
        fp = self.aligned_tilt_series_star()
        star = read_star(fp).first().trust_loop().to_pandas()
        star_filt = star[star["rlnTomoName"] == tomoname]
        if len(star_filt) == 0:
            raise ValueError(f"Tilt series {tomoname} not found in star file.")
        row = star_filt.iloc[0]
        return AlignedTiltSeriesInfo.from_series(row)


@dataclass
class TomogramInfo(AlignedTiltSeriesInfo):
    tomogram_binning: float = -1.0
    tomo_size_x: int = -1
    tomo_size_y: int = -1
    tomo_size_z: int = -1
    reconstructed_tomogram: list[Path] = field(default_factory=list)
    get_particles: Callable[[], pd.DataFrame] | None = None

    @classmethod
    def from_series(cls, series: pd.Series) -> Self:
        """Create a TomogramInfo instance from a pandas Series."""
        out = super().from_series(series)
        out.tomogram_binning = series.get("rlnTomoTomogramBinning", -1.0)
        out.tomo_size_x = series.get("rlnTomoSizeX", -1)
        out.tomo_size_y = series.get("rlnTomoSizeY", -1)
        out.tomo_size_z = series.get("rlnTomoSizeZ", -1)
        if "rlnTomoReconstructedTomogram" in series:
            out.reconstructed_tomogram = [Path(series["rlnTomoReconstructedTomogram"])]
        else:
            out.reconstructed_tomogram = [
                Path(series.get("rlnTomoReconstructedTomogramHalf1")),
                Path(series.get("rlnTomoReconstructedTomogramHalf2")),
            ]
        return out

    @classmethod
    def from_series_denoised(cls, series: pd.Series) -> Self:
        """Create a TomogramInfo instance from a pandas Series for denoised tomograms."""
        out = super().from_series(series)
        out.tomogram_binning = series.get("rlnTomoTomogramBinning", -1.0)
        out.tomo_size_x = series.get("rlnTomoSizeX", -1)
        out.tomo_size_y = series.get("rlnTomoSizeY", -1)
        out.tomo_size_z = series.get("rlnTomoSizeZ", -1)
        out.reconstructed_tomogram = [
            Path(series.get("rlnTomoReconstructedTomogramDenoised"))
        ]
        return out

    @property
    def is_halfset_reconstruction(self) -> bool:
        """Check if the tomogram reconstruction is half-set."""
        return len(self.reconstructed_tomogram) == 2

    @property
    def tomo_pixel_size(self) -> float:
        """Return the pixel size of the tomogram tilt series."""
        if self.tomogram_binning > 0 and self.tomo_tilt_series_pixel_size > 0:
            return self.tomo_tilt_series_pixel_size * self.tomogram_binning
        return -1.0

    @property
    def tomo_shape(self) -> tuple[int, int, int]:
        """Return the shape of the tomogram as (Z, Y, X)."""
        return (self.tomo_size_z, self.tomo_size_y, self.tomo_size_x)

    def read_tomogram(self, rln_dir: Path) -> ArrayFilteredView:
        """Read the reconstructed tomogram from the file."""
        if self.is_halfset_reconstruction:
            return ArrayFilteredView.from_mrc_splits(
                [
                    rln_dir / self.reconstructed_tomogram[0],
                    rln_dir / self.reconstructed_tomogram[1],
                ]
            )
        else:
            return ArrayFilteredView.from_mrc(rln_dir / self.reconstructed_tomogram[0])


class TomogramJobDirectory(HasTomogramsJobDirectory):
    """Class for handling reconstructed tomogram job directories in RELION."""

    _job_type = "relion.reconstructtomograms"

    def tomograms_star(self) -> Path:
        """Return the path to the tomograms star file."""
        return self.path / "tomograms.star"

    def iter_tomogram_info(self) -> Iterator[TomogramInfo]:
        """Iterate over all tilt series info."""
        star = _read_star_as_df(self.tomograms_star())
        for _, row in star.iterrows():
            yield TomogramInfo.from_series(row)


class DenoiseJobDirectory(JobDirectory):
    """Class for handling denoise/predict job directories in RELION."""

    _job_type = "relion.denoisetomo"

    def __init__(self, path: str | Path):
        super().__init__(path)
        self._is_train = self.get_job_param("do_cryocare_train") == "Yes"
        self._is_predict = self.get_job_param("do_cryocare_predict") == "Yes"

    def tomograms_star(self) -> Path:
        """Return the path to the tomograms star file."""
        return self.path / "tomograms.star"

    def iter_tomogram(self) -> Iterator[TomogramInfo]:
        """Iterate over all tilt series info."""
        star = _read_star_as_df(self.tomograms_star())
        for _, row in star.iterrows():
            yield TomogramInfo.from_series_denoised(row)


class PickJobDirectory(JobDirectory):
    """Class for handling particle picking job directories in RELION."""

    _job_type = "relion.picktomo"

    def tomo_and_particles_star(self) -> tuple[Path | None, Path | None]:
        """Return the path to the tomogram and particles star file."""
        try:
            job_pipeline = self.parse_job_pipeline()
        except FileNotFoundError:
            return None, None
        rln_dir = self.relion_project_dir
        if node := job_pipeline.get_input_by_type("TomogramGroupMetadata"):
            tomo_star_path = rln_dir / node.path
        else:
            tomo_star_path = None
        if (path_opt := self.path / "optimisation_set.star").exists():
            opt_set = RelionOptimisationSet.from_file(path_opt)
            particle_star_path = rln_dir / opt_set.particles_star
        elif node_part := job_pipeline.get_input_by_type("ParticleGroupMetadata"):
            particle_star_path = rln_dir / node_part.path
        else:
            particle_star_path = None
        return tomo_star_path, particle_star_path

    def iter_tomogram(self) -> Iterator[TomogramInfo]:
        """Iterate over all tilt series info."""
        tomo_star, particles_star = self.tomo_and_particles_star()
        if tomo_star is None:
            return
        star = _read_star_as_df(tomo_star)
        for _, row in star.iterrows():
            info = TomogramInfo.from_series(row)
            getter = self._make_get_particles(particles_star, row)
            info.get_particles = getter
            yield info

    def _make_get_particles(
        self,
        particles_star: Path,
        row: pd.Series,
    ) -> Callable[[], pd.DataFrame]:
        """Create a function to get particles for a given tomogram."""

        def get_particles() -> pd.DataFrame:
            if particles_star is None:
                cols = [f"rlnCenteredCoordinate{x}Angst" for x in "ZYX"]
                return pd.DataFrame({c: [] for c in cols}, dtype=float)
            else:
                df_particles = _read_star_as_df(particles_star)
                sl = df_particles["rlnTomoName"] == str(row["rlnTomoName"])
                return df_particles[sl].reset_index(drop=True)

        return get_particles


class ExtractJobDirectory(JobDirectory):
    """Class for handling particle extraction job directories in RELION."""

    _job_type = "relion.pseudosubtomo"

    def particles_star(self) -> Path:
        """Return the path to the particles star file."""
        return self.path / "particles.star"

    def particles(self) -> pd.DataFrame:
        """Return the particles DataFrame for this iteration."""
        star_path = self.particles_star()
        return read_star_block(star_path, "particles").trust_loop().to_pandas()

    def is_2d(self) -> bool:
        """Return whether the extraction is 2D stack or 3D subtomogram."""
        return self.get_job_param("do_stack2d") == "Yes"

    def tomo_names(self) -> list[str]:
        """Return the list of tomogram names from the particles star file."""
        return [path.name for path in self.path.joinpath("Subtomograms").iterdir()]

    def max_num_subtomograms(self, tomoname: str) -> int:
        """Return the number of subtomograms for a given tomogram name."""
        tomo_dir = self.path / "Subtomograms" / tomoname
        if self.is_2d():
            suffix = "_stack2d.mrcs"
        else:
            suffix = "_data.mrc"
        ndigits = 1
        while True:
            question_marks = "?" * ndigits
            if next(tomo_dir.glob(f"{question_marks}{suffix}"), None):
                ndigits += 1
            else:
                break
        if ndigits == 1:
            return 0
        path = next(tomo_dir.rglob(f"{'?' * (ndigits - 1)}{suffix}"))
        return int(path.name[: -len(suffix)])

    def iter_subtomogram_paths(
        self,
        tomoname: str,
        indices: list[int],
    ) -> Iterator[tuple[int, Path]]:
        """Iterate over all subtomogram paths for a given tomogram name."""
        tomo_dir = self.path / "Subtomograms" / tomoname
        if self.is_2d():
            suffix = "_stack2d.mrcs"
        else:
            suffix = "_data.mrc"
        for i in indices:
            path = tomo_dir / f"{i}{suffix}"
            yield i, path

    def iter_subtomograms(
        self,
        tomoname: str,
        indices: list[int],
    ) -> Iterator[tuple[int, NDArray[np.floating] | None]]:
        """Iterate over all subtomogram paths for a given tomogram name."""
        for i, path in self.iter_subtomogram_paths(tomoname, indices):
            try:
                with mrcfile.open(path, mode="r") as mrc:
                    yield i, mrc.data
            except Exception:
                yield i, None


@dataclass
class _3DResultsBase:
    path: Path
    it_str: str

    @classmethod
    def from_niter(cls, path: Path, niter: int) -> Self:
        """Create an instance from a path and iteration number."""
        it_str = f"_it{niter:03d}"
        return cls(path=path, it_str=it_str)

    # def angdist(self, class_id: int) -> list[np.ndarray]:
    #     """Return the angular distribution for a given class ID."""
    #     if self.it_str == "":
    #         paths = [f"run_class{class_id:03d}_angdist.bild"]
    #     else:
    #         paths = [
    #             f"run{self.it_str}_half1_class{class_id:03d}_angdist.bild",
    #             f"run{self.it_str}_half2_class{class_id:03d}_angdist.bild",
    #         ]
    #     angdist = []
    #     for path in paths:
    #         full_path = self.path / path
    #         with open(full_path, "r") as f:
    #             color = f.readline()
    #             cylinder = f.readline()

    #         angdist.append(data)

    def particles(self) -> pd.DataFrame:
        """Return the particles DataFrame for this iteration."""
        star_path = self._data_star()
        return read_star_block(star_path, "particles").trust_loop().to_pandas()

    def _data_star(self) -> Path:
        """Return the path to the data star file for this iteration."""
        return self.path / f"run{self.it_str}_data.star"

    def _optimisation_set_star(self) -> Path:
        """Return the path to the optimisation set star file for this iteration."""
        return self.path / f"run{self.it_str}_optimisation_set.star"

    def _optimiser_star(self) -> Path:
        """Return the path to the optimiser star file for this iteration."""
        return self.path / f"run{self.it_str}_optimiser.star"

    def _sampling_star(self) -> Path:
        """Return the path to the sampling star file for this iteration."""
        return self.path / f"run{self.it_str}_sampling.star"


@dataclass
class InitialModelResults(_3DResultsBase):
    def class_map(self, class_id: int) -> NDArray[np.floating]:
        """Return the 3D map for a given class ID."""
        mrc_path = self.path / f"run{self.it_str}_class{class_id + 1:03d}.mrc"
        with mrcfile.open(mrc_path, mode="r") as mrc:
            return mrc.data


class InitialModel3DJobDirectory(JobDirectory):
    """Class for handling initial model 3D job directories in RELION."""

    _job_type = "relion.initialmodel.tomo"

    def initial_model_map(self) -> NDArray[np.floating]:
        """Return the image of the initial model."""
        path = self.path / "initial_model.mrc"
        with mrcfile.open(path, mode="r") as mrc:
            return mrc.data

    def get_class_mrc(self, niter: int) -> list[Path]:
        name = f"run_it{niter:03d}_class"
        return list(self.path.glob(f"{name}*.mrc"))

    def get_optimisation_set_star(self, niter: int) -> Path:
        """Return the path to the optimisation set star file for a given iteration."""
        return self.path / f"run_it{niter:03d}_optimisation_set.star"

    def get_result(self, niter: int) -> InitialModelResults:
        return InitialModelResults.from_niter(self.path, niter)

    def num_classes(self) -> int:
        """Return the number of classes."""
        return len(list(self.path.glob("run_it000_class*.mrc")))

    def niter_list(self) -> list[int]:
        """Return the list of number of iterations."""
        nums: list[int] = []
        for path in self.path.glob("run_it*_data.star"):
            value = int(path.stem[6:-5])
            nums.append(value)
        return sorted(nums)


@dataclass
class Refine3DResults(_3DResultsBase):
    def refined_map(self, class_id: int) -> NDArray[np.floating]:
        """Return the refined map for a given class ID."""
        mrc_path = self.path / f"run_class{class_id + 1:03d}.mrc"
        with mrcfile.open(mrc_path, mode="r") as mrc:
            return mrc.data

    def halfmaps(
        self, class_id: int
    ) -> tuple[NDArray[np.floating] | None, NDArray[np.floating] | None]:
        """Return the half maps for a given class ID."""
        half1_path = self._half_class_mrc(class_id + 1, 1)
        half2_path = self._half_class_mrc(class_id + 1, 2)
        try:
            with mrcfile.open(half1_path, mode="r") as mrc1:
                img1 = mrc1.data
        except Exception:
            img1 = None
        try:
            with mrcfile.open(half2_path, mode="r") as mrc2:
                img2 = mrc2.data
        except Exception:
            img2 = None
        return img1, img2

    def model_dataframe(
        self, class_id: int = 1
    ) -> tuple[pd.DataFrame | None, pd.DataFrame | None]:
        starpath = self.path / f"run{self.it_str}_half1_model.star"
        if not starpath.exists():
            return None, None
        star = read_star(starpath)
        df_fsc = star[f"model_class_{class_id}"].to_pandas()
        df_groups = star["model_groups"].to_pandas()
        # df_groups example:
        # rlnGroupNumber rlnGroupName  rlnGroupNrParticles  rlnGroupScaleCorrection
        #   1             TS_01            931                 0.998775
        #   2             TS_03            914                 1.016683
        return df_fsc, df_groups

    # def angdist(self, class_id: int) -> list[np.ndarray]:
    #     """Return the angular distribution for a given class ID."""
    #     if self.it_str == "":
    #         paths = [f"run_class{class_id:03d}_angdist.bild"]
    #     else:
    #         paths = [
    #             f"run{self.it_str}_half1_class{class_id:03d}_angdist.bild",
    #             f"run{self.it_str}_half2_class{class_id:03d}_angdist.bild",
    #         ]
    #     angdist = []
    #     for path in paths:
    #         full_path = self.path / path
    #         with open(full_path, "r") as f:
    #             color = f.readline()
    #             cylinder = f.readline()

    #         angdist.append(data)

    def _half_class_mrc(self, class_id: int, num: Literal[1, 2] = 1) -> Path:
        """Return the path to the half 1 class MRC file for this iteration."""
        if self.it_str == "":
            suffix = "_unfil"
        else:
            suffix = ""
        name = f"run{self.it_str}_half{num}_class{class_id:03d}{suffix}.mrc"
        return self.path / name

    def _half_class_angdist_bild(self, class_id: int, num: Literal[1, 2] = 1) -> Path:
        """Return the path to the half 1 class angular distribution BILD file for this iteration."""
        # f"run{self.it_str}_class{class_id:03d}_angdist.bild"
        return (
            self.path / f"run{self.it_str}_half{num}_class{class_id:03d}_angdist.bild"
        )

    def _half_model_star(self, class_id: int, num: Literal[1, 2] = 1) -> Path:
        """Return the path to the half 1 model star file for this iteration."""
        return self.path / f"run{self.it_str}_half{num}_model_class{class_id:03d}.star"


class Refine3DJobDirectory(JobDirectory):
    """Class for handling refine 3D job directories in RELION."""

    _job_type = "relion.refine3d.tomo"

    def refined_model_mrc(self) -> list[Path]:
        """Return the path to the refined model image."""
        return list(self.path.glob("run_class*.mrc"))

    def get_result(self, niter: int) -> Refine3DResults:
        return Refine3DResults.from_niter(self.path, niter)

    def get_final_result(self) -> Refine3DResults:
        """Return the final result of the refine 3D job."""
        return Refine3DResults(self.path, "")

    def num_classes(self) -> int:
        """Return the number of classes in the refine 3D job."""
        return len(list(self.path.glob("run_it000_half1_model*.star")))

    def num_iters(self) -> int:
        """Return the number of iterations in the refine 3D job."""
        return len(list(self.path.glob("run_it*_data.star")))


class Class3DResults(_3DResultsBase):
    def class_map(self, class_id: int) -> NDArray[np.floating]:
        """Return the class 3D map for a given class ID."""
        mrc_path = self.path / f"run{self.it_str}_class{class_id + 1:03d}.mrc"
        with mrcfile.open(mrc_path, mode="r") as mrc:
            return mrc.data

    def value_ratio(self) -> dict[int, float]:
        counts = self.particles()["rlnClassNumber"].value_counts().sort_index()
        ratio = counts / counts.sum()
        return {num: ratio.get(num, 0.0) for num in range(1, len(ratio) + 1)}

    def summary_dataframe(self) -> pd.DataFrame | None:
        starpath = self.path / f"run{self.it_str}_model.star"
        try:
            block = read_star_block(starpath, "model_classes")
            return block.trust_loop().to_pandas()
        except Exception as e:
            _LOGGER.warning(f"Failed to read FSC data from {starpath}: {e}")
            return None

    def fsc_dataframe(self, class_id: int) -> pd.DataFrame | None:
        starpath = self.path / f"run{self.it_str}_model.star"
        try:
            block = read_star_block(starpath, f"model_class_{class_id}")
            return block.trust_loop().to_pandas()
        except Exception as e:
            _LOGGER.warning(f"Failed to read FSC data from {starpath}: {e}")
            return None


class Class3DJobDirectory(JobDirectory):
    """Class for handling class 3D job directories in RELION."""

    _job_type = "relion.class3d"

    def class_3d_mrc(self) -> list[Path]:
        """Return the path to the class 3D model image."""
        return list(self.path.glob("run_class*.mrc"))

    def get_result(self, niter: int) -> Class3DResults:
        return Class3DResults.from_niter(self.path, niter)

    def iter_results(self) -> Iterator[Class3DResults]:
        """Iterate over all class 3D results."""
        for niter in range(1, 1000000):
            try:
                yield self.get_result(niter)
            except FileNotFoundError:
                break

    def num_classes(self) -> int:
        """Return the current number of classes in the class 3D job."""
        return len(list(self.path.glob("run_it000_class*.mrc")))

    def num_iters(self) -> int:
        """Return the number of iterations in the class 3D job."""
        return len(list(self.path.glob("run_it*_model.star")))


class ReconstructParticlesJobDirectory(JobDirectory):
    """Class for handling reconstruct particles job directories in RELION."""

    _job_type = "relion.reconstructparticletomo"

    def merged_mrc(self) -> NDArray[np.floating] | None:
        """Return the path to the merged MRC file if exists."""
        path = self.path / "merged.mrc"
        try:
            with mrcfile.open(path, mode="r") as mrc:
                return mrc.data
        except Exception:
            return None


class MaskCreateJobDirectory(JobDirectory):
    """Class for handling mask creation job directories in RELION."""

    _job_type = "relion.maskcreate"

    def mask_mrc(self) -> NDArray[np.floating] | None:
        """Return the mask MRC file."""
        mask_path = self.path / "mask.mrc"
        try:
            with mrcfile.open(mask_path, mode="r") as mrc:
                return mrc.data
        except Exception:
            return None


class PostProcessJobDirectory(JobDirectory):
    """Class for handling post-processing job directories in RELION."""

    _job_type = "relion.postprocess"

    def map_mrc_path(self, masked: bool = False) -> Path:
        """Return the path to the post-processed map MRC file."""
        name = "postprocess_masked.mrc" if masked else "postprocess.mrc"
        return self.path / name

    def map_mrc(self, masked: bool = False) -> NDArray[np.floating] | None:
        """Return the post-processed map MRC file."""
        mrc_path = self.map_mrc_path(masked=masked)
        if mrc_path.exists():
            with mrcfile.open(mrc_path, mode="r") as mrc:
                return mrc.data

    def fsc_dataframe(self) -> pd.DataFrame | None:
        """Return the FSC DataFrame."""
        star_path = self.path / "postprocess.star"
        if star_path.exists():
            return read_star_block(star_path, "fsc").trust_loop().to_pandas()


class SelectInteractiveJobDirectory(JobDirectory):
    _job_type = "relion.select.interactive"

    def particles_star(self) -> Path:
        """Return the path to the particles star file."""
        return self.path / "particles.star"

    def particles_pre_star(self) -> Path:
        """Return the path to the pre-selection particles star file."""
        path_opt_star = self._opt_star()
        opt_dict = read_star(path_opt_star).first().trust_single().to_dict()
        return self.relion_project_dir / opt_dict["rlnTomoParticlesFile"]

    def is_selected_array(self) -> NDArray[np.bool_] | None:
        try:
            df = _read_star_as_df(self.path / "backup_selection.star")
            return df["rlnSelected"].to_numpy(dtype=np.bool_)
        except Exception:
            return None

    def class_map_paths(self, num_classes: int) -> list[Path | None]:
        """Return the paths to the class maps."""
        path_opt_star = self._opt_star()
        # path_opt_star is something like .../run_it0XX_optimisation_set.star
        nchars = len("optimisation_set")
        mrc_paths = []
        prefix = path_opt_star.stem[:-nchars]
        for i in range(num_classes):
            path = (
                self.relion_project_dir
                / path_opt_star.parent
                / (prefix + f"class{i + 1:0>3}.mrc")
            )
            if path.exists():
                mrc_paths.append(path)
            else:
                mrc_paths.append(None)
        return mrc_paths

    def _opt_star(self):
        b_in = read_star_block(self.path / "job_pipeline.star", "pipeline_input_edges")
        df = b_in.trust_loop().to_pandas()
        optimizer_star_path = Path(df["rlnPipeLineEdgeFromNode"].iloc[0])
        new_stem = optimizer_star_path.stem[: -len("optimiser")] + "optimisation_set"
        return optimizer_star_path.parent / (new_stem + ".star")


class RemoveDuplicatesJobDirectory(JobDirectory):
    _job_type = "relion.select.removeduplicates"

    def particles_star(self) -> Path:
        """Return the path to the particles star file."""
        return self.path / "particles.star"

    def particles_removed_star(self) -> Path:
        """Return the path to the particles_removed star file."""
        return self.path / "particles_removed.star"


class SplitParticlesJobDirectory(JobDirectory):
    _job_type = "relion.select.split"

    def iter_particles_stars(self) -> Iterator[Path]:
        """Iterate over all particles star files."""
        path_ith_list: list[tuple[Path, int]] = []
        num = len("particles_split")
        for path in self.path.glob("particles_split*.star"):
            ith = int(path.stem[num:])
            path_ith_list.append((path, ith))
        path_ith_list.sort(key=lambda x: x[1])
        for path, _ in path_ith_list:
            yield path


class CtfRefineTomoJobDirectory(HasTiltSeriesJobDirectory):
    """Class for handling CTF refinement job directories in RELION."""

    _job_type = "relion.ctfrefinetomo"


class FrameAlignTomoJobDirectory(JobDirectory):
    """Class for handling frame alignment job directories in RELION."""

    _job_type = "relion.framealigntomo"


# class JoinStarJobDirectory(JobDirectory):
#     """Class for handling join star job directories in RELION."""

#     _job_type = "relion.joinstar.particles"

#     def output_star(self) -> Path:
#         """Return the path to the output star file."""
#         return self.path / "output.star"


def _read_star_as_df(star_path: Path) -> pd.DataFrame:
    return read_star(star_path).first().trust_loop().to_pandas()
