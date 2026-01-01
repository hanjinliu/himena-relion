from pathlib import Path
from typing import Annotated, Any, Literal

from magicgui.widgets.bases import ValueWidget
from himena_relion._job_class import _RelionBuiltinJob, parse_string
from himena_relion._job_dir import JobDirectory
from himena_relion import _configs, _annotated as _a
from himena_relion.schemas import OptimisationSetModel


class _Relion5Job(_RelionBuiltinJob):
    @classmethod
    def command_palette_title_prefix(cls):
        return "RELION 5:"


class ImportMoviesJob(_Relion5Job):
    """Import movies into RELION."""

    @classmethod
    def type_label(cls) -> str:
        return "relion.import.movies"

    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        kwargs = super().normalize_kwargs(**kwargs)
        kwargs["do_other"] = False
        kwargs["node_type"] = "Particle coordinates (*.box, *_pick.star)"
        kwargs["fn_in_other"] = ""
        kwargs["optics_group_particles"] = ""
        kwargs["do_raw"] = True
        return kwargs

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs) -> dict[str, Any]:
        kwargs = super().normalize_kwargs_inv(**kwargs)
        for name in [
            "fn_in_other", "do_other", "node_type", "optics_group_particles",
            "do_raw", "do_queue", "min_dedicated",
        ]:  # fmt: skip
            kwargs.pop(name, None)
        return kwargs

    def run(
        self,
        fn_in_raw: _a.import_.FN_IN_RAW = "",
        is_multiframe: _a.import_.IN_MULTIFRAME = True,
        optics_group_name: _a.import_.OPTICS_GROUP_NAME = "opticsGroup1",
        fn_mtf: _a.import_.FN_MTF = "",
        angpix: _a.import_.ANGPIX = 1.4,
        kV: _a.import_.KV = 300,
        Cs: _a.import_.CS = 2.7,
        Q0: _a.import_.Q0 = 0.1,
        beamtilt_x: _a.import_.BEAM_TILT_X = 0,
        beamtilt_y: _a.import_.BEAM_TILT_Y = 0,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class ImportOthersJob(_Relion5Job):
    @classmethod
    def type_label(cls) -> str:
        return "relion.import.other"

    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        kwargs = super().normalize_kwargs(**kwargs)
        kwargs["do_other"] = True
        kwargs["do_raw"] = False
        kwargs["fn_in_raw"] = ""
        kwargs["is_multiframe"] = True
        kwargs["optics_group_name"] = "opticsGroup1"
        kwargs["fn_mtf"] = ""
        kwargs["angpix"] = 1.4
        kwargs["kV"] = 300
        kwargs["Cs"] = 2.7
        kwargs["Q0"] = 0.1
        kwargs["beamtilt_x"] = 0
        kwargs["beamtilt_y"] = 0
        return kwargs

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs) -> dict[str, Any]:
        kwargs = super().normalize_kwargs_inv(**kwargs)
        for name in [
            "fn_in_raw", "is_multiframe", "optics_group_name", "fn_mtf", "angpix", "kV",
            "Cs", "Q0", "beamtilt_x", "beamtilt_y", "do_other", "do_raw", "do_queue",
            "min_dedicated",
        ]:  # fmt: skip
            kwargs.pop(name, None)
        return kwargs

    def run(
        self,
        fn_in_other: _a.import_.FN_IN_OTHER = "",
        node_type: _a.import_.NODE_TYPE = "Particle coordinates (*.box, *_pick.star)",
        optics_group_particles: _a.import_.OPTICS_GROUP_PARTICLES = "",
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class _MotionCorrJobBase(_Relion5Job):
    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        kwargs["fn_motioncor2_exe"] = _configs.get_motioncor2_exe()
        if "patch" in kwargs:
            kwargs["patch_x"], kwargs["patch_y"] = kwargs.pop("patch")
        return super().normalize_kwargs(**kwargs)

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs) -> dict[str, Any]:
        kwargs.pop("fn_motioncor2_exe", None)
        kwargs["patch"] = (kwargs.pop("patch_x", 1), kwargs.pop("patch_y", 1))
        return super().normalize_kwargs_inv(**kwargs)


