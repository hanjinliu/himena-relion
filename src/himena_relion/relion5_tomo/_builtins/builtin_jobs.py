from abc import abstractmethod
import subprocess
import tempfile
from typing import Annotated, Any
from pathlib import Path

from uuid import uuid4

import starfile
from himena_relion.consts import JOB_ID_MAP
from himena_relion._job_class import RelionJob, connect_jobs, to_string
from himena_relion._utils import last_job_directory
from himena_relion import _configs

TILTSERIES_TYPE = Annotated[str, {"label": "Tilt series", "group": "I/O"}]

MPI_TYPE = Annotated[
    int,
    {"label": "Number of MPI processes", "min": 1, "max": 64, "group": "Running"},
]
THREAD_TYPE = Annotated[
    int,
    {"label": "Number of threads", "min": 1, "max": 64, "group": "Running"},
]
DO_QUEUE_TYPE = Annotated[
    bool,
    {"label": "Submit to queue", "group": "Running"},
]
MIN_DEDICATED_TYPE = Annotated[
    int,
    {
        "label": "Minimum dedicated cores per node",
        "min": 1,
        "max": 64,
        "group": "Running",
    },
]


class _RelionBuiltinJob(RelionJob):
    @classmethod
    @abstractmethod
    def type_label(cls) -> str:
        """Get the type label for this builtin job."""

    @classmethod
    def command_id(cls) -> str:
        return cls.type_label()

    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        """Normalize the keyword arguments for this job."""
        kwargs.update(_configs.get_queue_dict())
        return kwargs

    @classmethod
    def job_title(cls) -> str:
        return JOB_ID_MAP.get(cls.type_label(), "Unknown")

    @classmethod
    def himena_model_type(cls):
        return cls.command_id()

    @classmethod
    def create_and_run_job(cls, **kwargs) -> str:
        kwargs_normed = cls.normalize_kwargs(**kwargs)
        star = prep_builtin_job_star(
            type_label=cls.type_label(),
            kwargs=kwargs_normed,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            job_star_path = tmpdir / f"{uuid4()}.star"
            starfile.write(star, job_star_path)
            subprocess.run(
                [
                    "relion_pipeliner",
                    "--addJobFromStar",
                    str(job_star_path),
                ]
            )
        d = last_job_directory()
        subprocess.Popen(["relion_pipeliner", "--RunJobs", d])
        return d


def prep_builtin_job_star(
    type_label: str, is_tomo: int = 0, kwargs: dict[str, Any] = {}
):
    job = {
        "rlnJobTypeLabel": type_label,
        "rlnJobIsContinue": 0,
        "rlnJobIsTomo": is_tomo,
    }
    _var = []
    _val = []
    for k, v in kwargs.items():
        _var.append(k)
        _val.append(to_string(v))
    joboptions_values = {
        "rlnJobOptionVariable": _var,
        "rlnJobOptionValue": _val,
    }
    return {
        "job": job,
        "joboptions": joboptions_values,
    }


class _AlignTiltSeriesJobBase(_RelionBuiltinJob):
    @classmethod
    def type_label(cls) -> str:
        return "relion.aligntiltseries"

    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        kwargs["fn_aretomo_exe"] = _configs.get_aretomo2_exe()
        kwargs["fn_batchtomo_exe"] = _configs.get_batchruntomo_exe()
        return super().normalize_kwargs(**kwargs)


class AlignTiltSeriesImodFiducial(_AlignTiltSeriesJobBase):
    @classmethod
    def command_id(cls):
        return super().command_id() + "-imodfiducial"

    @classmethod
    def job_title(cls) -> str:
        return "Align Tilt Series (IMOD Fiducials)"

    @classmethod
    def normalize_kwargs(cls, **kwargs):
        kwargs["do_imod_fiducials"] = True
        kwargs["do_aretomo2"] = False
        kwargs["do_imod_patchtrack"] = False
        kwargs["gui_ids"] = ""
        return super().normalize_kwargs(**kwargs)

    def run(
        self,
        in_tiltseries: TILTSERIES_TYPE = "",
        fiducial_diameter: Annotated[float, {"label": "Fiducial diameter (nm)"}] = 10.0,
        nr_mpi: MPI_TYPE = 1,
        do_queue: DO_QUEUE_TYPE = False,
        min_dedicated: MIN_DEDICATED_TYPE = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class AlignTiltSeriesImodPatch(_AlignTiltSeriesJobBase):
    @classmethod
    def command_id(cls):
        return super().command_id() + "-imodpatch"

    @classmethod
    def job_title(cls) -> str:
        return "Align Tilt Series (IMOD Patch Tracking)"

    @classmethod
    def normalize_kwargs(cls, **kwargs):
        kwargs["do_imod_fiducials"] = False
        kwargs["do_aretomo2"] = False
        kwargs["do_imod_patchtrack"] = True
        kwargs["gui_ids"] = ""
        return super().normalize_kwargs(**kwargs)

    def run(
        self,
        in_tiltseries: TILTSERIES_TYPE = "",
        patch_size: Annotated[float, {"label": "Patch size (nm)", "min": 1}] = 100,
        patch_overlap: Annotated[
            float, {"label": "Patch overlap (%)", "min": 0, "max": 100}
        ] = 50,
        nr_mpi: MPI_TYPE = 1,
        do_queue: DO_QUEUE_TYPE = False,
        min_dedicated: MIN_DEDICATED_TYPE = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class AlignTiltSeriesAreTomo2(_AlignTiltSeriesJobBase):
    @classmethod
    def command_id(cls):
        return super().command_id() + "-aretomo2"

    @classmethod
    def job_title(cls) -> str:
        return "Align Tilt Series (AreTomo2)"

    @classmethod
    def normalize_kwargs(cls, **kwargs):
        kwargs["do_imod_fiducials"] = False
        kwargs["do_aretomo2"] = True
        kwargs["do_imod_patchtrack"] = False
        return super().normalize_kwargs(**kwargs)

    def run(
        self,
        in_tiltseries: TILTSERIES_TYPE = "",
        do_aretomo_tiltcorrect: Annotated[
            bool, {"label": "Correct tilt angle offset"}
        ] = False,
        aretomo_tiltcorrect_angle: Annotated[int, {"label": "Tilt angle offset"}] = 999,
        do_aretomo_ctf: Annotated[bool, {"label": "Estimate CTF"}] = False,
        do_aretomo_phaseshift: Annotated[
            bool, {"label": "Estimate phase shift"}
        ] = False,
        other_aretomo_args: Annotated[str, {"label": "Other AreTomo2 arguments"}] = "",
        gpu_ids: Annotated[str, {"label": "GPU IDs"}] = "",
        nr_mpi: MPI_TYPE = 1,
        do_queue: DO_QUEUE_TYPE = False,
        min_dedicated: MIN_DEDICATED_TYPE = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class ReconstructTomogramJob(_RelionBuiltinJob):
    @classmethod
    def type_label(cls) -> str:
        return "relion.reconstructtomograms"

    @classmethod
    def normalize_kwargs(cls, **kwargs):
        # kwargs["tomo_name"] = " ".join(kwargs["tomo_name"]) ???
        return super().normalize_kwargs(**kwargs)

    def run(
        self,
        # Tab 1: I/O
        in_tiltseries: TILTSERIES_TYPE = "",
        generate_split_tomograms: Annotated[
            bool, {"label": "Split tomograms", "group": "I/O"}
        ] = False,
        do_proj: Annotated[
            bool, {"label": "Write 2D projection", "group": "I/O"}
        ] = False,
        centre_proj: Annotated[
            int, {"label": "Central Z-slice (binned pix)", "group": "I/O"}
        ] = 0,
        thickness_proj: Annotated[
            int, {"label": "Number of Z-slices (binned pix)", "group": "I/O"}
        ] = 10,
        # Tab 2: Reconstruct
        xdim: Annotated[
            int, {"label": "Tomogram X size (unbinned pix)", "group": "Reconstruct"}
        ] = 4000,
        ydim: Annotated[
            int, {"label": "Tomogram Y size (unbinned pix)", "group": "Reconstruct"}
        ] = 4000,
        zdim: Annotated[
            int, {"label": "Tomogram Z size (unbinned pix)", "group": "Reconstruct"}
        ] = 2000,
        binned_angpix: Annotated[
            float, {"label": "Pixel size (A)", "group": "Reconstruct"}
        ] = 10.0,
        tiltangle_offset: Annotated[
            float, {"label": "Tilt angle offset (deg)", "group": "Reconstruct"}
        ] = 0.0,
        tomo_name: Annotated[
            str, {"label": "Reconstruct only this tomogram", "group": "Reconstruct"}
        ] = "",
        do_fourier: Annotated[
            bool,
            {"label": "Fourier-inversion with odd/even frames", "group": "Reconstruct"},
        ] = True,
        ctf_intact_first_peak: Annotated[
            bool, {"label": "Ignore CTFs until first peaks", "group": "Reconstruct"}
        ] = True,
        # Tab 3: Running
        nr_mpi: MPI_TYPE = 1,
        nr_threads: THREAD_TYPE = 1,
        do_queue: DO_QUEUE_TYPE = False,
        min_dedicated: MIN_DEDICATED_TYPE = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


connect_jobs(
    AlignTiltSeriesImodFiducial,
    ReconstructTomogramJob,
    node_mapping={"aligned_tilt_series.star": "in_tiltseries"},
)
