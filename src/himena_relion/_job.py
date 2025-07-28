from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, Literal, TYPE_CHECKING
import numpy as np
from numpy.typing import NDArray
import pandas as pd
import starfile
import mrcfile
from himena_relion.consts import RelionJobState

if TYPE_CHECKING:
    from typing import Self


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
        job_type = starfile.read(fp)["job"]["rlnJobTypeLabel"]
        cls = JobDirectory._type_map.get(job_type, JobDirectory)
        job_dir = fp.parent
        return cls(job_dir)

    def job_star(self) -> Path:
        """Return the path to the job.star file."""
        return self.path / "job.star"

    def run_out(self) -> Path:
        """Return the path to the job's run output log file."""
        return self.path / "run.out"

    def run_err(self) -> Path:
        """Return the path to the job's run error log file."""
        return self.path / "run.err"

    def job_pipeline(self) -> Path:
        """Return the path to the job's pipeline control file."""
        return self.path / "job_pipeline.star"

    def default_pipeline(self) -> Path:
        """Return the default pipeline control file."""
        return self.path / "default_pipeline.star"

    def note(self) -> Path:
        """Return the path to the job's note file."""
        return self.path / "note.txt"

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
            return RelionJobState.ELSE


@dataclass
class TiltSeriesInfo:
    tomo_name: str
    tomo_tilt_series_star_file: Path
    voltage: float = -1.0
    spherical_abberation: float = -1.0
    amplitude_contrast: float = -1.0
    micrograph_original_pixel_size: float = -1.0
    tomo_hand: Literal[1, -1] = 1

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


class ImportJobDirectory(JobDirectory):
    """Class for handling import job directories in RELION."""

    _job_type = "relion.importtomo"

    def tilt_series_star(self) -> Path:
        """Return the path to the tilt series star file."""
        return self.path / "tilt_series.star"

    def iter_tilt_series(self) -> Iterator[TiltSeriesInfo]:
        """Iterate over all tilt series info."""
        star = starfile.read(self.tilt_series_star())
        if not isinstance(star, pd.DataFrame):
            raise TypeError(f"Expected a DataFrame, got {type(star)}")
        for _, row in star.iterrows():
            yield TiltSeriesInfo.from_series(row)


@dataclass
class CorrectedTiltSeriesInfo(TiltSeriesInfo):
    tomo_tilt_series_pixel_size: float = -1.0

    @classmethod
    def from_series(cls, series: pd.Series) -> Self:
        """Create a CorrectedTiltSeriesInfo instance from a pandas Series."""
        out = super().from_series(series)
        out.tomo_tilt_series_pixel_size = series.get("rlnTomoTiltSeriesPixelSize", -1.0)
        return out


class MotionCorrectionJobDirectory(JobDirectory):
    """Class for handling motion correction job directories in RELION."""

    _job_type = "relion.motioncorr.own"

    def corrected_tilt_series_star(self) -> Path:
        """Return the path to the motion-corrected tilt series star file."""
        return self.path / "corrected_tilt_series.star"

    def iter_corrected_tilt_series(self) -> Iterator[CorrectedTiltSeriesInfo]:
        """Iterate over all motion correction info."""
        star = starfile.read(self.corrected_tilt_series_star())
        if not isinstance(star, pd.DataFrame):
            raise TypeError(f"Expected a DataFrame, got {type(star)}")
        for _, row in star.iterrows():
            yield CorrectedTiltSeriesInfo.from_series(row)


# _rlnTomoTiltMovieFrameCount #1
# _rlnTomoNominalStageTiltAngle #2
# _rlnTomoNominalTiltAxisAngle #3
# _rlnMicrographPreExposure #4
# _rlnTomoNominalDefocus #5
# _rlnCtfPowerSpectrum #6
# _rlnMicrographNameEven #7
# _rlnMicrographNameOdd #8
# _rlnMicrographMetadata #9
# _rlnAccumMotionTotal #10
# _rlnAccumMotionEarly #11
# _rlnAccumMotionLate #12
# _rlnCtfImage #13
# _rlnDefocusU #14
# _rlnDefocusV #15
# _rlnCtfAstigmatism #16
# _rlnDefocusAngle #17
# _rlnCtfFigureOfMerit #18
# _rlnCtfMaxResolution #19
class CtfCorrectionJobDirectory(JobDirectory):
    """Class for handling CTF correction job directories in RELION."""

    _job_type = "relion.ctffind.ctffind4"

    def tilt_series_ctf_star(self) -> Path:
        """Return the path to the CTF-corrected tilt series star file."""
        return self.path / "tilt_series_ctf.star"

    def iter_tilt_series_ctf(self) -> Iterator[CorrectedTiltSeriesInfo]:
        """Iterate over all CTF-corrected tilt series info."""
        star = starfile.read(self.tilt_series_ctf_star())
        if not isinstance(star, pd.DataFrame):
            raise TypeError(f"Expected a DataFrame, got {type(star)}")
        for _, row in star.iterrows():
            yield CorrectedTiltSeriesInfo.from_series(row)


@dataclass
class SelectedTiltSeriesInfo(CorrectedTiltSeriesInfo):
    tilt_series_star_file: Path = Path("")

    @classmethod
    def from_series(cls, series: pd.Series) -> Self:
        """Create a SelectedTiltSeriesInfo instance from a pandas Series."""
        out = super().from_series(series)
        out.tilt_series_star_file = Path(series.get("rlnTomoTiltSeriesStarFile", ""))
        return out