class MotionCorr2Job(_MotionCorrJobBase):
    """Motion correction using MotionCor2 (GPU)."""

    @classmethod
    def type_label(cls) -> str:
        return "relion.motioncorr.motioncor2"

    @classmethod
    def job_title(cls):
        return "Motion Correction (MotionCor2)"

    @classmethod
    def normalize_kwargs(cls, **kwargs):
        kwargs["do_own_motioncor"] = False
        kwargs["do_save_ps"] = False
        return super().normalize_kwargs(**kwargs)

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs):
        kwargs = super().normalize_kwargs_inv(**kwargs)
        kwargs.pop("do_own_motioncor", None)
        kwargs.pop("do_save_ps", None)
        return kwargs

    def run(
        self,
        input_star_mics: _a.io.IN_MOVIES = "",
        first_frame_sum: _a.mcor.FIRST_FRAME_SUM = 1,
        last_frame_sum: _a.mcor.LAST_FRAME_SUM = -1,
        dose_per_frame: _a.mcor.DOSE_PER_FRAME = 1.0,
        pre_exposure: _a.mcor.PRE_EXPOSURE = 0.0,
        eer_grouping: _a.mcor.EER_FRAC = 32,
        do_float16: _a.io.DO_F16 = True,
        do_dose_weighting: _a.mcor.DO_DOSE_WEIGHTING = True,
        group_for_ps: _a.mcor.SUM_EVERY_E = 4.0,
        # Motion correction
        bfactor: _a.mcor.BFACTOR = 150,
        group_frames: _a.mcor.GROUP_FRAMES = 1,
        bin_factor: _a.mcor.BIN_FACTOR = 1,
        fn_defect: _a.mcor.DEFECT_FILE = "",
        fn_gain_ref: _a.mcor.GAIN_REF = "",
        gain_rot: _a.mcor.GAIN_ROT = "No rotation (0)",
        gain_flip: _a.mcor.GAIN_FLIP = "No flipping (0)",
        patch: _a.mcor.PATCH = (1, 1),
        gpu_ids: _a.compute.GPU_IDS = "0",
        # Running
        nr_mpi: _a.running.MPI_TYPE = 1,
        nr_threads: _a.running.THREAD_TYPE = 1,
        do_queue: _a.running.DO_QUEUE_TYPE = False,
        min_dedicated: _a.running.MIN_DEDICATED_TYPE = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class MotionCorrOwnJob(_MotionCorrJobBase):
    """Motion correction using RELION's implementation (CPU)."""

    @classmethod
    def type_label(cls) -> str:
        return "relion.motioncorr.own"

    @classmethod
    def job_title(cls):
        return "Motion Correction (RELION)"

    @classmethod
    def normalize_kwargs(cls, **kwargs):
        kwargs["do_own_motioncor"] = True
        kwargs["other_motioncor2_args"] = ""
        kwargs["gpu_ids"] = ""
        return super().normalize_kwargs(**kwargs)

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs):
        kwargs = super().normalize_kwargs_inv(**kwargs)
        kwargs.pop("do_own_motioncor", None)
        kwargs.pop("other_motioncor2_args", None)
        kwargs.pop("gpu_ids", None)
        return kwargs

    def run(
        self,
        input_star_mics: _a.io.IN_MOVIES = "",
        first_frame_sum: _a.mcor.FIRST_FRAME_SUM = 1,
        last_frame_sum: _a.mcor.LAST_FRAME_SUM = -1,
        dose_per_frame: _a.mcor.DOSE_PER_FRAME = 1.0,
        pre_exposure: _a.mcor.PRE_EXPOSURE = 0.0,
        eer_grouping: _a.mcor.EER_FRAC = 32,
        do_float16: _a.io.DO_F16 = True,
        do_dose_weighting: _a.mcor.DO_DOSE_WEIGHTING = True,
        do_save_noDW: _a.mcor.DO_SAVE_NO_DW = False,
        do_save_ps: _a.mcor.DO_SAVE_PS = True,
        group_for_ps: _a.mcor.SUM_EVERY_E = 4.0,
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
        nr_mpi: _a.running.MPI_TYPE = 1,
        nr_threads: _a.running.THREAD_TYPE = 1,
        do_queue: _a.running.DO_QUEUE_TYPE = False,
        min_dedicated: _a.running.MIN_DEDICATED_TYPE = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")

    @classmethod
    def setup_widgets(cls, widgets: dict[str, ValueWidget]) -> None:
        @widgets["do_save_ps"].changed.connect
        def _on_do_float16_changed(value: bool):
            widgets["group_for_ps"].enabled = not value

        _on_do_float16_changed(widgets["do_save_ps"].value)  # initialize


class CtfEstimationJob(_Relion5Job):
    """Contrast transfer function (CTF) estimation using CTFFIND4."""

    @classmethod
    def type_label(cls) -> str:
        return "relion.ctffind.ctffind4"

    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        kwargs["fn_ctffind_exe"] = _configs.get_ctffind4_exe()
        if "phase_range" in kwargs:
            kwargs["phase_min"], kwargs["phase_max"], kwargs["phase_step"] = kwargs.pop(
                "phase_range"
            )
        if "dfrange" in kwargs:
            kwargs["dfmin"], kwargs["dfmax"], kwargs["dfstep"] = kwargs.pop("dfrange")
        return super().normalize_kwargs(**kwargs)

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs) -> dict[str, Any]:
        kwargs.pop("fn_ctffind_exe", None)
        kwargs["phase_range"] = (
            kwargs.pop("phase_min", 0),
            kwargs.pop("phase_max", 180),
            kwargs.pop("phase_step", 10),
        )
        kwargs["dfrange"] = (
            kwargs.pop("dfmin", 5000),
            kwargs.pop("dfmax", 50000),
            kwargs.pop("dfstep", 500),
        )
        return super().normalize_kwargs_inv(**kwargs)

    def run(
        self,
        # I/O
        input_star_mics: _a.io.IN_MICROGRAPHS = "",
        use_noDW: _a.ctffind.USE_NODW = False,
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
        # Running
        nr_mpi: _a.running.MPI_TYPE = 1,
        do_queue: _a.running.DO_QUEUE_TYPE = False,
        min_dedicated: _a.running.MIN_DEDICATED_TYPE = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")

    @classmethod
    def setup_widgets(cls, widgets: dict[str, ValueWidget]) -> None:
        @widgets["do_phaseshift"].changed.connect
        def _on_do_phaseshift_changed(value: bool):
            widgets["phase_range"].enabled = value

        widgets["phase_range"].enabled = False


class ManualPickJob(_Relion5Job):
    """Manual particle picking."""

    @classmethod
    def type_label(cls) -> str:
        return "relion.manualpick"

    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        kwargs = super().normalize_kwargs(**kwargs)
        filter_method = kwargs.pop("filter_method", "Band-pass")
        kwargs["do_topaz_denoise"] = filter_method == "Topaz"
        kwargs["do_fom_threshold"] = kwargs["minimum_pick_fom"] is not None
        if kwargs["minimum_pick_fom"] is None:
            kwargs["minimum_pick_fom"] = 0
        return kwargs

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs) -> dict[str, Any]:
        kwargs = super().normalize_kwargs_inv(**kwargs)
        kwargs["filter_method"] = (
            "Topaz" if kwargs.pop("do_topaz_denoise", False) else "Band-pass"
        )
        if not kwargs.pop("do_fom_threshold", False):
            kwargs["minimum_pick_fom"] = None
        for name in ["do_queue", "min_dedicated"]:
            kwargs.pop(name, None)
        return kwargs

    def run(
        self,
        fn_in: _a.io.IN_MICROGRAPHS = "",
        do_startend: Annotated[
            bool, {"label": "Pick star-end coordinates helices", "group": "I/O"}
        ] = False,
        minimum_pick_fom: Annotated[
            float | None,
            {"label": "Minimum autopick FOM", "min": -10, "max": 10, "group": "I/O"},
        ] = None,
        # Display
        diameter: Annotated[
            float, {"label": "Particle diameter (A)", "group": "Display"}
        ] = 100,
        micscale: Annotated[
            float, {"label": "Scale for micrographs", "group": "Display"}
        ] = 0.2,
        sigma_contrast: Annotated[
            float, {"label": "Sigma contrast", "group": "Display"}
        ] = 3,
        white_val: Annotated[float, {"label": "White value", "group": "Display"}] = 0,
        black_val: Annotated[float, {"label": "Black value", "group": "Display"}] = 0,
        angpix: Annotated[float, {"label": "Pixel size (A)", "group": "Display"}] = -1,
        filter_method: Annotated[
            str,
            {
                "label": "Denoising method",
                "choices": ["Band-pass", "Topaz"],
                "group": "Display",
            },
        ] = "Band-pass",
        lowpass: Annotated[
            float, {"label": "Lowpass filter (A)", "group": "Display"}
        ] = 20,
        highpass: Annotated[
            float, {"label": "Highpass filter (A)", "group": "Display"}
        ] = -1,
        # Colors
        do_color: Annotated[
            bool, {"label": "Color particles by metadata", "group": "Colors"}
        ] = False,
        color_label: Annotated[
            str, {"label": "Color by this label", "group": "Colors"}
        ] = "rlnAutopickFigureOfMerit",
        fn_color: Annotated[
            str, {"label": "STAR file with color label", "group": "Colors"}
        ] = "",
        blue_value: Annotated[float, {"label": "Blue value", "group": "Colors"}] = 0,
        red_value: Annotated[float, {"label": "Red value", "group": "Colors"}] = 2,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")

    @classmethod
    def setup_widgets(cls, widgets):
        @widgets["filter_method"].changed.connect
        def _on_filter_method_changed(value: str):
            widgets["lowpass"].enabled = value == "Band-pass"
            widgets["highpass"].enabled = value == "Band-pass"

        _on_filter_method_changed(widgets["filter_method"].value)  # initialize


class _AutoPickJob(_Relion5Job):
    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        kwargs = super().normalize_kwargs(**kwargs)
        kwargs["continue_manual"] = False
        # template pick
        for key, value in [
            ("do_refs", False),
            ("fn_refs_autopick", ""),
            ("do_ref3d", False),
            ("fn_ref3d_autopick", ""),
            ("ref3d_symmetry", "C1"),
            ("ref3d_sampling", "30 degrees"),
            ("lowpass", 20),
            ("highpass", -1),
            ("angpix_ref", -1),
            ("psi_sampling_autopick", 5),
            ("do_invert_refs", True),
            ("do_ctf_autopick", True),
            ("do_ignore_first_ctfpeak_autopick", False),
            # LoG
            ("do_log", False),
            ("log_diam_min", 200),
            ("log_diam_max", 250),
            ("log_invert", False),
            ("log_maxres", 20),
            ("log_adjust_thr", 0),
            ("log_upper_thr", 999),
            # Topaz
            ("do_topaz", False),
            ("do_topaz_filaments", False),
            ("do_topaz_pick", False),
            ("do_topaz_train", False),
            ("do_topaz_train_parts", False),
            ("fn_topaz_exe", "relion_python_topaz"),
            ("topaz_filament_threshold", -5),
            ("topaz_hough_length", -1),
            ("topaz_model", ""),
            ("topaz_nr_particles", -1),
            ("topaz_other_args", ""),
            ("topaz_particle_diameter", -1),
            ("topaz_train_parts", ""),
            ("topaz_train_picks", ""),
        ]:
            kwargs.setdefault(key, value)

        # others
        kwargs["use_gpu"] = kwargs["gpu_ids"] != ""
        return kwargs

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs):
        kwargs = super().normalize_kwargs_inv(**kwargs)
        kwargs.pop("use_gpu", None)
        return kwargs


