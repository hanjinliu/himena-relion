from pathlib import Path
from typing import Any

from himena_relion._job_class import _Relion5BuiltinJob, parse_string
from himena_relion import _configs
from himena_relion._pipeline import RelionPipeline
from himena_relion import _annotated as _a
from himena_relion.relion5._builtins import (
    CtfEstimationJob,
    Class3DNoAlignmentJob,
    Class3DJob,
    MotionCorr2Job,
    MotionCorrOwnJob,
    PostProcessJob,
    InitialModelJob,
    Refine3DJob,
)


def norm_optim(**kwargs):
    optim = kwargs.pop("in_optim", {})
    kwargs["in_optimisation"] = optim.get("in_optimisation", "")
    kwargs["use_direct_entries"] = parse_string(
        optim.get("use_direct_entries", False), bool
    )
    kwargs["in_particles"] = optim.get("in_particles", "")
    kwargs["in_tomograms"] = optim.get("in_tomograms", "")
    kwargs["in_trajectories"] = optim.get("in_trajectories", "")
    if "sigma_tilt" in kwargs and kwargs["sigma_tilt"] is None:
        kwargs["sigma_tilt"] = -1.0
    return kwargs


def norm_optim_inv(**kwargs):
    if "in_optim" not in kwargs:
        kwargs["in_optim"] = {
            "in_optimisation": kwargs.pop("in_optimisation", ""),
            "use_direct_entries": kwargs.pop("use_direct_entries", False),
            "in_particles": kwargs.pop("in_particles", ""),
            "in_tomograms": kwargs.pop("in_tomograms", ""),
            "in_trajectories": kwargs.pop("in_trajectories", ""),
        }
    if "sigma_tilt" in kwargs and float(kwargs["sigma_tilt"]) < 0:
        kwargs["sigma_tilt"] = None
    return kwargs


class _Relion5TomoJob(_Relion5BuiltinJob):
    @classmethod
    def command_palette_title_prefix(cls):
        return "RELION 5 Tomo:"

    @classmethod
    def command_id(cls):
        return super().command_id() + ".tomo"

    @classmethod
    def job_is_tomo(cls) -> bool:
        return True


class _ImportTomoOrCoordsJob(_Relion5TomoJob):
    @classmethod
    def type_label(cls) -> str:
        return "relion.importtomo"

    @classmethod
    def job_is_tomo(cls):
        return False