class ExcludeTiltSeriesJobDirectory(JobDirectory):
    """Class for handling exclude tilt series job directories in RELION."""

    _job_type = "relion.excludetilts"

    def selected_tilt_series_star(self) -> Path:
        """Return the path to the selected tilt series star file."""
        return self.path / "selected_tilt_series.star"

    def iter_excluded_tilt_series(self) -> Iterator[SelectedTiltSeriesInfo]:
        """Iterate over all excluded tilt series info."""
        star = starfile.read(self.selected_tilt_series_star())
        if not isinstance(star, pd.DataFrame):
            raise TypeError(f"Expected a DataFrame, got {type(star)}")
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


class AlignTiltSeriesJobDirectory(JobDirectory):
    """Class for handling align tilt series job directories in RELION."""

    _job_type = "relion.aligntiltseries"

    def aligned_tilt_series_star(self) -> Path:
        """Return the path to the aligned tilt series star file."""
        return self.path / "aligned_tilt_series.star"

    def iter_aligned_tilt_series(self) -> Iterator[AlignedTiltSeriesInfo]:
        """Iterate over all aligned tilt series info."""
        star = starfile.read(self.aligned_tilt_series_star())
        if not isinstance(star, pd.DataFrame):
            raise TypeError(f"Expected a DataFrame, got {type(star)}")
        for _, row in star.iterrows():
            yield AlignedTiltSeriesInfo.from_series(row)


@dataclass
class TomogramInfo(AlignedTiltSeriesInfo):
    tomogram_binning: float = -1.0
    tomo_size_x: int = -1
    tomo_size_y: int = -1
    tomo_size_z: int = -1
    reconstructed_tomogram: list[Path] = field(default_factory=list)

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

    def read_tomogram(self) -> NDArray[np.floating]:
        """Read the reconstructed tomogram from the file."""
        image = 0
        for path in self.reconstructed_tomogram:
            if path.exists():
                with mrcfile.open(path, mode="r") as mrc:
                    image += mrc.data
        if image == 0:
            raise FileNotFoundError(
                f"Reconstructed tomogram not found in {self.reconstructed_tomogram}"
            )
        return image


class TomogramJobDirectory(JobDirectory):
    """Class for handling reconstructed tomogram job directories in RELION."""

    _job_type = "relion.reconstructtomograms"

    def tomograms_star(self) -> Path:
        """Return the path to the tomograms star file."""
        return self.path / "tomograms.star"

    def iter_tomogram(self) -> Iterator[TomogramInfo]:
        """Iterate over all tilt series info."""
        star = starfile.read(self.tomograms_star())
        if not isinstance(star, pd.DataFrame):
            raise TypeError(f"Expected a DataFrame, got {type(star)}")
        for _, row in star.iterrows():
            yield TomogramInfo.from_series(row)


@dataclass
class _3DResultsBase:
    path: Path
    it_str: str

    def __post_init__(self):
        if not self._data_star().exists():
            raise FileNotFoundError(f"Results for iteration {self.it_str} not found")

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
        return starfile.read(star_path)["particles"]

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
        return len(list(self.path.glob("run_it000_class*.star")))

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
    ) -> tuple[NDArray[np.floating], NDArray[np.floating]]:
        """Return the half maps for a given class ID."""
        half1_path = self._half_class_mrc(class_id, 1)
        half2_path = self._half_class_mrc(class_id, 2)
        with mrcfile.open(half1_path, mode="r") as mrc1:
            img1 = mrc1.data
        with mrcfile.open(half2_path, mode="r") as mrc2:
            img2 = mrc2.data
        return img1, img2

    def fsc_dataframe(self, class_id: int) -> pd.DataFrame:
        _dict = starfile.read(f"run{self.it_str}_half1_model.star")
        return _dict[f"model_class_{class_id}"]

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

    def iter_results(self) -> Iterator[Refine3DResults]:
        """Iterate over all refine 3D results."""
        for niter in range(1, 1000000):
            try:
                yield self.get_result(niter)
            except FileNotFoundError:
                break

    def get_final_result(self) -> Refine3DResults:
        """Return the final result of the refine 3D job."""
        return Refine3DResults(self.path, "")

    def num_classes(self) -> int:
        """Return the number of classes in the refine 3D job."""
        return len(list(self.path.glob("run_it000_half1_model*.star")))

    def num_iters(self) -> int:
        """Return the number of iterations in the refine 3D job."""
        return len(list(self.path.glob("run_it*_half1_model_class001.star")))


class Class3DResults(_3DResultsBase):
    def class_map(self, class_id: int) -> NDArray[np.floating]:
        """Return the class 3D map for a given class ID."""
        mrc_path = self.path / f"run{self.it_str}_class{class_id + 1:03d}.mrc"
        with mrcfile.open(mrc_path, mode="r") as mrc:
            return mrc.data

    def value_ratio(self, num_classes: int) -> dict[int, float]:
        counts = self.particles()["rlnClassNumber"].value_counts().sort_index()
        ratio = counts / counts.sum()
        return {num: ratio.get(num, 0.0) for num in range(1, num_classes + 1)}


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