class AutoPickLogJob(_AutoPickJob):
    """Automatic particle picking using Laplacian of Gaussian filter."""

    @classmethod
    def type_label(cls) -> str:
        return "relion.autopick.log"

    @classmethod
    def job_title(cls):
        return "LoG Pick"

    @classmethod
    def normalize_kwargs(cls, **kwargs):
        kwargs["gpu_ids"] = ""
        kwargs["do_log"] = True
        kwargs["minavgnoise_autopick"] = -999
        kwargs["maxstddevnoise_autopick"] = 1.1  # ignored in LoG picker
        kwargs["mindist_autopick"] = 100  # ignored in LoG picker
        kwargs["threshold_autopick"] = 0.05
        kwargs["shrink"] = 0
        kwargs = super().normalize_kwargs(**kwargs)
        return kwargs

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs):
        kwargs = super().normalize_kwargs_inv(**kwargs)
        keys_to_pop = [
            "continue_manual", "minavgnoise_autopick", "do_log", "do_ref3d", "do_refs",
            "log_upper_thr", "angpix_ref", "do_ctf_autopick",
            "do_ignore_first_ctfpeak_autopick", "do_invert_refs", "fn_ref3d_autopick",
            "fn_refs_autopick", "fn_topaz_exe", "highpass", "lowpass", "shrink",
            "psi_sampling_autopick", "ref3d_sampling", "ref3d_symmetry", "gpu_ids",
            "maxstddevnoise_autopick", "mindist_autopick", "threshold_autopick"
        ]  # fmt: skip
        for key in kwargs:
            if key.startswith(("do_topaz", "topaz_")):
                keys_to_pop.append(key)
        for key in keys_to_pop:
            kwargs.pop(key, None)
        return kwargs

    def run(
        self,
        fn_input_autopick: _a.io.IN_MICROGRAPHS = "",
        angpix: _a.autopick.ANGPIX = -1,
        # Laplacian
        log_diam_min: _a.autopick.LOG_DIAM_MIN = 200,
        log_diam_max: _a.autopick.LOG_DIAM_MAX = 250,
        log_invert: _a.autopick.LOG_INVERT = False,
        log_maxres: _a.autopick.LOG_MAXRES = 20,
        log_adjust_thr: _a.autopick.LOG_ADJUST_THR = 0,
        log_upper_thr: _a.autopick.LOG_UPPER_THR = 999,
        # Autopicking
        do_write_fom_maps: _a.autopick.DO_WHITE_FOM_MAPS = False,
        do_read_fom_maps: _a.autopick.DO_READ_FOM_MAPS = False,
        gpu_ids: _a.compute.GPU_IDS = "",
        # Helical
        do_pick_helical_segments: _a.autopick.DO_PICK_HELICAL_SEGMENTS = False,
        helical_tube_outer_diameter: _a.helix.HELICAL_TUBE_DIAMETER = 200,
        helical_tube_length_min: _a.autopick.HELICAL_TUBE_LENGTH_MIN = -1,
        helical_tube_kappa_max: _a.autopick.HELICAL_TUBE_KAPPA_MAX = 0.1,
        helical_nr_asu: _a.helix.HELICAL_NR_ASU = 1,
        helical_rise: _a.helix.HELICAL_RISE = -1,
        do_amyloid: _a.autopick.DO_AMYLOID = False,
        # Running
        nr_mpi: _a.running.MPI_TYPE = 1,
        do_queue: _a.running.DO_QUEUE_TYPE = False,
        min_dedicated: _a.running.MIN_DEDICATED_TYPE = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class AutoPickTemplate2DJob(_AutoPickJob):
    """Automatic particle picking using template matching."""

    @classmethod
    def type_label(cls) -> str:
        return "relion.autopick.ref2d"

    @classmethod
    def job_title(cls):
        return "Template Pick (2D Reference)"

    @classmethod
    def normalize_kwargs(cls, **kwargs):
        kwargs = super().normalize_kwargs(**kwargs)
        kwargs["do_refs"] = True
        kwargs["do_ref3d"] = False
        return kwargs

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs):
        kwargs = super().normalize_kwargs_inv(**kwargs)
        keys_to_pop = [
            "continue_manual",
            "do_log",
            "do_ref3d",
            "do_refs",
            "fn_ref3d_autopick",
            "ref3d_sampling",
            "ref3d_symmetry",
            "fn_topaz_exe",
        ]
        for key in kwargs:
            if key.startswith(("do_topaz", "topaz_", "log_")):
                keys_to_pop.append(key)
        for key in keys_to_pop:
            kwargs.pop(key, None)
        return kwargs

    def run(
        self,
        fn_input_autopick: _a.io.IN_MICROGRAPHS = "",
        angpix: _a.autopick.ANGPIX = -1,
        # References
        fn_refs_autopick: _a.autopick.FN_REFS_AUTOPICK = "",
        lowpass: _a.autopick.LOWPASS = 20,
        highpass: _a.autopick.HIGHPASS = -1,
        angpix_ref: _a.autopick.ANGPIX_REF = -1,
        psi_sampling_autopick: _a.autopick.PSI_SAMPLING_AUTOPICK = 5,
        do_invert_refs: _a.autopick.DO_INVERT_REFS = True,
        do_ctf_autopick: _a.autopick.DO_CTF_AUTOPICK = True,
        do_ignore_first_ctfpeak_autopick: _a.autopick.DO_IGNORE_FIRST_CTFPEAK_AUTOPICK = False,
        # Autopicking
        threshold_autopick: _a.autopick.THRESHOLD_AUTOPICK = 0.05,
        mindist_autopick: _a.autopick.MINDIST_AUTOPICK = 100,
        maxstddevnoise_autopick: _a.autopick.MAXSTDDEVNOISE_AUTOPICK = 1.1,
        minavgnoise_autopick: _a.autopick.MINAVGNOISE_AUOTPICK = -999,
        do_write_fom_maps: _a.autopick.DO_WHITE_FOM_MAPS = False,
        do_read_fom_maps: _a.autopick.DO_READ_FOM_MAPS = False,
        shrink: _a.autopick.SHRINK = 0,
        gpu_ids: _a.compute.GPU_IDS = "",
        # Helical
        do_pick_helical_segments: _a.autopick.DO_PICK_HELICAL_SEGMENTS = False,
        helical_tube_outer_diameter: _a.helix.HELICAL_TUBE_DIAMETER = 200,
        helical_tube_length_min: _a.autopick.HELICAL_TUBE_LENGTH_MIN = -1,
        helical_tube_kappa_max: _a.autopick.HELICAL_TUBE_KAPPA_MAX = 0.1,
        helical_nr_asu: _a.helix.HELICAL_NR_ASU = 1,
        helical_rise: _a.helix.HELICAL_RISE = -1,
        do_amyloid: _a.autopick.DO_AMYLOID = False,
        # Running
        nr_mpi: _a.running.MPI_TYPE = 1,
        do_queue: _a.running.DO_QUEUE_TYPE = False,
        min_dedicated: _a.running.MIN_DEDICATED_TYPE = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class AutoPickTemplate3DJob(_AutoPickJob):
    @classmethod
    def type_label(cls) -> str:
        return "relion.autopick.ref3d"

    @classmethod
    def job_title(cls):
        return "Template Pick (3D Reference)"

    @classmethod
    def normalize_kwargs(cls, **kwargs):
        kwargs = super().normalize_kwargs(**kwargs)
        kwargs["do_refs"] = kwargs["do_ref3d"] = True
        kwargs["fn_refs_autopick"] = ""
        return kwargs

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs):
        kwargs = super().normalize_kwargs_inv(**kwargs)
        keys_to_pop = [
            "continue_manual",
            "do_log",
            "do_ref3d",
            "do_refs",
            "log_upper_thr",
            "fn_topaz_exe",
            "fn_refs_autopick",
        ]
        for key in kwargs:
            if key.startswith(("do_topaz", "topaz_", "log_")):
                keys_to_pop.append(key)
        for key in keys_to_pop:
            kwargs.pop(key, None)
        return kwargs

    def run(
        self,
        fn_input_autopick: _a.io.IN_MICROGRAPHS = "",
        fn_ref3d_autopick: _a.io.REF_TYPE = "",
        angpix: _a.autopick.ANGPIX = -1,
        # References
        ref3d_symmetry: _a.autopick.REF3D_SYMMETRY = "C1",
        ref3d_sampling: _a.autopick.REF3D_SAMPLING = "30 degrees",
        lowpass: _a.autopick.LOWPASS = 20,
        highpass: _a.autopick.HIGHPASS = -1,
        angpix_ref: _a.autopick.ANGPIX_REF = -1,
        psi_sampling_autopick: _a.autopick.PSI_SAMPLING_AUTOPICK = 5,
        do_invert_refs: _a.autopick.DO_INVERT_REFS = True,
        do_ctf_autopick: _a.autopick.DO_CTF_AUTOPICK = True,
        do_ignore_first_ctfpeak_autopick: _a.autopick.DO_IGNORE_FIRST_CTFPEAK_AUTOPICK = False,
        # Autopicking
        threshold_autopick: _a.autopick.THRESHOLD_AUTOPICK = 0.05,
        mindist_autopick: _a.autopick.MINDIST_AUTOPICK = 100,
        maxstddevnoise_autopick: _a.autopick.MAXSTDDEVNOISE_AUTOPICK = 1.1,
        minavgnoise_autopick: _a.autopick.MINAVGNOISE_AUOTPICK = -999,
        do_write_fom_maps: _a.autopick.DO_WHITE_FOM_MAPS = False,
        do_read_fom_maps: _a.autopick.DO_READ_FOM_MAPS = False,
        shrink: _a.autopick.SHRINK = 0,
        gpu_ids: _a.compute.GPU_IDS = "",
        # Helical
        do_pick_helical_segments: _a.autopick.DO_PICK_HELICAL_SEGMENTS = False,
        helical_tube_outer_diameter: _a.helix.HELICAL_TUBE_DIAMETER = 200,
        helical_tube_length_min: _a.autopick.HELICAL_TUBE_LENGTH_MIN = -1,
        helical_tube_kappa_max: _a.autopick.HELICAL_TUBE_KAPPA_MAX = 0.1,
        helical_nr_asu: _a.helix.HELICAL_NR_ASU = 1,
        helical_rise: _a.helix.HELICAL_RISE = -1,
        do_amyloid: _a.autopick.DO_AMYLOID = False,
        # Running
        nr_mpi: _a.running.MPI_TYPE = 1,
        do_queue: _a.running.DO_QUEUE_TYPE = False,
        min_dedicated: _a.running.MIN_DEDICATED_TYPE = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")

    @classmethod
    def setup_widgets(cls, widgets):
        @widgets["do_pick_helical_segments"].changed.connect
        def _on_do_pick_helical_segments_changed(value: bool):
            widgets["helical_tube_outer_diameter"].enabled = value
            widgets["helical_tube_length_min"].enabled = value
            widgets["helical_tube_kappa_max"].enabled = value
            widgets["helical_nr_asu"].enabled = value
            widgets["helical_rise"].enabled = value
            widgets["do_amyloid"].enabled = value

        _on_do_pick_helical_segments_changed(
            widgets["do_pick_helical_segments"].value
        )  # initialize


class AutoPickTopazTrain(_AutoPickJob):
    @classmethod
    def type_label(cls) -> str:
        return "relion.autopick.topaz.train"

    @classmethod
    def job_title(cls):
        return "Topaz Train"

    @classmethod
    def normalize_kwargs(cls, **kwargs):
        kwargs = super().normalize_kwargs(**kwargs)
        kwargs["do_topaz"] = True
        kwargs["do_topaz_train"] = True
        kwargs["fn_topaz_exe"] = _configs.get_topaz_exe()
        return kwargs

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs):
        kwargs = super().normalize_kwargs_inv(**kwargs)
        kwargs.pop("fn_topaz_exe", None)
        return kwargs

    def run(
        self,
        fn_input_autopick: _a.io.IN_MICROGRAPHS = "",
        angpix: _a.autopick.ANGPIX = -1,
        # Topaz
        topaz_particle_diameter: _a.autopick.TOPAZ_PARTICLE_DIAMETER = -1,
        topaz_nr_particles: _a.autopick.TOPAZ_NR_PARTICLES = -1,
        do_topaz_train_parts: _a.autopick.DO_TOPAZ_TRAIN_PARTS = False,
        topaz_train_picks: _a.autopick.TOPAZ_TRAIN_PICKS = "",
        topaz_train_parts: _a.autopick.TOPAZ_TRAIN_PARTS = "",
        # Autopicking
        threshold_autopick: _a.autopick.THRESHOLD_AUTOPICK = 0.05,
        mindist_autopick: _a.autopick.MINDIST_AUTOPICK = 100,
        maxstddevnoise_autopick: _a.autopick.MAXSTDDEVNOISE_AUTOPICK = 1.1,
        do_write_fom_maps: _a.autopick.DO_WHITE_FOM_MAPS = False,
        do_read_fom_maps: _a.autopick.DO_READ_FOM_MAPS = False,
        shrink: _a.autopick.SHRINK = 0,
        gpu_ids: _a.compute.GPU_IDS = "",
        # Helical
        do_pick_helical_segments: _a.autopick.DO_PICK_HELICAL_SEGMENTS = False,
        helical_tube_outer_diameter: _a.helix.HELICAL_TUBE_DIAMETER = 200,
        helical_tube_length_min: _a.autopick.HELICAL_TUBE_LENGTH_MIN = -1,
        helical_tube_kappa_max: _a.autopick.HELICAL_TUBE_KAPPA_MAX = 0.1,
        helical_nr_asu: _a.helix.HELICAL_NR_ASU = 1,
        helical_rise: _a.helix.HELICAL_RISE = -1,
        do_amyloid: _a.autopick.DO_AMYLOID = False,
        # Running
        nr_mpi: _a.running.MPI_TYPE = 1,
        do_queue: _a.running.DO_QUEUE_TYPE = False,
        min_dedicated: _a.running.MIN_DEDICATED_TYPE = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")

    @classmethod
    def setup_widgets(cls, widgets: dict[str, ValueWidget]) -> None:
        @widgets["do_topaz_train_parts"].changed.connect
        def _on_do_topaz_train_parts_changed(value: bool):
            widgets["topaz_train_parts"].enabled = value
            widgets["topaz_train_picks"].enabled = not value

        _on_do_topaz_train_parts_changed(
            widgets["do_topaz_train_parts"].value
        )  # initialize


class AutoPickTopazPick(_AutoPickJob):
    @classmethod
    def type_label(cls) -> str:
        return "relion.autopick.topaz.pick"

    @classmethod
    def job_title(cls):
        return "Topaz Pick"

    @classmethod
    def normalize_kwargs(cls, **kwargs):
        kwargs = super().normalize_kwargs(**kwargs)
        kwargs["do_topaz"] = True
        kwargs["do_topaz_pick"] = True
        kwargs["fn_topaz_exe"] = _configs.get_topaz_exe()
        return kwargs

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs):
        kwargs = super().normalize_kwargs_inv(**kwargs)
        kwargs.pop("fn_topaz_exe", None)
        return kwargs

    def run(
        self,
        fn_input_autopick: _a.io.IN_MICROGRAPHS = "",
        angpix: _a.autopick.ANGPIX = -1,
        # Topaz
        topaz_particle_diameter: _a.autopick.TOPAZ_PARTICLE_DIAMETER = -1,
        topaz_model: _a.autopick.TOPAZ_MODEL = "",
        do_topaz_filaments: _a.autopick.DO_TOPAZ_FILAMENTS = False,
        topaz_filament_threshold: _a.autopick.TOPAZ_FILAMENT_THRESHOLD = -5,
        topaz_hough_length: _a.autopick.TOPAZ_HOUGH_LENGTH = -1,
        topaz_other_args: _a.autopick.TOPAZ_OTHER_ARGS = "",
        # Autopicking
        threshold_autopick: _a.autopick.THRESHOLD_AUTOPICK = 0.05,
        mindist_autopick: _a.autopick.MINDIST_AUTOPICK = 100,
        maxstddevnoise_autopick: _a.autopick.MAXSTDDEVNOISE_AUTOPICK = 1.1,
        do_write_fom_maps: _a.autopick.DO_WHITE_FOM_MAPS = False,
        do_read_fom_maps: _a.autopick.DO_READ_FOM_MAPS = False,
        shrink: _a.autopick.SHRINK = 0,
        gpu_ids: _a.compute.GPU_IDS = "",
        # Helical
        do_pick_helical_segments: _a.autopick.DO_PICK_HELICAL_SEGMENTS = False,
        helical_tube_outer_diameter: _a.helix.HELICAL_TUBE_DIAMETER = 200,
        helical_tube_length_min: _a.autopick.HELICAL_TUBE_LENGTH_MIN = -1,
        helical_tube_kappa_max: _a.autopick.HELICAL_TUBE_KAPPA_MAX = 0.1,
        helical_nr_asu: _a.helix.HELICAL_NR_ASU = 1,
        helical_rise: _a.helix.HELICAL_RISE = -1,
        do_amyloid: _a.autopick.DO_AMYLOID = False,
        # Running
        nr_mpi: _a.running.MPI_TYPE = 1,
        do_queue: _a.running.DO_QUEUE_TYPE = False,
        min_dedicated: _a.running.MIN_DEDICATED_TYPE = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class ExtractJobBase(_Relion5Job):
    @classmethod
    def normalize_kwargs(cls, **kwargs):
        kwargs = super().normalize_kwargs(**kwargs)

        # common defaults
        for key, value in [
            ("star_mics", ""),
            ("coords_suffix", ""),
            ("do_reextract", False),
            ("fndata_reextract", ""),
            ("do_reset_offsets", False),
            ("do_recenter", True),
        ]:
            kwargs.setdefault(key, value)

        kwargs["recenter_x"], kwargs["recenter_y"], kwargs["recenter_z"] = (0, 0, 0)

        # normalize
        kwargs["do_rescale"] = kwargs["extract_size"] != kwargs.get(
            "rescale", (0, 0, 0)
        )
        kwargs["do_fom_threshold"] = kwargs.get("minimum_pick_fom", None) is not None
        if kwargs["minimum_pick_fom"] is None:
            kwargs["minimum_pick_fom"] = 0.0
        return kwargs

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs):
        kwargs = super().normalize_kwargs_inv(**kwargs)
        kwargs.pop("do_reextract", None)
        kwargs.pop("do_recenter", None)
        if kwargs.pop("do_fom_threshold", False):
            pass
        else:
            kwargs["minimum_pick_fom"] = None
        return kwargs

    @classmethod
    def setup_widgets(cls, widgets):
        @widgets["do_extract_helix"].changed.connect
        def _on_do_extract_helix_changed(value: bool):
            for name in [
                "helical_tube_outer_diameter",
                "helical_bimodal_angular_priors",
                "do_extract_helical_tubes",
                "do_cut_into_segments",
                "helical_nr_asu",
                "helical_rise",
            ]:
                widgets[name].enabled = value

        _on_do_extract_helix_changed(widgets["do_extract_helix"].value)  # initialize