class _ImportTomoJob(_ImportTomoOrCoordsJob):
    @classmethod
    def normalize_kwargs(cls, **kwargs):
        kwargs = super().normalize_kwargs(**kwargs)
        kwargs["do_coords"] = False
        dose = kwargs.pop("dose_rate_value", {})
        kwargs["dose_rate"] = dose.pop("dose_rate", 5.0)
        kwargs["dose_is_per_movie_frame"] = dose.pop("dose_is_per_movie_frame", False)
        kwargs["in_coords"] = ""
        kwargs["remove_substring"] = ""
        kwargs["remove_substring2"] = ""
        kwargs["is_center"] = False
        kwargs["scale_factor"] = 1.0
        kwargs["add_factor"] = 0.0
        kwargs["do_queue"] = False
        return kwargs

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs):
        kwargs = super().normalize_kwargs_inv(**kwargs)
        kwargs["dose_rate_value"] = {
            "dose_is_per_movie_frame": kwargs.pop("dose_is_per_movie_frame", False),
            "dose_rate": kwargs.pop("dose_rate", 5.0),
        }
        for name in [
            "in_coords", "do_queue", "remove_substring2", "is_center", "scale_factor",
            "do_coords", "add_factor", "remove_substring", "images_are_motion_corrected"
        ]:  # fmt: skip
            kwargs.pop(name, None)
        return kwargs

    def run(
        self,
        # General
        movie_files: _a.import_.MOVIE_FILES = "frames/*.mrc",
        mdoc_files: _a.import_.MDOC_FILES = "mdoc/*.mdoc",
        optics_group_name: _a.import_.OPTICS_GROUP_NAME = "",
        prefix: _a.import_.PREFIX = "",
        angpix: _a.import_.ANGPIX = 0.675,
        kV: _a.import_.KV = 300,
        Cs: _a.import_.CS = 2.7,
        Q0: _a.import_.Q0 = 0.1,
        # Tilt series
        dose_rate_value: _a.import_.DOSE_RATE_VALUE = None,
        tilt_axis_angle: _a.import_.TILT_AXIS_ANGLE = 85,
        mtf_file: _a.import_.FN_MTF = "",
        flip_tiltseries_hand: _a.import_.FLIP_TILTSERIES_HAND = True,
        # Running
        min_dedicated: _a.running.MIN_DEDICATED = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class ImportTomoJob(_ImportTomoJob):
    """Import tilt series from movies."""

    @classmethod
    def command_id(cls):
        return super().command_id() + ".movies"

    @classmethod
    def param_matches(cls, job_params: dict[str, str]) -> bool:
        return (
            job_params.get("do_coords", "No") == "No"
            and job_params.get("images_are_motion_corrected", "No") == "No"
        )

    @classmethod
    def normalize_kwargs(cls, **kwargs):
        kwargs = super().normalize_kwargs(**kwargs)
        kwargs["images_are_motion_corrected"] = False
        return kwargs

    @classmethod
    def job_title(cls) -> str:
        return "Import Movies as Tilt Series"


class ImportTomoMicrographsJob(_ImportTomoJob):
    """Import tilt series from motion-corrected micrographs."""

    @classmethod
    def command_id(cls):
        return super().command_id() + ".micrographs"

    @classmethod
    def param_matches(cls, job_params: dict[str, str]) -> bool:
        return (
            job_params.get("do_coords", "No") == "No"
            and job_params.get("images_are_motion_corrected", "No") == "Yes"
        )

    @classmethod
    def normalize_kwargs(cls, **kwargs):
        kwargs = super().normalize_kwargs(**kwargs)
        kwargs["images_are_motion_corrected"] = True
        return kwargs

    @classmethod
    def job_title(cls) -> str:
        return "Import Micrographs as Tilt Series"


class ImportCoordinatesJob(_ImportTomoOrCoordsJob):
    @classmethod
    def command_id(cls):
        return super().command_id() + ".coords"

    @classmethod
    def param_matches(cls, job_params: dict[str, str]) -> bool:
        return job_params.get("do_coords", "No") == "Yes"

    @classmethod
    def job_title(cls) -> str:
        return "Import Coordinates"

    @classmethod
    def normalize_kwargs(cls, **kwargs):
        kwargs = super().normalize_kwargs(**kwargs)
        kwargs["do_coords"] = True
        return kwargs

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs):
        kwargs = super().normalize_kwargs_inv(**kwargs)
        kwargs.pop("do_coords", None)
        return kwargs

    def run(
        self,
        in_coords: _a.import_.IN_COORDS = "",
        remove_substring: _a.import_.REMOVE_SUBSTRING = "",
        remove_substring2: _a.import_.REMOVE_SUBSTRING2 = "",
        is_centered: _a.import_.IS_CENTERED = False,
        scale_factor: _a.import_.SCALE_FACTOR = 1.0,
        add_factor: _a.import_.ADD_FACTOR = 0.0,
        # Running
        do_queue: _a.running.DO_QUEUE = False,
        min_dedicated: _a.running.MIN_DEDICATED = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class MotionCorr2TomoJob(_Relion5TomoJob, MotionCorr2Job):
    def run(
        self,
        input_star_mics: _a.io.IN_MOVIES = "",
        eer_grouping: _a.mcor.EER_FRAC = 32,
        do_even_odd_split: _a.mcor.DO_ODD_EVEN_SPLIT = False,
        # Motion correction
        bfactor: _a.mcor.BFACTOR = 150,
        group_frames: _a.mcor.GROUP_FRAMES = 1,
        bin_factor: _a.mcor.BIN_FACTOR = 1,
        fn_defect: _a.mcor.DEFECT_FILE = "",
        fn_gain_ref: _a.mcor.GAIN_REF = "",
        gain_rot: _a.mcor.GAIN_ROT = "No rotation (0)",
        gain_flip: _a.mcor.GAIN_FLIP = "No flipping (0)",
        patch: _a.mcor.PATCH = (1, 1),
        other_motioncor2_args: _a.mcor.OTHER_MOTIONCOR2_ARGS = "",
        gpu_ids: _a.compute.GPU_IDS = "0",
        # Running
        nr_mpi: _a.running.NR_MPI = 1,
        nr_threads: _a.running.NR_THREADS = 1,
        do_queue: _a.running.DO_QUEUE = False,
        min_dedicated: _a.running.MIN_DEDICATED = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class MotionCorrOwnTomoJob(_Relion5TomoJob, MotionCorrOwnJob):
    def run(
        self,
        input_star_mics: _a.io.IN_MOVIES = "",
        do_even_odd_split: _a.mcor.DO_ODD_EVEN_SPLIT = False,
        do_float16: _a.io.DO_F16 = True,
        eer_grouping: _a.mcor.EER_FRAC = 32,
        do_save_ps: _a.mcor.DO_SAVE_PS = True,
        group_for_ps: _a.mcor.SUM_EVERY_N = 4,
        # Motion correction
        bfactor: _a.mcor.BFACTOR = 150,
        group_frames: _a.mcor.GROUP_FRAMES = 1,
        bin_factor: _a.mcor.BIN_FACTOR = 1,
        fn_defect: _a.mcor.DEFECT_FILE = "",
        fn_gain_ref: _a.mcor.GAIN_REF = "",
        gain_rot: _a.mcor.GAIN_ROT = "No rotation (0)",
        gain_flip: _a.mcor.GAIN_FLIP = "No flipping (0)",
        patch: _a.mcor.PATCH = (1, 1),
        # Running
        nr_mpi: _a.running.NR_MPI = 1,
        nr_threads: _a.running.NR_THREADS = 1,
        do_queue: _a.running.DO_QUEUE = False,
        min_dedicated: _a.running.MIN_DEDICATED = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class CtfEstimationTomoJob(_Relion5TomoJob, CtfEstimationJob):
    def run(
        self,
        # I/O
        input_star_mics: _a.io.IN_MICROGRAPHS = "",
        do_phaseshift: _a.ctffind.DO_PHASESHIFT = False,
        phase_range: _a.ctffind.PHASE_RANGE = (0, 180, 10),
        dast: _a.ctffind.DAST = 100,
        # CTFFIND
        use_given_ps: _a.ctffind.USE_GIVEN_PS = True,
        slow_search: _a.ctffind.SLOW_SEARCH = False,
        ctf_win: _a.ctffind.CTF_WIN = -1,
        box: _a.ctffind.BOX = 512,
        resmax: _a.ctffind.RESMAX = 5,
        resmin: _a.ctffind.RESMIN = 30,
        dfrange: _a.ctffind.DFRANGE = (5000, 50000, 500),
        localsearch_nominal_defocus: _a.ctffind.LOCALSEARCH_NOMINAL_DEFOCUS = 10000,
        exp_factor_dose: _a.ctffind.EXP_FACTOR_DOSE = 100,
        # Running
        nr_mpi: _a.running.NR_MPI = 1,
        do_queue: _a.running.DO_QUEUE = False,
        min_dedicated: _a.running.MIN_DEDICATED = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class ExcludeTiltJob(_Relion5TomoJob):
    """Manually select tilts to exclude from further processing."""

    @classmethod
    def type_label(cls) -> str:
        return "relion.excludetilts"

    @classmethod
    def job_is_tomo(cls):
        return False

    def run(
        self,
        in_tiltseries: _a.io.IN_TILT = "",
        cache_size: _a.tomo.EXCLUDETILT_CACHE_SIZE = 5,
        # Running
        do_queue: _a.running.DO_QUEUE = False,
        min_dedicated: _a.running.MIN_DEDICATED = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class _AlignTiltSeriesJobBase(_Relion5TomoJob):
    @classmethod
    def type_label(cls) -> str:
        return "relion.aligntiltseries"

    @classmethod
    def job_is_tomo(cls):
        return False

    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        kwargs["fn_aretomo_exe"] = _configs.get_aretomo2_exe()
        kwargs["fn_batchtomo_exe"] = _configs.get_batchruntomo_exe()
        kwargs.setdefault("do_aretomo_tiltcorrect", False)
        kwargs.setdefault("aretomo_tiltcorrect_angle", 999)
        kwargs.setdefault("other_aretomo_args", "")
        kwargs.setdefault("patch_overlap", 50)
        kwargs.setdefault("patch_size", 100)
        kwargs.setdefault("do_aretomo_ctf", False)
        kwargs.setdefault("do_aretomo_phaseshift", False)
        kwargs.setdefault("fiducial_diameter", 10.0)
        kwargs = super().normalize_kwargs(**kwargs)
        kwargs.pop("use_gpu", None)
        return kwargs

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs) -> dict[str, Any]:
        kwargs.pop("fn_aretomo_exe", None)
        kwargs.pop("fn_batchtomo_exe", None)
        return super().normalize_kwargs_inv(**kwargs)


class AlignTiltSeriesImodFiducial(_AlignTiltSeriesJobBase):
    """Automatic tilt series alignment using IMOD fiducial tracking."""

    @classmethod
    def command_id(cls):
        return super().command_id() + ".imodfiducial"

    @classmethod
    def param_matches(cls, job_params: dict[str, str]) -> bool:
        return job_params.get("do_imod_fiducials", "No") == "Yes"

    @classmethod
    def job_title(cls) -> str:
        return "Align Tilt Series (IMOD Fiducials)"

    @classmethod
    def normalize_kwargs(cls, **kwargs):
        kwargs["do_imod_fiducials"] = True
        kwargs["do_aretomo2"] = False
        kwargs["do_imod_patchtrack"] = False
        kwargs["tomogram_thickness"] = 300.0
        kwargs = super().normalize_kwargs(**kwargs)
        kwargs["gpu_ids"] = ""
        return kwargs

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs) -> dict[str, Any]:
        kwargs.pop("do_imod_fiducials", None)
        kwargs.pop("do_aretomo2", None)
        kwargs.pop("do_imod_patchtrack", None)
        kwargs.pop("gpu_ids", None)
        # remove parameters from other methods
        for key in [
            "patch_size", "patch_overlap", "do_aretomo_tiltcorrect", "do_aretomo",
            "aretomo_tiltcorrect_angle", "do_aretomo_ctf", "do_aretomo_phaseshift",
            "other_aretomo_args", "aretomo_thickness", "aretomo_tiltcorrect",
            "tomogram_thickness",
        ]:  # fmt: skip
            kwargs.pop(key, None)
        return super().normalize_kwargs_inv(**kwargs)

    def run(
        self,
        in_tiltseries: _a.io.IN_TILT = "",
        fiducial_diameter: _a.tomo.FIDUCIAL_DIAMETER = 10.0,
        # Running
        nr_mpi: _a.running.NR_MPI = 1,
        do_queue: _a.running.DO_QUEUE = False,
        min_dedicated: _a.running.MIN_DEDICATED = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class AlignTiltSeriesImodPatch(_AlignTiltSeriesJobBase):
    """Automatic tilt series alignment using IMOD patch tracking."""

    @classmethod
    def command_id(cls):
        return super().command_id() + ".imodpatch"

    @classmethod
    def param_matches(cls, job_params: dict[str, str]) -> bool:
        return job_params.get("do_imod_patchtrack", "No") == "Yes"

    @classmethod
    def job_title(cls) -> str:
        return "Align Tilt Series (IMOD Patch Tracking)"

    @classmethod
    def normalize_kwargs(cls, **kwargs):
        kwargs["do_imod_fiducials"] = False
        kwargs["do_aretomo2"] = False
        kwargs["do_imod_patchtrack"] = True
        kwrags = super().normalize_kwargs(**kwargs)
        kwrags["gpu_ids"] = ""
        return kwrags

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs) -> dict[str, Any]:
        kwargs.pop("do_imod_fiducials", None)
        kwargs.pop("do_aretomo2", None)
        kwargs.pop("do_imod_patchtrack", None)
        kwargs.pop("gpu_ids", None)
        kwargs.pop("fiducial_diameter", None)
        kwargs.pop("do_aretomo_tiltcorrect", None)
        kwargs.pop("aretomo_tiltcorrect_angle", None)
        kwargs.pop("do_aretomo_ctf", None)
        kwargs.pop("do_aretomo_phaseshift", None)
        kwargs.pop("other_aretomo_args", None)
        return super().normalize_kwargs_inv(**kwargs)

    def run(
        self,
        in_tiltseries: _a.io.IN_TILT = "",
        tomogram_thickness: _a.tomo.TOMO_THICKNESS = 300.0,
        patch_size: _a.tomo.PATCH_SIZE = 100,
        patch_overlap: _a.tomo.PATCH_OVERLAP = 50,
        # Running
        nr_mpi: _a.running.NR_MPI = 1,
        do_queue: _a.running.DO_QUEUE = False,
        min_dedicated: _a.running.MIN_DEDICATED = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class AlignTiltSeriesAreTomo2(_AlignTiltSeriesJobBase):
    """Automatic tilt series alignment using AreTomo2."""

    @classmethod
    def command_id(cls):
        return super().command_id() + ".aretomo2"

    @classmethod
    def param_matches(cls, job_params: dict[str, str]) -> bool:
        return job_params.get("do_aretomo2", "No") == "Yes"

    @classmethod
    def job_title(cls) -> str:
        return "Align Tilt Series (AreTomo2)"

    @classmethod
    def normalize_kwargs(cls, **kwargs):
        kwargs["do_imod_fiducials"] = False
        kwargs["do_aretomo2"] = True
        kwargs["do_imod_patchtrack"] = False
        if kwargs["aretomo_tiltcorrect_angle"] is not None:
            kwargs["do_aretomo_tiltcorrect"] = True
        else:
            kwargs["do_aretomo_tiltcorrect"] = False
            kwargs["aretomo_tiltcorrect_angle"] = 999
        return super().normalize_kwargs(**kwargs)

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs) -> dict[str, Any]:
        kwargs = super().normalize_kwargs_inv(**kwargs)
        kwargs.pop("fiducial_diameter", None)
        kwargs.pop("patch_size", None)
        kwargs.pop("patch_overlap", None)
        kwargs.pop("do_imod_fiducials", None)
        kwargs.pop("do_aretomo2", None)
        kwargs.pop("do_imod_patchtrack", None)
        if kwargs.pop("do_aretomo_tiltcorrect", "No") == "No":
            kwargs["aretomo_tiltcorrect_angle"] = None
        return kwargs

    def run(
        self,
        in_tiltseries: _a.io.IN_TILT = "",
        tomogram_thickness: _a.tomo.TOMO_THICKNESS = 300.0,
        aretomo_tiltcorrect_angle: _a.tomo.ARETOMO_TILTCORRECT_ANGLE = 999,
        do_aretomo_ctf: _a.tomo.DO_ARETOMO_CTF = False,
        do_aretomo_phaseshift: _a.tomo.DO_ARETOMO_PHASESHIFT = False,
        other_aretomo_args: _a.tomo.OTHER_ARETOMO_ARGS = "",
        gpu_ids: _a.compute.GPU_IDS = "",
        # Running
        nr_mpi: _a.running.NR_MPI = 1,
        do_queue: _a.running.DO_QUEUE = False,
        min_dedicated: _a.running.MIN_DEDICATED = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")

    @classmethod
    def setup_widgets(cls, widgets):
        @widgets["do_aretomo_ctf"].changed.connect
        def _on_do_aretomo_ctf_changed(value: bool):
            widgets["do_aretomo_phaseshift"].enabled = value

        _on_do_aretomo_ctf_changed(widgets["do_aretomo_ctf"].value)


class _ReconstructTomogramBaseJob(_Relion5TomoJob):
    @classmethod
    def type_label(cls) -> str:
        return "relion.reconstructtomograms"

    @classmethod
    def job_is_tomo(cls):
        return False

    @classmethod
    def normalize_kwargs(cls, **kwargs):
        if "dims" in kwargs:
            xdim, ydim, zdim = kwargs.pop("dims")
            kwargs["xdim"] = xdim
            kwargs["ydim"] = ydim
            kwargs["zdim"] = zdim
        return super().normalize_kwargs(**kwargs)

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs) -> dict[str, Any]:
        kwargs = super().normalize_kwargs_inv(**kwargs)
        kwargs["dims"] = (
            kwargs.pop("xdim", 4000),
            kwargs.pop("ydim", 4000),
            kwargs.pop("zdim", 2000),
        )
        return kwargs

    @classmethod
    def setup_widgets(cls, widgets):
        @widgets["do_proj"].changed.connect
        def _on_do_proj_changed(value: bool):
            widgets["centre_proj"].enabled = value
            widgets["thickness_proj"].enabled = value

        _on_do_proj_changed(widgets["do_proj"].value)

        # TODO: the input path is relative, so it is not simple to get choices
        # @widgets["in_tiltseries"].changed.connect
        # def _on_in_tiltseries_changed(value: str):
        #     choices = []
        #     if Path(value).exists() and Path(value).is_file():
        #         if star := read_star(value).try_first():
        #             if loop := star.try_loop():
        #                 choices = loop.to_polars()["rlnTomoName"].to_list()

        #     widgets["tomo_name"].choices = [""] + choices

        # _on_in_tiltseries_changed(widgets["in_tiltseries"].value)


class ReconstructTomogramJob(_ReconstructTomogramBaseJob):
    """Reconstruct tomograms from aligned tilt series by back projection."""

    @classmethod
    def normalize_kwargs(cls, **kwargs):
        kwargs["generate_split_tomograms"] = False
        return super().normalize_kwargs(**kwargs)

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs) -> dict[str, Any]:
        kwargs = super().normalize_kwargs_inv(**kwargs)
        kwargs.pop("generate_split_tomograms", None)
        return kwargs

    @classmethod
    def command_id(cls):
        return super().command_id() + ".full"

    @classmethod
    def param_matches(cls, job_params):
        return job_params.get("generate_split_tomograms", "No") == "No"

    @classmethod
    def job_title(cls) -> str:
        return "Reconstruct Tomos"

    def run(
        self,
        # I/O
        in_tiltseries: _a.io.IN_TILT = "",
        do_proj: _a.tomo.DO_PROJ = False,
        centre_proj: _a.tomo.CENTRE_PROJ = 0,
        thickness_proj: _a.tomo.THICKNESS_PROJ = 10,
        # Reconstruct
        dims: _a.tomo.DIMS = (4000, 4000, 2000),
        binned_angpix: _a.tomo.BINNED_ANGPIX = 10.0,
        tiltangle_offset: _a.tomo.TILTANGLE_OFFSET = 0.0,
        tomo_name: _a.tomo.TOMO_NAME = "",
        # Filter
        do_fourier: _a.tomo.DO_FOURIER = True,
        ctf_intact_first_peak: _a.tomo.CTF_INTACT_FIRST_PEAK = True,
        # Running
        nr_mpi: _a.running.NR_MPI = 1,
        nr_threads: _a.running.NR_THREADS = 1,
        do_queue: _a.running.DO_QUEUE = False,
        min_dedicated: _a.running.MIN_DEDICATED = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")

    @classmethod
    def setup_widgets(cls, widgets):
        super().setup_widgets(widgets)

        @widgets["do_fourier"].changed.connect
        def _on_do_fourier_changed(value: bool):
            widgets["ctf_intact_first_peak"].enabled = value

        _on_do_fourier_changed(widgets["do_fourier"].value)


class ReconstructHalfTomogramJob(_ReconstructTomogramBaseJob):
    """Reconstruct half tomograms from aligned tilt series."""

    @classmethod
    def normalize_kwargs(cls, **kwargs):
        kwargs["do_fourier"] = False
        kwargs["ctf_intact_first_peak"] = True
        kwargs["generate_split_tomograms"] = True
        return super().normalize_kwargs(**kwargs)

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs) -> dict[str, Any]:
        kwargs = super().normalize_kwargs_inv(**kwargs)
        kwargs.pop("do_fourier", None)
        kwargs.pop("ctf_intact_first_peak", None)
        kwargs.pop("generate_split_tomograms", None)
        return kwargs

    @classmethod
    def command_id(cls):
        return super().command_id() + ".halves"

    @classmethod
    def job_title(cls) -> str:
        return "Reconstruct Tomos For Denoise"

    @classmethod
    def param_matches(cls, job_params):
        return job_params.get("generate_split_tomograms", "No") == "Yes"

    def run(
        self,
        # I/O
        in_tiltseries: _a.io.IN_TILT = "",
        do_proj: _a.tomo.DO_PROJ = False,
        centre_proj: _a.tomo.CENTRE_PROJ = 0,
        thickness_proj: _a.tomo.THICKNESS_PROJ = 10,
        # Reconstruct
        dims: _a.tomo.DIMS = (4000, 4000, 2000),
        binned_angpix: _a.tomo.BINNED_ANGPIX = 10.0,
        tiltangle_offset: _a.tomo.TILTANGLE_OFFSET = 0.0,
        tomo_name: _a.tomo.TOMO_NAME = "",
        # Running
        nr_mpi: _a.running.NR_MPI = 1,
        nr_threads: _a.running.NR_THREADS = 1,
        do_queue: _a.running.DO_QUEUE = False,
        min_dedicated: _a.running.MIN_DEDICATED = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class PickJob(_Relion5TomoJob):
    """Manually pick particles from tomograms."""

    @classmethod
    def type_label(cls) -> str:
        return "relion.picktomo"

    @classmethod
    def normalize_kwargs(cls, **kwargs):
        if kwargs.get("particle_spacing") is None:
            kwargs["particle_spacing"] = -1
        return super().normalize_kwargs(**kwargs)

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs) -> dict[str, Any]:
        if "particle_spacing" in kwargs and float(kwargs["particle_spacing"]) < 0:
            kwargs["particle_spacing"] = None
        return super().normalize_kwargs_inv(**kwargs)

    @classmethod
    def job_is_tomo(cls):
        return False

    def run(
        self,
        in_tomoset: _a.io.IN_TILT = "",
        in_star_file: _a.io.IN_PARTICLES = "",
        pick_mode: _a.manualpick.PICK_MODE = "particles",
        particle_spacing: _a.manualpick.PARTICLE_SPACING = None,
        # Running
        do_queue: _a.running.DO_QUEUE = False,
        min_dedicated: _a.running.MIN_DEDICATED = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class ExtractParticlesTomoJob(_Relion5TomoJob):
    """Extract pseudo subtomograms for averaging and refinement."""

    @classmethod
    def type_label(cls) -> str:
        return "relion.pseudosubtomo"

    @classmethod
    def job_is_tomo(cls):
        return False

    @classmethod
    def normalize_kwargs(cls, **kwargs):
        kwargs = norm_optim(**super().normalize_kwargs(**kwargs))
        for name in ["crop_size", "max_dose"]:
            if kwargs.get(name) is None:
                kwargs[name] = -1
        return kwargs

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs) -> dict[str, Any]:
        kwargs = norm_optim_inv(**super().normalize_kwargs_inv(**kwargs))
        for name in ["crop_size", "max_dose"]:
            if name in kwargs and float(kwargs[name]) < 0:
                kwargs[name] = None
        return kwargs

    def run(
        self,
        in_optim: _a.io.IN_OPTIM = None,
        # Reconstruct
        binning: _a.extract.BINNING = 1,
        box_size: _a.extract.BOX_SIZE = 128,
        crop_size: _a.extract.CROP_SIZE = None,
        max_dose: _a.extract.MAX_DOSE = None,
        min_frames: _a.extract.MIN_FRAMES = 1,
        do_stack2d: _a.extract.DO_STACK2D = True,
        do_float16: _a.io.DO_F16 = True,
        # Running
        nr_mpi: _a.running.NR_MPI = 1,
        nr_threads: _a.running.NR_THREADS = 1,
        do_queue: _a.running.DO_QUEUE = False,
        min_dedicated: _a.running.MIN_DEDICATED = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class _DenoiseJobBase(_Relion5TomoJob):
    @classmethod
    def type_label(cls) -> str:
        return "relion.denoisetomo"

    @classmethod
    def job_is_tomo(cls):
        return False

    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        kwargs["cryocare_path"] = _configs.get_cryocare_dir()
        kwargs = super().normalize_kwargs(**kwargs)
        kwargs.pop("use_gpu", None)  # CryoCARE always uses GPU, so this arg is not used
        return kwargs

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs) -> dict[str, Any]:
        kwargs.pop("cryocare_path", None)
        return super().normalize_kwargs_inv(**kwargs)


class DenoiseTrain(_DenoiseJobBase):
    @classmethod
    def command_id(cls):
        return super().command_id() + "-train"

    @classmethod
    def param_matches(cls, job_params: dict[str, str]) -> bool:
        return job_params.get("do_cryocare_train", "No") == "Yes"

    @classmethod
    def job_title(cls) -> str:
        return "CryoCARE Train"

    @classmethod
    def normalize_kwargs(cls, **kwargs):
        kwargs["do_cryocare_predict"] = False
        kwargs["do_cryocare_train"] = True
        kwargs["care_denoising_model"] = ""
        kwargs["ntiles_x"] = 2
        kwargs["ntiles_y"] = 2
        kwargs["ntiles_z"] = 2
        kwargs["denoising_tomo_name"] = ""
        return super().normalize_kwargs(**kwargs)

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs) -> dict[str, Any]:
        kwargs.pop("do_cryocare_predict", None)
        kwargs.pop("do_cryocare_train", None)
        kwargs.pop("care_denoising_model", None)
        kwargs.pop("ntiles_x", None)
        kwargs.pop("ntiles_y", None)
        kwargs.pop("ntiles_z", None)
        kwargs.pop("denoising_tomo_name", None)
        return super().normalize_kwargs_inv(**kwargs)

    def run(
        self,
        in_tomoset: _a.tomo.IN_TOMOSET = "",
        tomograms_for_training: _a.tomo.TOMOGRAMS_FOR_TRAINING = "",
        number_training_subvolumes: _a.tomo.NUMBER_TRAINING_SUBVOLUMES = 1200,
        subvolume_dimensions: _a.tomo.SUBVOLUME_DIMENSIONS = 72,
        gpu_ids: _a.compute.GPU_IDS = "0",
        # Running
        do_queue: _a.running.DO_QUEUE = False,
        min_dedicated: _a.running.MIN_DEDICATED = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class DenoisePredict(_DenoiseJobBase):
    @classmethod
    def command_id(cls):
        return super().command_id() + "-predict"

    @classmethod
    def param_matches(cls, job_params: dict[str, str]) -> bool:
        return job_params.get("do_cryocare_predict", "No") == "Yes"

    @classmethod
    def job_title(cls) -> str:
        return "CryoCARE Predict"

    @classmethod
    def normalize_kwargs(cls, **kwargs):
        kwargs["do_cryocare_predict"] = True
        kwargs["do_cryocare_train"] = False
        kwargs["tomograms_for_training"] = ""
        kwargs["number_training_subvolumes"] = 1200
        kwargs["subvolume_dimensions"] = 72
        if "ntiles" in kwargs:
            ntile_x, ntile_y, ntile_z = kwargs.pop("ntiles")
            kwargs["ntiles_x"] = ntile_x
            kwargs["ntiles_y"] = ntile_y
            kwargs["ntiles_z"] = ntile_z
        return super().normalize_kwargs(**kwargs)

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs) -> dict[str, Any]:
        kwargs.pop("do_cryocare_predict", None)
        kwargs.pop("do_cryocare_train", None)
        kwargs.pop("tomograms_for_training", None)
        kwargs.pop("number_training_subvolumes", None)
        kwargs.pop("subvolume_dimensions", None)
        kwargs["ntiles"] = (
            kwargs.pop("ntiles_x", 2),
            kwargs.pop("ntiles_y", 2),
            kwargs.pop("ntiles_z", 2),
        )
        return super().normalize_kwargs_inv(**kwargs)

    def run(
        self,
        in_tomoset: _a.tomo.IN_TOMOSET = "",
        care_denoising_model: _a.tomo.CARE_DENOISING_MODEL = "",
        ntiles: _a.tomo.NTILES = (2, 2, 2),
        denoising_tomo_name: _a.tomo.DENOISING_TOMO_NAME = "",
        gpu_ids: _a.compute.GPU_IDS = "0",
        # Running
        do_queue: _a.running.DO_QUEUE = False,
        min_dedicated: _a.running.MIN_DEDICATED = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class InitialModelTomoJob(_Relion5TomoJob, InitialModelJob):
    @classmethod
    def type_label(cls) -> str:
        return "relion.initialmodel.tomo"

    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        kwargs["fn_cont"] = ""
        return norm_optim(**super().normalize_kwargs(**kwargs))

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs) -> dict[str, Any]:
        kwargs.pop("fn_cont", None)
        return norm_optim_inv(**super().normalize_kwargs_inv(**kwargs))

    def run(
        self,
        in_optim: _a.io.IN_OPTIM = None,
        # CTF
        do_ctf_correction: _a.misc.DO_CTF = True,
        ctf_intact_first_peak: _a.misc.IGNORE_CTF = False,
        # Optimisation
        nr_iter: _a.inimodel.NUM_ITER = 200,
        tau_fudge: _a.misc.TAU_FUDGE = 4,
        nr_classes: _a.inimodel.NUM_CLASS = 1,
        particle_diameter: _a.misc.MASK_DIAMETER = 200,
        do_solvent: _a.inimodel.DO_SOLVENT = True,
        sym_name: _a.inimodel.SYM_NAME = "C1",
        do_run_C1: _a.inimodel.DO_RUN_C1 = True,
        sigma_tilt: _a.sampling.SIGMA_TILT = None,
        # Compute
        do_parallel_discio: _a.compute.USE_PARALLEL_DISC_IO = True,
        nr_pool: _a.compute.NUM_POOL = 3,
        do_preread_images: _a.compute.DO_PREREAD = False,
        use_scratch: _a.compute.USE_SCRATCH = False,
        do_combine_thru_disc: _a.compute.DO_COMBINE_THRU_DISC = False,
        gpu_ids: _a.compute.GPU_IDS = "",
        # Running
        nr_mpi: _a.running.NR_MPI = 1,
        nr_threads: _a.running.NR_THREADS = 1,
        do_queue: _a.running.DO_QUEUE = False,
        min_dedicated: _a.running.MIN_DEDICATED = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")

    @classmethod
    def setup_widgets(cls, widgets):
        @widgets["do_ctf_correction"].changed.connect
        def _on_do_ctf_correction_changed(value: bool):
            widgets["ctf_intact_first_peak"].enabled = value

        widgets["ctf_intact_first_peak"].enabled = widgets["do_ctf_correction"].value


class Class3DNoAlignmentTomoJob(_Relion5TomoJob, Class3DNoAlignmentJob):
    """3D classification of subtomograms without alignment."""

    @classmethod
    def command_id(cls):
        return super().command_id() + "-tomo"

    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        kwargs["sigma_tilt"] = -1
        return norm_optim(**Class3DNoAlignmentJob.normalize_kwargs(**kwargs))

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs) -> dict[str, Any]:
        kwargs.pop("sigma_tilt", None)
        return norm_optim_inv(**Class3DNoAlignmentJob.normalize_kwargs_inv(**kwargs))

    def run(
        self,
        in_optim: _a.io.IN_OPTIM = None,
        fn_ref: _a.io.REF_TYPE = "",
        fn_mask: _a.io.IN_MASK = "",
        # Reference
        ref_correct_greyscale: _a.misc.REF_CORRECT_GRAY = False,
        trust_ref_size: _a.misc.TRUST_REF_SIZE = True,
        ini_high: _a.misc.INITIAL_LOWPASS = 60,
        sym_name: _a.misc.REF_SYMMETRY = "C1",
        # CTF
        do_ctf_correction: _a.misc.DO_CTF = True,
        ctf_intact_first_peak: _a.misc.IGNORE_CTF = False,
        # Optimisation
        nr_classes: _a.class_.NUM_CLASS = 1,
        nr_iter: _a.class_.NUM_ITER = 25,
        tau_fudge: _a.misc.TAU_FUDGE = 1,
        particle_diameter: _a.misc.MASK_DIAMETER = 200,
        do_zero_mask: _a.misc.MASK_WITH_ZEROS = True,
        do_blush: _a.misc.DO_BLUSH = False,
        # Helix
        do_helix: _a.helix.DO_HELIX = False,
        helical_tube_diameter_range: _a.helix.HELICAL_TUBE_DIAMETER_RANGE = (-1, -1),
        helical_range_distance: _a.helix.HELICAL_RANGE_DIST = -1,
        keep_tilt_prior_fixed: _a.helix.KEEP_TILT_PRIOR_FIXED = True,
        do_apply_helical_symmetry: _a.helix.DO_APPLY_HELICAL_SYMMETRY = True,
        helical_twist_initial: _a.helix.HELICAL_TWIST_INITIAL = 0,
        helical_rise_initial: _a.helix.HELICAL_RISE_INITIAL = 0,
        helical_nr_asu: _a.helix.HELICAL_NR_ASU = 1,
        helical_z_percentage: _a.helix.HELICAL_Z_PERCENTAGE = 30,
        # Compute
        do_fast_subsets: _a.compute.USE_FAST_SUBSET = False,
        do_parallel_discio: _a.compute.USE_PARALLEL_DISC_IO = True,
        use_scratch: _a.compute.USE_SCRATCH = False,
        nr_pool: _a.compute.NUM_POOL = 3,
        do_pad1: _a.compute.DO_PAD1 = False,
        do_preread_images: _a.compute.DO_PREREAD = False,
        do_combine_thru_disc: _a.compute.DO_COMBINE_THRU_DISC = False,
        # Running
        nr_mpi: _a.running.NR_MPI = 1,
        nr_threads: _a.running.NR_THREADS = 1,
        do_queue: _a.running.DO_QUEUE = False,
        min_dedicated: _a.running.MIN_DEDICATED = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class Class3DTomoJob(_Relion5TomoJob, Class3DJob):
    """3D classification of subtomograms."""

    @classmethod
    def command_id(cls):
        return super().command_id() + "-tomo"

    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        return norm_optim(**Class3DJob.normalize_kwargs(**kwargs))

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs) -> dict[str, Any]:
        return norm_optim_inv(**Class3DJob.normalize_kwargs_inv(**kwargs))

    def run(
        self,
        in_optim: _a.io.IN_OPTIM = None,
        fn_ref: _a.io.REF_TYPE = "",
        fn_mask: _a.io.IN_MASK = "",
        # Reference
        ref_correct_greyscale: _a.misc.REF_CORRECT_GRAY = False,
        trust_ref_size: _a.misc.TRUST_REF_SIZE = True,
        ini_high: _a.misc.INITIAL_LOWPASS = 60,
        sym_name: _a.misc.REF_SYMMETRY = "C1",
        # CTF
        do_ctf_correction: _a.misc.DO_CTF = True,
        ctf_intact_first_peak: _a.misc.IGNORE_CTF = False,
        # Optimisation
        nr_classes: _a.class_.NUM_CLASS = 1,
        tau_fudge: _a.misc.TAU_FUDGE = 1,
        nr_iter: _a.class_.NUM_ITER = 25,
        particle_diameter: _a.misc.MASK_DIAMETER = 200,
        do_zero_mask: _a.misc.MASK_WITH_ZEROS = True,
        highres_limit: _a.class_.HIGH_RES_LIMIT = -1,
        do_blush: _a.misc.DO_BLUSH = False,
        # Sampling
        sampling: _a.sampling.ANG_SAMPLING = "7.5 degrees",
        offset_range_step: _a.sampling.OFFSET_RANGE_STEP = (5, 1),
        allow_coarser: _a.sampling.ALLOW_COARSER_SAMPLING = False,
        do_local_ang_searches: _a.sampling.LOCAL_ANG_SEARCH = False,
        sigma_angles: _a.sampling.SIGMA_ANGLES = 5,
        relax_sym: _a.sampling.RELAX_SYMMETRY = "",
        sigma_tilt: _a.sampling.SIGMA_TILT = None,
        # Helix
        do_helix: _a.helix.DO_HELIX = False,
        helical_tube_diameter_range: _a.helix.HELICAL_TUBE_DIAMETER_RANGE = (-1, -1),
        rot_tilt_psi_range: _a.helix.ROT_TILT_PSI_RANGE = (-1, 15, 10),
        helical_range_distance: _a.helix.HELICAL_RANGE_DIST = -1,
        keep_tilt_prior_fixed: _a.helix.KEEP_TILT_PRIOR_FIXED = True,
        do_apply_helical_symmetry: _a.helix.DO_APPLY_HELICAL_SYMMETRY = True,
        helical_twist_initial: _a.helix.HELICAL_TWIST_INITIAL = 0,
        helical_rise_initial: _a.helix.HELICAL_RISE_INITIAL = 0,
        helical_nr_asu: _a.helix.HELICAL_NR_ASU = 1,
        helical_z_percentage: _a.helix.HELICAL_Z_PERCENTAGE = 30,
        do_local_search_helical_symmetry: _a.helix.DO_LOCAL_SEARCH_H_SYM = False,
        helical_twist_range: _a.helix.HELICAL_TWIST_RANGE = (0, 0, 0),
        helical_rise_range: _a.helix.HELICAL_RISE_RANGE = (0, 0, 0),
        # Compute
        do_fast_subsets: _a.compute.USE_FAST_SUBSET = False,
        do_parallel_discio: _a.compute.USE_PARALLEL_DISC_IO = True,
        use_scratch: _a.compute.USE_SCRATCH = False,
        nr_pool: _a.compute.NUM_POOL = 3,
        do_pad1: _a.compute.DO_PAD1 = False,
        do_preread_images: _a.compute.DO_PREREAD = False,
        do_combine_thru_disc: _a.compute.DO_COMBINE_THRU_DISC = False,
        gpu_ids: _a.compute.GPU_IDS = "",
        # Running
        nr_mpi: _a.running.NR_MPI = 1,
        nr_threads: _a.running.NR_THREADS = 1,
        do_queue: _a.running.DO_QUEUE = False,
        min_dedicated: _a.running.MIN_DEDICATED = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class Refine3DTomoJob(_Relion5TomoJob, Refine3DJob):
    @classmethod
    def type_label(cls) -> str:
        return "relion.refine3d.tomo"

    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        return norm_optim(**Refine3DJob.normalize_kwargs(**kwargs))

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs) -> dict[str, Any]:
        return norm_optim_inv(**Refine3DJob.normalize_kwargs_inv(**kwargs))

    def run(
        self,
        in_optim: _a.io.IN_OPTIM = None,
        fn_ref: _a.io.REF_TYPE = "",
        fn_mask: _a.io.IN_MASK = "",
        # Reference
        ref_correct_greyscale: _a.misc.REF_CORRECT_GRAY = False,
        trust_ref_size: _a.misc.TRUST_REF_SIZE = True,
        ini_high: _a.misc.INITIAL_LOWPASS = 60,
        sym_name: _a.misc.REF_SYMMETRY = "C1",
        # CTF
        do_ctf_correction: _a.misc.DO_CTF = True,
        ctf_intact_first_peak: _a.misc.IGNORE_CTF = False,
        # Optimisation
        particle_diameter: _a.misc.MASK_DIAMETER = 200,
        do_zero_mask: _a.misc.MASK_WITH_ZEROS = True,
        do_solvent_fsc: _a.misc.SOLVENT_FLATTEN_FSC = False,
        do_blush: _a.misc.DO_BLUSH = False,
        # Sampling
        sampling: _a.sampling.ANG_SAMPLING = "7.5 degrees",
        offset_range_step: _a.sampling.OFFSET_RANGE_STEP = (5, 1),
        auto_local_sampling: _a.sampling.LOC_ANG_SAMPLING = "1.8 degrees",
        relax_sym: _a.sampling.RELAX_SYMMETRY = "",
        auto_faster: _a.sampling.AUTO_FASTER = False,
        sigma_tilt: _a.sampling.SIGMA_TILT = None,
        # Helix
        do_helix: _a.helix.DO_HELIX = False,
        helical_tube_diameter_range: _a.helix.HELICAL_TUBE_DIAMETER_RANGE = (-1, -1),
        rot_tilt_psi_range: _a.helix.ROT_TILT_PSI_RANGE = (-1, 15, 10),
        helical_range_distance: _a.helix.HELICAL_RANGE_DIST = -1,
        keep_tilt_prior_fixed: _a.helix.KEEP_TILT_PRIOR_FIXED = True,
        do_apply_helical_symmetry: _a.helix.DO_APPLY_HELICAL_SYMMETRY = True,
        helical_nr_asu: _a.helix.HELICAL_NR_ASU = 1,
        helical_twist_initial: _a.helix.HELICAL_TWIST_INITIAL = 0,
        helical_rise_initial: _a.helix.HELICAL_RISE_INITIAL = 0,
        helical_z_percentage: _a.helix.HELICAL_Z_PERCENTAGE = 30,
        do_local_search_helical_symmetry: _a.helix.DO_LOCAL_SEARCH_H_SYM = False,
        helical_twist_range: _a.helix.HELICAL_TWIST_RANGE = (0, 0, 0),
        helical_rise_range: _a.helix.HELICAL_RISE_RANGE = (0, 0, 0),
        # Compute
        do_parallel_discio: _a.compute.USE_PARALLEL_DISC_IO = True,
        nr_pool: _a.compute.NUM_POOL = 3,
        do_pad1: _a.compute.DO_PAD1 = False,
        do_preread_images: _a.compute.DO_PREREAD = False,
        use_scratch: _a.compute.USE_SCRATCH = False,
        do_combine_thru_disc: _a.compute.DO_COMBINE_THRU_DISC = False,
        gpu_ids: _a.compute.GPU_IDS = "",
        # Running
        nr_mpi: _a.running.NR_MPI = 3,
        nr_threads: _a.running.NR_THREADS = 1,
        do_queue: _a.running.DO_QUEUE = False,
        min_dedicated: _a.running.MIN_DEDICATED = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class ReconstructParticlesJob(_Relion5TomoJob):
    @classmethod
    def type_label(cls) -> str:
        return "relion.reconstructparticletomo"

    @classmethod
    def normalize_kwargs(cls, **kwargs):
        kwargs = norm_optim(**super().normalize_kwargs(**kwargs))
        if kwargs.get("crop_size") is None:
            kwargs["crop_size"] = -1
        return kwargs

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs) -> dict[str, Any]:
        kwargs = norm_optim_inv(**super().normalize_kwargs_inv(**kwargs))
        if "crop_size" in kwargs and float(kwargs["crop_size"]) < 0:
            kwargs["crop_size"] = None
        return kwargs

    def run(
        self,
        in_optim: _a.io.IN_OPTIM = None,
        # Average
        binning: _a.tomo.BINNING = 1,
        box_size: _a.tomo.BOX_SIZE = 128,
        crop_size: _a.tomo.CROP_SIZE = None,
        snr: _a.tomo.SNR = 0,
        sym_name: _a.tomo.SYM_NAME = "C1",
        # Helix
        do_helix: _a.helix.DO_HELIX = False,
        helical_nr_asu: _a.helix.HELICAL_NR_ASU = 1,
        helical_twist: _a.tomo.HELICAL_TWIST = -1,
        helical_rise: _a.helix.HELICAL_RISE = 4.75,
        helical_tube_outer_diameter: _a.helix.HELICAL_TUBE_DIAMETER = 200,
        helical_z_percentage: _a.helix.HELICAL_Z_PERCENTAGE = 20,
        # Running
        nr_mpi: _a.running.NR_MPI = 1,
        nr_threads: _a.running.NR_THREADS = 1,
        do_queue: _a.running.DO_QUEUE = False,
        min_dedicated: _a.running.MIN_DEDICATED = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")

    @staticmethod
    def get_optimisation_set(path: Path) -> str | None:
        """Function used for job connection."""
        if (opt_path := path.joinpath("optimisation_set.star")).exists():
            return opt_path.as_posix()
        if (pipeline_path := path.joinpath("job_pipeline.star")).exists():
            pipeline = RelionPipeline.from_star(pipeline_path)
            if node := pipeline.get_input_by_type("TomoOptimisationSet"):
                return node.path
        return None

    @classmethod
    def setup_widgets(cls, widgets):
        @widgets["do_helix"].changed.connect
        def _on_do_helix_changed(value: bool):
            for name, child in widgets.items():
                if name.startswith("helical_"):
                    child.enabled = value

        _on_do_helix_changed(widgets["do_helix"].value)


class CtfRefineTomoJob(_Relion5TomoJob):
    @classmethod
    def type_label(cls) -> str:
        return "relion.ctfrefinetomo"

    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        kwargs = norm_optim(**super().normalize_kwargs(**kwargs))
        if "lambda" not in kwargs:
            kwargs["lambda"] = kwargs.pop("lambda_param", None)
        if kwargs["lambda"] is None:
            kwargs["lambda"] = 0.1
            kwargs["do_reg_def"] = False
        else:
            kwargs["do_reg_def"] = True
        return kwargs

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs) -> dict[str, Any]:
        kwargs = norm_optim_inv(**super().normalize_kwargs_inv(**kwargs))
        if "lambda" in kwargs:
            kwargs["lambda_param"] = kwargs.pop("lambda")
        if not kwargs.pop("do_reg_def", False):
            kwargs["lambda_param"] = None
        return kwargs

    def run(
        self,
        in_optim: _a.io.IN_OPTIM = None,
        in_halfmaps: _a.io.HALFMAP_TYPE = "",
        in_refmask: _a.io.IN_MASK = "",
        in_post: _a.io.PROCESS_TYPE = "",
        # CTF Refinement
        box_size: _a.ctfrefine.BOX_SIZE = 128,
        do_defocus: _a.ctfrefine.DO_DEFOCUS_TOMO = True,
        focus_range: _a.ctfrefine.FOCUS_RANGE = 3000,
        lambda_param: _a.ctfrefine.LAMBDA_PARAM = 0.1,
        do_scale: _a.ctfrefine.DO_SCALE = True,
        do_frame_scale: _a.ctfrefine.DO_FRAME_SCALE = True,
        do_tomo_scale: _a.ctfrefine.DO_TOMO_SCALE = False,
        # Running
        nr_mpi: _a.running.NR_MPI = 1,
        nr_threads: _a.running.NR_THREADS = 1,
        do_queue: _a.running.DO_QUEUE = False,
        min_dedicated: _a.running.MIN_DEDICATED = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")

    @classmethod
    def setup_widgets(cls, widgets):
        @widgets["do_defocus"].changed.connect
        def _on_do_defocus_changed(value: bool):
            widgets["focus_range"].enabled = value
            widgets["lambda_param"].enabled = value

        _on_do_defocus_changed(widgets["do_defocus"].value)

        @widgets["do_scale"].changed.connect
        def _on_do_scale_changed(value: bool):
            widgets["do_frame_scale"].enabled = value
            widgets["do_tomo_scale"].enabled = value

        _on_do_scale_changed(widgets["do_scale"].value)


class PostProcessTomoJob(_Relion5TomoJob, PostProcessJob):
    """Run post-processing on a subtomogram average."""

    # parameters are the same


class FrameAlignTomoJob(_Relion5TomoJob):
    """Run Bayesian polishing on tilt series frames."""

    @classmethod
    def type_label(cls) -> str:
        return "relion.framealigntomo"

    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        kwargs = norm_optim(**super().normalize_kwargs(**kwargs))
        return kwargs

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs) -> dict[str, Any]:
        kwargs = norm_optim_inv(**super().normalize_kwargs_inv(**kwargs))
        return kwargs

    def run(
        self,
        # I/O
        in_optim: _a.io.IN_OPTIM = None,
        in_halfmaps: _a.io.HALFMAP_TYPE = "",
        in_refmask: _a.io.IN_MASK = "",
        in_post: _a.io.PROCESS_TYPE = "",
        # Polish
        box_size: _a.polish.BOX_SIZE = 128,
        max_error: _a.polish.MAX_ERROR = 5,
        do_shift_align: _a.polish.DO_SHIFT_ALIGN = True,
        shift_align_type: _a.polish.SHIFT_ALIGN_TYPE = "Entire micrographs",
        do_motion: _a.polish.DO_MOTION = False,
        sigma_vel: _a.polish.SIGMA_VEL = 0.2,
        sigma_div: _a.polish.SIGMA_DIV = 5000,
        do_sq_exp_ker: _a.polish.DO_SQ_EXP_KER = False,
        # Running
        nr_mpi: _a.running.NR_MPI = 1,
        nr_threads: _a.running.NR_THREADS = 1,
        do_queue: _a.running.DO_QUEUE = False,
        min_dedicated: _a.running.MIN_DEDICATED = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")

    @classmethod
    def setup_widgets(cls, widgets):
        @widgets["do_shift_align"].changed.connect
        def _on_do_shift_align_changed(value: bool):
            widgets["shift_align_type"].enabled = value

        _on_do_shift_align_changed(widgets["do_shift_align"].value)

        @widgets["do_motion"].changed.connect
        def _on_do_motion_changed(value: bool):
            widgets["sigma_vel"].enabled = value
            widgets["sigma_div"].enabled = value
            widgets["do_sq_exp_ker"].enabled = value

        _on_do_motion_changed(widgets["do_motion"].value)