class ExtractJob(ExtractJobBase):
    """Particle extraction from micrographs."""

    @classmethod
    def type_label(cls) -> str:
        return "relion.extract"

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs):
        kwargs = super().normalize_kwargs_inv(**kwargs)
        for name in [
            "fndata_reextract",
            "do_reset_offsets",
            "do_recenter",
            "recenter_x",
            "recenter_y",
            "recenter_z",
            "do_rescale",
        ]:
            kwargs.pop(name, None)
        return kwargs

    def run(
        self,
        # I/O
        star_mics: _a.io.IN_MICROGRAPHS = "",
        coords_suffix: _a.io.IN_COORDINATES = "",
        do_float16: _a.mcor.DO_F16 = True,
        # Extract
        extract_size: _a.extract.SIZE = 128,
        rescale: _a.extract.DO_RESCALE = 128,
        do_invert: _a.extract.DO_INVERT = True,
        do_norm: _a.extract.DO_NORM = True,
        bg_diameter: _a.extract.DIAMETER = -1,
        white_dust: _a.extract.WIGHT_DUST = -1,
        black_dust: _a.extract.BLACK_DUST = -1,
        minimum_pick_fom: _a.extract.MINIMUM_PICK_FOM = None,
        # Helix
        do_extract_helix: _a.helix.DO_HELIX = False,
        helical_tube_outer_diameter: _a.helix.HELICAL_TUBE_DIAMETER = 200,
        helical_bimodal_angular_priors: _a.extract.HELICAL_BIMODAL_ANGULAR_PRIORS = True,
        do_extract_helical_tubes: _a.extract.DO_EXTRACT_HELICAL_TUBES = True,
        do_cut_into_segments: _a.extract.DO_CUT_INTO_SEGMENTS = True,
        helical_nr_asu: _a.helix.HELICAL_NR_ASU = 1,
        helical_rise: _a.helix.HELICAL_RISE = 1,
        # Running
        nr_mpi: _a.running.MPI_TYPE = 1,
        do_queue: _a.running.DO_QUEUE_TYPE = False,
        min_dedicated: _a.running.MIN_DEDICATED_TYPE = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class ReExtractJob(ExtractJobBase):
    """Particle re-extraction from micrographs."""

    @classmethod
    def type_label(cls) -> str:
        return "relion.extract.reextract"

    @classmethod
    def normalize_kwargs(cls, **kwargs):
        kwargs = super().normalize_kwargs(**kwargs)
        kwargs["do_reextract"] = True
        return kwargs

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs):
        kwargs = super().normalize_kwargs_inv(**kwargs)
        for name in ["coords_suffix", "do_rescale"]:
            kwargs.pop(name, None)
        kwargs["recenter"] = tuple(kwargs.pop(f"recenter_{x}", 0) for x in "xyz")
        return kwargs

    def run(
        self,
        # I/O
        star_mics: _a.io.IN_MICROGRAPHS = "",
        fndata_reextract: _a.io.IN_PARTICLES = "",
        do_reset_offsets: _a.extract.DO_RESET_OFFSET = False,
        do_recenter: _a.extract.DO_RECENTER = True,
        recenter: _a.extract.RECENTER = (0, 0, 0),
        do_float16: _a.io.DO_F16 = True,
        # Extract
        extract_size: _a.extract.SIZE = 128,
        rescale: _a.extract.DO_RESCALE = 128,
        do_invert: _a.extract.DO_INVERT = True,
        do_norm: _a.extract.DO_NORM = True,
        bg_diameter: _a.extract.DIAMETER = -1,
        white_dust: _a.extract.WIGHT_DUST = -1,
        black_dust: _a.extract.BLACK_DUST = -1,
        minimum_pick_fom: _a.extract.MINIMUM_PICK_FOM = None,
        # Helix
        do_extract_helix: _a.helix.DO_HELIX = False,
        helical_tube_outer_diameter: _a.helix.HELICAL_TUBE_DIAMETER = 200,
        helical_bimodal_angular_priors: _a.extract.HELICAL_BIMODAL_ANGULAR_PRIORS = True,
        do_extract_helical_tubes: _a.extract.DO_EXTRACT_HELICAL_TUBES = True,
        do_cut_into_segments: _a.extract.DO_CUT_INTO_SEGMENTS = True,
        helical_nr_asu: _a.helix.HELICAL_NR_ASU = 1,
        helical_rise: _a.helix.HELICAL_RISE = 1,
        # Running
        nr_mpi: _a.running.MPI_TYPE = 1,
        do_queue: _a.running.DO_QUEUE_TYPE = False,
        min_dedicated: _a.running.MIN_DEDICATED_TYPE = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class Class2DJob(_Relion5Job):
    @classmethod
    def type_label(cls) -> str:
        return "relion.class2d"

    @classmethod
    def normalize_kwargs(cls, **kwargs):
        kwargs = super().normalize_kwargs(**kwargs)
        kwargs["fn_cont"] = ""

        if "offset_range_step" in kwargs:
            rng, step = kwargs.pop("offset_range_step")
            kwargs["offset_range"], kwargs["offset_step"] = rng, step

        algo = kwargs.pop("algorithm")
        if algo["algorithm"] == "EM":
            kwargs["do_em"] = True
            kwargs["do_grad"] = False
            kwargs["nr_iter_em"] = algo["niter"]
            kwargs.setdefault("n_iter_grad", 200)
        else:
            kwargs["do_em"] = False
            kwargs["do_grad"] = True
            kwargs["nr_iter_grad"] = algo["niter"]
            kwargs.setdefault("nr_iter_em", 25)
        return kwargs

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs):
        kwargs = super().normalize_kwargs_inv(**kwargs)
        nr_iter_em = kwargs.pop("nr_iter_em", 25)
        nr_iter_grad = kwargs.pop("nr_iter_grad", 200)
        if kwargs.pop("do_em", False):
            kwargs["algorithm"] = {
                "algorithm": "EM",
                "niter": nr_iter_em,
            }
        else:
            kwargs["algorithm"] = {
                "algorithm": "VDAM",
                "niter": nr_iter_grad,
            }

        kwargs["offset_range_step"] = (
            kwargs.pop("offset_range", 5),
            kwargs.pop("offset_step", 1),
        )
        # remove internal
        kwargs.pop("do_grad", None)
        kwargs.pop("fn_cont", None)
        return kwargs

    def run(
        self,
        # I/O
        fn_img: _a.io.IN_PARTICLES = "",
        # CTF
        do_ctf_correction: _a.misc.DO_CTF = True,
        ctf_intact_first_peak: _a.misc.IGNORE_CTF = False,
        # Optimisation
        nr_classes: _a.class_.NUM_CLASS = 50,
        tau_fudge: _a.misc.TAU_FUDGE = 2,
        algorithm: _a.class_.OPTIM_ALGORIGHM = {"algorithm": "VDAM", "niter": 200},
        particle_diameter: _a.misc.MASK_DIAMETER = 200,
        do_zero_mask: _a.misc.MASK_WITH_ZEROS = True,
        highres_limit: _a.class_.HIGH_RES_LIMIT = -1,
        do_center: _a.class_.DO_CENTER = True,
        # Sampling
        dont_skip_align: _a.sampling.DONT_SKIP_ALIGN = True,
        psi_sampling: _a.class_.PSI_SAMPLING = 6,
        offset_range_step: _a.sampling.OFFSET_RANGE_STEP = (5, 1),
        allow_coarser: _a.sampling.ALLOW_COARSER_SAMPLING = False,
        # Helix
        do_helix: _a.class_.DO_HELIX = False,
        helical_tube_outer_diameter: _a.helix.HELICAL_TUBE_DIAMETER = 200,
        do_bimodal_psi: _a.class_.DO_BIMODAL_PSI = True,
        range_psi: _a.class_.RANGE_PSI = 6.0,
        do_restrict_xoff: _a.class_.DO_RESTRICT_XOFF = True,
        helical_rise: _a.helix.HELICAL_RISE = 4.75,
        # Compute
        do_parallel_discio: _a.compute.USE_PARALLEL_DISC_IO = True,
        nr_pool: _a.compute.NUM_POOL = 3,
        do_preread_images: _a.compute.DO_PREREAD = False,
        use_scratch: _a.compute.USE_SCRATCH = False,
        do_combine_thru_disc: _a.compute.DO_COMBINE_THRU_DISC = False,
        gpu_ids: _a.compute.GPU_IDS = "",
        # Running
        nr_mpi: _a.running.MPI_TYPE = 1,
        nr_threads: _a.running.THREAD_TYPE = 1,
        do_queue: _a.running.DO_QUEUE_TYPE = False,
        min_dedicated: _a.running.MIN_DEDICATED_TYPE = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")

    @classmethod
    def setup_widgets(cls, widgets):
        @widgets["do_helix"].changed.connect
        def _on_do_helix_changed(value: bool):
            widgets["helical_tube_outer_diameter"].enabled = value
            widgets["do_bimodal_psi"].enabled = value
            widgets["range_psi"].enabled = value
            widgets["do_restrict_xoff"].enabled = value
            widgets["helical_rise"].enabled = value

        _on_do_helix_changed(widgets["do_helix"].value)  # initialize


class InitialModelJob(_Relion5Job):
    @classmethod
    def type_label(cls) -> str:
        return "relion.initialmodel"

    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        kwargs["fn_cont"] = ""
        return super().normalize_kwargs(**kwargs)

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs) -> dict[str, Any]:
        kwargs.pop("fn_cont", None)
        return super().normalize_kwargs_inv(**kwargs)

    def run(
        self,
        fn_img: _a.io.IN_PARTICLES = None,
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
        # Compute
        do_parallel_discio: _a.compute.USE_PARALLEL_DISC_IO = True,
        nr_pool: _a.compute.NUM_POOL = 3,
        do_preread_images: _a.compute.DO_PREREAD = False,
        use_scratch: _a.compute.USE_SCRATCH = False,
        do_combine_thru_disc: _a.compute.DO_COMBINE_THRU_DISC = False,
        gpu_ids: _a.compute.GPU_IDS = "",
        # Running
        nr_mpi: _a.running.MPI_TYPE = 1,
        nr_threads: _a.running.THREAD_TYPE = 1,
        do_queue: _a.running.DO_QUEUE_TYPE = False,
        min_dedicated: _a.running.MIN_DEDICATED_TYPE = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")

    @classmethod
    def setup_widgets(cls, widgets):
        @widgets["do_ctf_correction"].changed.connect
        def _on_do_ctf_correction_changed(value: bool):
            widgets["ctf_intact_first_peak"].enabled = value

        widgets["ctf_intact_first_peak"].enabled = widgets["do_ctf_correction"].value


class _Class3DJobBase(_Relion5Job):
    """3D classification."""

    @classmethod
    def type_label(cls) -> str:
        return "relion.class3d"

    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        if "helical_twist_range" in kwargs:
            (
                kwargs["helical_twist_min"],
                kwargs["helical_twist_max"],
                kwargs["helical_twist_inistep"],
            ) = kwargs.pop("helical_twist_range")
        if "helical_rise_range" in kwargs:
            (
                kwargs["helical_rise_min"],
                kwargs["helical_rise_max"],
                kwargs["helical_rise_inistep"],
            ) = kwargs.pop("helical_rise_range")
        if "rot_tilt_psi_range" in kwargs:
            kwargs["range_rot"], kwargs["range_tilt"], kwargs["range_psi"] = kwargs.pop(
                "rot_tilt_psi_range"
            )
        if "helical_tube_diameter_range" in kwargs:
            (
                kwargs["helical_tube_inner_diameter"],
                kwargs["helical_tube_outer_diameter"],
            ) = kwargs.pop("helical_tube_diameter_range")
        if "offset_range_step" in kwargs:
            kwargs["offset_range"], kwargs["offset_step"] = kwargs.pop(
                "offset_range_step"
            )
        kwargs["fn_cont"] = ""
        return super().normalize_kwargs(**kwargs)

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs) -> dict[str, Any]:
        kwargs["helical_twist_range"] = (
            kwargs.pop("helical_twist_min", 0),
            kwargs.pop("helical_twist_max", 0),
            kwargs.pop("helical_twist_inistep", 0),
        )
        kwargs["helical_rise_range"] = (
            kwargs.pop("helical_rise_min", 0),
            kwargs.pop("helical_rise_max", 0),
            kwargs.pop("helical_rise_inistep", 0),
        )
        kwargs["rot_tilt_psi_range"] = (
            kwargs.pop("range_rot", -1),
            kwargs.pop("range_tilt", 15),
            kwargs.pop("range_psi", 10),
        )
        kwargs["helical_tube_diameter_range"] = (
            kwargs.pop("helical_tube_inner_diameter", -1),
            kwargs.pop("helical_tube_outer_diameter", -1),
        )
        kwargs["offset_range_step"] = (
            kwargs.pop("offset_range", 5),
            kwargs.pop("offset_step", 1),
        )
        kwargs.pop("fn_cont", None)
        return super().normalize_kwargs_inv(**kwargs)

    @classmethod
    def setup_widgets(cls, widgets):
        @widgets["do_local_ang_searches"].changed.connect
        def _on_do_local_ang_searches_changed(value: bool):
            widgets["sigma_angles"].enabled = value
            widgets["relax_sym"].enabled = value

        @widgets["do_ctf_correction"].changed.connect
        def _on_do_ctf_correction_changed(value: bool):
            widgets["ctf_intact_first_peak"].enabled = value

        widgets["sigma_angles"].enabled = widgets["do_local_ang_searches"].value
        widgets["relax_sym"].enabled = widgets["do_local_ang_searches"].value
        widgets["ctf_intact_first_peak"].enabled = widgets["do_ctf_correction"].value

        _setup_helix_params(widgets)


class Class3DNoAlignmentJob(_Class3DJobBase):
    @classmethod
    def command_id(cls):
        return super().command_id() + ".noalignment"

    @classmethod
    def param_matches(cls, job_params: dict[str, str]) -> bool:
        return job_params.get("dont_skip_align", "Yes") == "No"

    @classmethod
    def job_title(cls):
        return "3D Class (No Alignment)"

    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        kwargs = super().normalize_kwargs(**kwargs)
        # force no alignment
        kwargs["dont_skip_align"] = False
        kwargs["highres_limit"] = -1
        return kwargs

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs) -> dict[str, Any]:
        kwargs = super().normalize_kwargs_inv(**kwargs)
        kwargs.pop("dont_skip_align", None)
        kwargs.pop("highres_limit", None)
        return kwargs

    def run(
        self,
        fn_img: _a.io.IN_PARTICLES = "",
        fn_ref: _a.io.REF_TYPE = "",
        fn_mask: _a.io.MASK_TYPE = "",
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
        nr_mpi: _a.running.MPI_TYPE = 1,
        nr_threads: _a.running.THREAD_TYPE = 1,
        do_queue: _a.running.DO_QUEUE_TYPE = False,
        min_dedicated: _a.running.MIN_DEDICATED_TYPE = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class Class3DJob(_Class3DJobBase):
    @classmethod
    def command_id(cls):
        return super().command_id() + ".alignment"

    @classmethod
    def param_matches(cls, job_params: dict[str, str]) -> bool:
        return job_params.get("dont_skip_align", "Yes") == "Yes"

    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        kwargs = super().normalize_kwargs(**kwargs)
        # force no alignment
        kwargs["dont_skip_align"] = True
        return kwargs

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs) -> dict[str, Any]:
        kwargs = super().normalize_kwargs_inv(**kwargs)
        kwargs.pop("dont_skip_align", None)
        return kwargs

    def run(
        self,
        fn_img: _a.io.IN_PARTICLES = "",
        fn_ref: _a.io.REF_TYPE = "",
        fn_mask: _a.io.MASK_TYPE = "",
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
        highres_limit: _a.class_.HIGH_RES_LIMIT = -1,
        do_blush: _a.misc.DO_BLUSH = False,
        # Sampling
        sampling: _a.sampling.ANG_SAMPLING = "7.5 degrees",
        offset_range_step: _a.sampling.OFFSET_RANGE_STEP = (5, 1),
        do_local_ang_searches: _a.sampling.LOCAL_ANG_SEARCH = False,
        sigma_angles: _a.sampling.SIGMA_ANGLES = 5,
        relax_sym: _a.sampling.RELAX_SYMMETRY = "",
        allow_coarser: _a.sampling.ALLOW_COARSER_SAMPLING = False,
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
        nr_mpi: _a.running.MPI_TYPE = 1,
        nr_threads: _a.running.THREAD_TYPE = 1,
        do_queue: _a.running.DO_QUEUE_TYPE = False,
        min_dedicated: _a.running.MIN_DEDICATED_TYPE = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class Refine3DJob(_Relion5Job):
    """3D auto-refinement of pre-aligned particles."""

    @classmethod
    def type_label(cls) -> str:
        return "relion.refine3d"

    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        if "helical_twist_range" in kwargs:
            (
                kwargs["helical_twist_min"],
                kwargs["helical_twist_max"],
                kwargs["helical_twist_inistep"],
            ) = kwargs.pop("helical_twist_range")
        if "helical_rise_range" in kwargs:
            (
                kwargs["helical_rise_min"],
                kwargs["helical_rise_max"],
                kwargs["helical_rise_inistep"],
            ) = kwargs.pop("helical_rise_range")
        if "rot_tilt_psi_range" in kwargs:
            kwargs["range_rot"], kwargs["range_tilt"], kwargs["range_psi"] = kwargs.pop(
                "rot_tilt_psi_range"
            )
        if "helical_tube_diameter_range" in kwargs:
            (
                kwargs["helical_tube_inner_diameter"],
                kwargs["helical_tube_outer_diameter"],
            ) = kwargs.pop("helical_tube_diameter_range")
        if "offset_range_step" in kwargs:
            kwargs["offset_range"], kwargs["offset_step"] = kwargs.pop(
                "offset_range_step"
            )
        kwargs["fn_cont"] = ""
        return super().normalize_kwargs(**kwargs)

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs) -> dict[str, Any]:
        kwargs["helical_twist_range"] = (
            kwargs.pop("helical_twist_min", 0),
            kwargs.pop("helical_twist_max", 0),
            kwargs.pop("helical_twist_inistep", 0),
        )
        kwargs["helical_rise_range"] = (
            kwargs.pop("helical_rise_min", 0),
            kwargs.pop("helical_rise_max", 0),
            kwargs.pop("helical_rise_inistep", 0),
        )
        kwargs["rot_tilt_psi_range"] = (
            kwargs.pop("range_rot", -1),
            kwargs.pop("range_tilt", 15),
            kwargs.pop("range_psi", 10),
        )
        kwargs["helical_tube_diameter_range"] = (
            kwargs.pop("helical_tube_inner_diameter", -1),
            kwargs.pop("helical_tube_outer_diameter", -1),
        )
        kwargs["offset_range_step"] = (
            kwargs.pop("offset_range", 5),
            kwargs.pop("offset_step", 1),
        )
        kwargs.pop("fn_cont", None)
        return super().normalize_kwargs_inv(**kwargs)

    def run(
        self,
        fn_img: _a.io.IN_PARTICLES = "",
        fn_ref: _a.io.REF_TYPE = "",
        fn_mask: _a.io.MASK_TYPE = "",
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
        # Helix
        do_helix: _a.helix.DO_HELIX = False,
        helical_tube_diameter_range: _a.helix.HELICAL_TUBE_DIAMETER_RANGE = (-1, -1),
        rot_tilt_psi_range: _a.helix.ROT_TILT_PSI_RANGE = (-1, 15, 10),
        helical_range_distance: _a.helix.HELICAL_RANGE_DIST = -1,
        do_apply_helical_symmetry: _a.helix.DO_APPLY_HELICAL_SYMMETRY = True,
        helical_nr_asu: _a.helix.HELICAL_NR_ASU = 1,
        helical_twist_initial: _a.helix.HELICAL_TWIST_INITIAL = 0,
        helical_rise_initial: _a.helix.HELICAL_RISE_INITIAL = 0,
        helical_z_percentage: _a.helix.HELICAL_Z_PERCENTAGE = 30,
        keep_tilt_prior_fixed: _a.helix.KEEP_TILT_PRIOR_FIXED = True,
        do_local_search_helical_symmetry: _a.helix.DO_LOCAL_SEARCH_H_SYM = False,
        helical_twist_range: _a.helix.HELICAL_TWIST_RANGE = (0, 0, 0),
        helical_rise_range: _a.helix.HELICAL_RISE_RANGE = (0, 0, 0),
        # Compute
        do_parallel_discio: _a.compute.USE_PARALLEL_DISC_IO = True,
        nr_pool: _a.compute.NUM_POOL = 3,
        use_scratch: _a.compute.USE_SCRATCH = False,
        do_pad1: _a.compute.DO_PAD1 = False,
        do_preread_images: _a.compute.DO_PREREAD = False,
        do_combine_thru_disc: _a.compute.DO_COMBINE_THRU_DISC = False,
        gpu_ids: _a.compute.GPU_IDS = "",
        # Running
        nr_mpi: _a.running.MPI_TYPE = 3,
        nr_threads: _a.running.THREAD_TYPE = 1,
        do_queue: _a.running.DO_QUEUE_TYPE = False,
        min_dedicated: _a.running.MIN_DEDICATED_TYPE = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")

    @classmethod
    def setup_widgets(cls, widgets):
        @widgets["do_ctf_correction"].changed.connect
        def _on_do_ctf_correction_changed(value: bool):
            widgets["ctf_intact_first_peak"].enabled = value

        widgets["ctf_intact_first_peak"].enabled = widgets["do_ctf_correction"].value
        _setup_helix_params(widgets)


def _setup_helix_params(widgets: dict[str, ValueWidget]) -> None:
    helical_names = [
        "helical_tube_diameter_range",
        "rot_tilt_psi_range",
        "do_apply_helical_symmetry",
        "do_local_search_helical_symmetry",
        "helical_range_distance",
        "helical_twist_initial",
        "helical_twist_range",
        "helical_rise_initial",
        "helical_rise_range",
        "helical_nr_asu",
        "helical_z_percentage",
        "keep_tilt_prior_fixed",
    ]

    @widgets["do_helix"].changed.connect
    def _on_helical(value: bool):
        for name in helical_names:
            widgets[name].enabled = value
        _on_do_local_search_helical_symmetry(
            widgets["do_local_search_helical_symmetry"].value
        )

    for name in helical_names:
        widgets[name].enabled = False

    @widgets["do_local_search_helical_symmetry"].changed.connect
    def _on_do_local_search_helical_symmetry(value: bool):
        widgets["helical_twist_range"].enabled = value
        widgets["helical_rise_range"].enabled = value

    widgets["helical_twist_range"].enabled = False
    widgets["helical_rise_range"].enabled = False


class _SelectJob(_Relion5Job):
    @classmethod
    def type_label(cls):
        return "relion.select"

    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        kwargs = super().normalize_kwargs(**kwargs)
        for name, default in [
            ("fn_model", ""),  # select class
            ("fn_mic", ""),  # select micrographs
            ("fn_data", ""),  # select particles
            ("do_class_ranker", False),
            ("do_discard", False),
            ("do_filaments", False),
            ("do_queue", False),
            ("do_random", False),
            ("do_recenter", False),
            ("do_regroup", False),
            ("do_select_values", False),
            ("do_split", False),
            ("do_remove_duplicates", False),
            ("select_label", "rlnCtfMaxResolution"),
            ("select_minval", -9999.0),
            ("select_maxval", 9999.0),
            ("duplicate_threshold", 30.0),
            ("image_angpix", -1.0),
            ("rank_threshold", 0.5),
            ("select_nr_classes", -1),
            ("select_nr_parts", -1),
            ("nr_groups", 1),
            ("split_size", 100),
            ("nr_split", -1),
            ("dendrogram_threshold", 0.85),
            ("dendrogram_minclass", -1000),
            ("min_dedicated", 1),
        ]:
            kwargs.setdefault(name, default)
        return super().normalize_kwargs(**kwargs)

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs):
        kwargs = super().normalize_kwargs_inv(**kwargs)
        params = cls._signature().parameters
        for name in list(kwargs.keys()):
            if name not in params:
                kwargs.pop(name)
        return kwargs


class SelectClassesInteractiveJob(_SelectJob):
    @classmethod
    def type_label(cls):
        return "relion.select.interactive"

    def run(self, fn_model: _a.io.IN_OPTIMISER = ""):
        raise NotImplementedError("This is a builtin job placeholder.")

    @classmethod
    def _search_parent_class3d(cls, path: Path) -> JobDirectory | None:
        job = JobDirectory(path)
        for p in job.parent_jobs():
            if p.job_type_label() == "relion.class3d":
                return p
        else:
            return None

    @classmethod
    def _search_opt(cls, path: Path) -> str | None:
        """Only used for inspect particles of tomo extension."""
        if job_class3d := cls._search_parent_class3d(path):
            params = job_class3d.get_job_params_as_dict()
            if opt_path := params.get("in_opimisation", None):
                return opt_path
        return None

    @classmethod
    def _search_mics(cls, path: Path) -> str | None:
        """Only used for inspect particles of tomo extension."""
        if job_class3d := cls._search_parent_class3d(path):
            params = job_class3d.get_job_params_as_dict()
            if opt_path := params.get("in_opimisation", None):
                opt_path = job_class3d.relion_project_dir / opt_path
                opt = OptimisationSetModel.validate_file(opt_path)
                return opt.tomogram_star
            elif in_tomo := params.get("in_tomograms", None):
                return in_tomo
        return None


class SelectClassesAutoJob(_SelectJob):
    @classmethod
    def type_label(cls):
        return "relion.select.class2dauto"

    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        kwargs = super().normalize_kwargs(**kwargs)
        kwargs["do_class_ranker"] = True
        return super().normalize_kwargs(**kwargs)

    def run(
        self,
        fn_model: _a.io.IN_OPTIMISER = "",
        rank_threshold: _a.select.RANK_THRESHOLD = 0.5,
        select_nr_parts: _a.select.SELECT_NR_PARTS = -1,
        select_nr_classes: _a.select.SELECT_NR_CLASSES = -1,
        do_recenter: _a.select.DO_RECENTER = False,
        do_regroup: _a.select.DO_REGROUP = False,
        nr_groups: _a.select.NR_GROUPS = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class _SelectValuesJob(_SelectJob):
    @classmethod
    def type_label(cls):
        return "relion.select.onvalue"


class SelectParticlesJob(_SelectValuesJob):
    @classmethod
    def param_matches(cls, job_params):
        return job_params["fn_data"] != ""

    @classmethod
    def command_id(cls):
        return super().command_id() + "-particles"

    @classmethod
    def job_title(cls):
        return "Select Particles by Value"

    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        kwargs = super().normalize_kwargs(**kwargs)
        kwargs["do_select_values"] = True
        return super().normalize_kwargs(**kwargs)

    def run(
        self,
        fn_data: _a.io.IN_PARTICLES = "",
        select_label: _a.select.SELECT_LABEL = "rlnCtfMaxResolution",
        select_minval: _a.select.SELECT_MINVAL = -9999,
        select_maxval: _a.select.SELECT_MAXVAL = 9999,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class SelectMicrographsJob(_SelectValuesJob):
    @classmethod
    def param_matches(cls, job_params):
        return job_params["fn_data"] == "" and job_params["fn_mic"]

    @classmethod
    def command_id(cls):
        return super().command_id() + "-micrographs"

    @classmethod
    def job_title(cls):
        return "Select Micrographs by Value"

    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        kwargs = super().normalize_kwargs(**kwargs)
        kwargs["do_discard"] = True
        return super().normalize_kwargs(**kwargs)

    def run(
        self,
        fn_mic: _a.io.IN_MICROGRAPHS = "",
        select_label: _a.select.SELECT_LABEL = "rlnCtfMaxResolution",
        select_minval: _a.select.SELECT_MINVAL = -9999,
        select_maxval: _a.select.SELECT_MAXVAL = 9999,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class SelectRemoveDuplicatesJob(_SelectJob):
    """Remove duplicate particles based on their coordinates."""

    @classmethod
    def type_label(cls):
        return "relion.select.removeduplicates"

    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        kwargs = super().normalize_kwargs(**kwargs)
        kwargs["do_remove_duplicates"] = True
        return super().normalize_kwargs(**kwargs)

    def run(
        self,
        fn_data: _a.io.IN_PARTICLES = "",
        duplicate_threshold: _a.select.DUPLICATE_THRESHOLD = 30,
        image_angpix: _a.select.IMAGE_ANGPIX = -1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class SelectSplitJob(_SelectJob):
    """Split particles into subsets."""

    @classmethod
    def type_label(cls):
        return "relion.select.split"

    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        kwargs = super().normalize_kwargs(**kwargs)
        kwargs["do_split"] = True
        return super().normalize_kwargs(**kwargs)

    def run(
        self,
        fn_data: _a.io.IN_PARTICLES = "",
        do_random: _a.select.DO_RANDOM = False,
        split_size: _a.select.SPLIT_SIZE = 100,
        nr_split: _a.select.NR_SPLIT = -1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class SelectFilamentsJob(_SelectJob):
    @classmethod
    def type_label(cls):
        return "relion.select.filamentsdendrogram"

    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        kwargs = super().normalize_kwargs(**kwargs)
        kwargs["do_filaments"] = True
        return super().normalize_kwargs(**kwargs)

    def run(
        self,
        fn_model: _a.io.IN_OPTIMISER = "",
        dendrogram_threshold: _a.select.DENDROGRAM_THRESHOLD = 0.85,
        dendrogram_minclass: _a.select.DENDROGRAM_MINCLASS = -1000,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class MaskCreationJob(_Relion5Job):
    """Create a 3D mask from a reconstructed map."""

    @classmethod
    def type_label(cls) -> str:
        return "relion.maskcreate"

    def run(
        self,
        fn_in: _a.io.MAP_TYPE = "",
        lowpass_filter: Annotated[
            float, {"label": "Lowpass filter (A)", "group": "Mask"}
        ] = 15,
        angpix: Annotated[float, {"label": "Pixel size (A)", "group": "Mask"}] = -1,
        inimask_threshold: Annotated[
            float, {"label": "Initial binarisation threshold", "group": "Mask"}
        ] = 0.02,
        extend_inimask: Annotated[
            int, {"label": "Extend binary map (pixels)", "group": "Mask"}
        ] = 3,
        width_mask_edge: Annotated[
            int, {"label": "Soft edge (pixels)", "group": "Mask"}
        ] = 3,
        do_helix: _a.helix.DO_HELIX = False,
        helical_z_percentage: _a.helix.HELICAL_Z_PERCENTAGE = 30,
        # Running
        nr_threads: _a.running.THREAD_TYPE = 1,
        do_queue: _a.running.DO_QUEUE_TYPE = False,
        min_dedicated: _a.running.MIN_DEDICATED_TYPE = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class PostProcessJob(_Relion5Job):
    @classmethod
    def type_label(cls) -> str:
        return "relion.postprocess"

    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        kwargs = super().normalize_kwargs(**kwargs)
        b_factor = kwargs.pop("b_factor", {})
        assert isinstance(b_factor, dict), f"b_factor must be a dict, got {b_factor!r}"
        kwargs["do_auto_bfac"] = b_factor.get("do_auto_bfac", True)
        kwargs["autob_lowres"] = b_factor.get("autob_lowres", 10)
        kwargs["do_adhoc_bfac"] = b_factor.get("do_adhoc_bfac", False)
        kwargs["adhoc_bfac"] = b_factor.get("adhoc_bfac", -1000)
        return kwargs

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs) -> dict[str, Any]:
        kwargs = super().normalize_kwargs_inv(**kwargs)
        do_auto_bfac = kwargs.pop("do_auto_bfac", True)
        autob_lowres = kwargs.pop("autob_lowres", 10)
        do_adhoc_bfac = kwargs.pop("do_adhoc_bfac", False)
        adhoc_bfac = kwargs.pop("adhoc_bfac", -1000)
        kwargs["b_factor"] = {
            "do_auto_bfac": parse_string(do_auto_bfac, bool),
            "autob_lowres": parse_string(autob_lowres, float),
            "do_adhoc_bfac": parse_string(do_adhoc_bfac, bool),
            "adhoc_bfac": parse_string(adhoc_bfac, float),
        }
        return kwargs

    def run(
        self,
        # I/O
        fn_in: _a.io.HALFMAP_TYPE = "",
        fn_mask: _a.io.MASK_TYPE = "",
        angpix: Annotated[
            float, {"label": "Calibrated pixel size (A)", "group": "I/O"}
        ] = -1,
        # Sharpen
        b_factor: _a.misc.B_FACTOR = None,
        do_skip_fsc_weighting: Annotated[
            bool, {"label": "Skip FSC-weighting", "group": "Sharpen"}
        ] = False,
        low_pass: Annotated[
            float, {"label": "Low-pass filter (A)", "group": "Sharpen"}
        ] = 5,
        fn_mtf: Annotated[
            str, {"label": "MTF of the detector", "group": "Sharpen"}
        ] = "",
        mtf_angpix: Annotated[
            float, {"label": "MTF pixel size (A)", "group": "Sharpen"}
        ] = 1,
        # Running
        do_queue: _a.running.DO_QUEUE_TYPE = False,
        min_dedicated: _a.running.MIN_DEDICATED_TYPE = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


FIT_CTF_CHOICES = Literal["No", "Per-micrograph", "Per-particle"]


class CtfRefineJob(_Relion5Job):
    _do_ctf_args = ("do_defocus", "do_astig", "do_bfactor", "do_phase")

    @classmethod
    def type_label(cls) -> str:
        return "relion.ctfrefine"

    @classmethod
    def normalize_kwargs(cls, **kwargs):
        kwargs = super().normalize_kwargs(**kwargs)
        kwargs["do_ctf"] = any(kwargs[name] != "No" for name in cls._do_ctf_args)

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs):
        kwargs = super().normalize_kwargs_inv(**kwargs)
        do_ctf = kwargs.pop("do_ctf", False)
        if not do_ctf:
            for name in cls._do_ctf_args:
                kwargs[name] = "No"
        return kwargs

    def run(
        self,
        fn_data: _a.io.IN_PARTICLES = "",
        fn_post: _a.io.PROCESS_TYPE = "",
        # Fit
        do_aniso_mag: Annotated[
            bool, {"label": "Estimate anisotropic magnification", "group": "Fit"}
        ] = False,
        do_defocus: Annotated[
            FIT_CTF_CHOICES, {"label": "Fit defocus", "group": "Fit"}
        ] = "No",
        do_astig: Annotated[
            FIT_CTF_CHOICES, {"label": "Fit astigmatism", "group": "Fit"}
        ] = "No",
        do_bfactor: Annotated[
            FIT_CTF_CHOICES, {"label": "Fit B-factor", "group": "Fit"}
        ] = "No",
        do_phase: Annotated[
            FIT_CTF_CHOICES, {"label": "Fit phase shift", "group": "Fit"}
        ] = "No",
        do_tilt: Annotated[
            bool, {"label": "Estimate beam tilt", "group": "Fit"}
        ] = False,
        do_trefoil: Annotated[
            bool, {"label": "Estimate trefoil", "group": "Fit"}
        ] = False,
        do_4thorder: Annotated[
            bool, {"label": "Estimate 4th order aberrations", "group": "Fit"}
        ] = False,
        minres: Annotated[
            float, {"label": "Minimum resolution for fitting (A)", "group": "Fit"}
        ] = 30,
        # Running
        nr_mpi: _a.running.MPI_TYPE = 1,
        nr_threads: _a.running.THREAD_TYPE = 1,
        do_queue: _a.running.DO_QUEUE_TYPE = False,
        min_dedicated: _a.running.MIN_DEDICATED_TYPE = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")

    @classmethod
    def setup_widgets(cls, widgets):
        @widgets["do_aniso_mag"].changed.connect
        def _on_do_aniso_mag_changed(value: bool):
            for name in cls._do_ctf_args:
                widgets[name].enabled = not value

        _on_do_aniso_mag_changed(widgets["do_aniso_mag"].value)


# "relion.joinstar.particles": "Join Particles",
# "relion.joinstar.micrographs": "Join Micrographs",
# "relion.joinstar.movies": "Join Movies",
class _JoinStarBase(_Relion5Job):
    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        kwargs = super().normalize_kwargs(**kwargs)
        for do in ["do_mic", "do_mov", "do_part"]:
            kwargs.setdefault(do, False)
        for i in [1, 2, 3, 4]:
            kwargs.setdefault(f"fn_mic{i}", "")
            kwargs.setdefault(f"fn_mov{i}", "")
            kwargs.setdefault(f"fn_part{i}", "")
        return kwargs

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs) -> dict[str, Any]:
        kwargs = super().normalize_kwargs_inv(**kwargs)
        params = cls._signature().parameters
        for do in ["do_mic", "do_mov", "do_part"]:
            if do not in params:
                kwargs.pop(do, None)
        for i in [1, 2, 3, 4]:
            for prefix in ["fn_mic", "fn_mov", "fn_part"]:
                if f"{prefix}{i}" not in params:
                    kwargs.pop(f"{prefix}{i}", None)
        return kwargs


class JoinParticlesJob(_JoinStarBase):
    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        kwargs = super().normalize_kwargs(**kwargs)
        kwargs["do_part"] = True
        return kwargs

    @classmethod
    def type_label(cls):
        return "relion.joinstar.particles"

    def run(
        self,
        fn_part1: _a.io.IN_PARTICLES = "",
        fn_part2: _a.io.IN_PARTICLES = "",
        fn_part3: _a.io.IN_PARTICLES = "",
        fn_part4: _a.io.IN_PARTICLES = "",
        do_queue: _a.running.DO_QUEUE_TYPE = False,
        min_dedicated: _a.running.MIN_DEDICATED_TYPE = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class JoinMicrographsJob(_JoinStarBase):
    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        kwargs = super().normalize_kwargs(**kwargs)
        kwargs["do_mic"] = True
        return kwargs

    @classmethod
    def type_label(cls):
        return "relion.joinstar.micrographs"

    def run(
        self,
        fn_mic1: _a.io.IN_MICROGRAPHS = "",
        fn_mic2: _a.io.IN_MICROGRAPHS = "",
        fn_mic3: _a.io.IN_MICROGRAPHS = "",
        fn_mic4: _a.io.IN_MICROGRAPHS = "",
        do_queue: _a.running.DO_QUEUE_TYPE = False,
        min_dedicated: _a.running.MIN_DEDICATED_TYPE = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class JoinMoviesJob(_JoinStarBase):
    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        kwargs = super().normalize_kwargs(**kwargs)
        kwargs["do_mov"] = True
        return kwargs

    @classmethod
    def type_label(cls):
        return "relion.joinstar.movies"

    def run(
        self,
        fn_mov1: _a.io.IN_MOVIES = "",
        fn_mov2: _a.io.IN_MOVIES = "",
        fn_mov3: _a.io.IN_MOVIES = "",
        fn_mov4: _a.io.IN_MOVIES = "",
        do_queue: _a.running.DO_QUEUE_TYPE = False,
        min_dedicated: _a.running.MIN_DEDICATED_TYPE = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")

    # "relion.localres.own": "Local Resolution",
    # "relion.localres.resmap": "Local Resolution",


class _LocalResolutionJobBase(_Relion5Job): ...


class LocalResolutionResmapJob(_LocalResolutionJobBase):
    @classmethod
    def type_label(cls):
        return "relion.localres.resmap"

    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        kwargs = super().normalize_kwargs(**kwargs)
        kwargs["do_resmap_locres"] = True
        kwargs["do_relion_locres"] = False
        return super().normalize_kwargs(**kwargs)

    def run(
        self,
        fn_in: _a.io.HALFMAP_TYPE = "",
        fn_mask: _a.io.MASK_TYPE = "",
        angpix: Annotated[float, {"label": "Pixel size (A)", "group": "I/O"}] = -1,
        pval: Annotated[
            float, {"label": "P-value for significance", "group": "ResMap"}
        ] = 0.05,
        minres: Annotated[
            float, {"label": "Highest resolution (A)", "group": "ResMap"}
        ] = 0,
        maxres: Annotated[
            float, {"label": "Lowest resolution (A)", "group": "ResMap"}
        ] = 0,
        stepres: Annotated[
            float, {"label": "Resolution step (A)", "group": "ResMap"}
        ] = 1,
        # Running
        nr_mpi: _a.running.MPI_TYPE = 1,
        do_queue: _a.running.DO_QUEUE_TYPE = False,
        min_dedicated: _a.running.MIN_DEDICATED_TYPE = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class LocalResolutionOwnJob(_LocalResolutionJobBase):
    @classmethod
    def type_label(cls):
        return "relion.localres.own"

    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        kwargs = super().normalize_kwargs(**kwargs)
        kwargs["do_resmap_locres"] = False
        kwargs["do_relion_locres"] = True
        return super().normalize_kwargs(**kwargs)

    def run(
        self,
        fn_in: _a.io.HALFMAP_TYPE = "",
        fn_mask: _a.io.MASK_TYPE = "",
        angpix: Annotated[float, {"label": "Pixel size (A)", "group": "I/O"}] = -1,
        adhoc_bfactor: Annotated[
            float, {"label": "User-provided B-factor (A^2)", "group": "Relion"}
        ] = -100,
        fn_mtf: Annotated[
            str, {"label": "MTF of the detector", "group": "Relion"}
        ] = "",
        # Running
        nr_mpi: _a.running.MPI_TYPE = 1,
        do_queue: _a.running.DO_QUEUE_TYPE = False,
        min_dedicated: _a.running.MIN_DEDICATED_TYPE = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")
