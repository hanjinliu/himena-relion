from __future__ import annotations

from magicgui.widgets import RadioButtons
from magicgui.widgets.bases import ValuedContainerWidget
from magicgui.types import Undefined
from himena.qt.magicgui import ToggleSwitch, FloatEdit, IntEdit

from himena_relion._job_class import parse_string
from himena_relion._widgets._path_input import PathDrop


class DoseRateEdit(ValuedContainerWidget):
    def __init__(self, **kwargs):
        self._kind = RadioButtons(
            choices=["Per tilt", "Per movie frame"],
            value="Per tilt",
            orientation="horizontal",
        )
        self._dose_rate = FloatEdit(label="", value=5.0)
        widgets = [self._kind, self._dose_rate]
        super().__init__(layout="vertical", labels=False, widgets=widgets, **kwargs)
        self.margins = (0, 0, 0, 0)

    def get_value(self):
        return {
            "dose_rate": self._dose_rate.value,
            "dose_is_per_movie_frame": self._kind.value == "Per movie frame",
        }

    def set_value(self, value):
        with self.changed.blocked():
            if value == Undefined or value is None:
                self._kind.value = "Per tilt"
                self._dose_rate.value = 5.0
            elif isinstance(value, dict):
                dose_is_per_movie_frame = value.get("dose_is_per_movie_frame", False)
                self._kind.value = (
                    "Per movie frame"
                    if parse_string(dose_is_per_movie_frame, bool)
                    else "Per tilt"
                )
                self._dose_rate.value = float(value.get("dose_rate", 5.0))
            else:
                raise ValueError("Value must be a dict or Undefined.")
        self.changed.emit(self.get_value())


class OptimisationSetEdit(ValuedContainerWidget):
    """Widget for selecting a optimisation set or direct entries."""

    def __init__(self, **kwargs):
        self._toggle_switch = ToggleSwitch(text="Use direct entries", value=False)
        self._in_opt = PathDrop(
            "",
            type_label="TomoOptimisationSet",
            allowed_extensions=[".star"],
            tooltip="Path to the optimisation_set.star file.",
        )
        self._in_particles = PathDrop(
            "",
            type_label=["ParticlesData", "ParticleGroupMetadata"],
            tooltip=(
                "Path to the particle star file (usually named particles.star or "
                "*_data.star)"
            ),
        )
        self._in_tomograms = PathDrop(
            "",
            type_label=["TomogramGroupMetadata"],
            allowed_extensions=[".star"],
            tooltip="Path to the tomogram.star file.",
        )
        self._in_trajectories = PathDrop(
            "",
            type_label="TomoTrajectoryData",
            allowed_extensions=[".star"],
            tooltip="Path to the trajectory star file.",
        )
        widgets = [
            self._toggle_switch,
            self._in_opt,
            self._in_particles,
            self._in_tomograms,
            self._in_trajectories,
        ]
        super().__init__(layout="vertical", labels=False, widgets=widgets, **kwargs)
        self.margins = (0, 0, 0, 0)
        self._toggle_switch.changed.connect(self._on_toggle_switch_changed)
        self._on_toggle_switch_changed(False)

    def _on_toggle_switch_changed(self, use_direct: bool):
        self._in_opt.visible = not use_direct
        self._in_particles.visible = use_direct
        self._in_tomograms.visible = use_direct
        self._in_trajectories.visible = use_direct

    def get_value(self):
        in_optimisation = self._in_opt.value
        in_particles = self._in_particles.value
        in_tomograms = self._in_tomograms.value
        in_trajectories = self._in_trajectories.value
        use_direct_entries = self._toggle_switch.value
        if use_direct_entries:
            in_optimisation = ""
        else:
            in_particles = ""
            in_tomograms = ""
            in_trajectories = ""
        return {
            "in_optimisation": in_optimisation,
            "use_direct_entries": use_direct_entries,
            "in_particles": in_particles,
            "in_tomograms": in_tomograms,
            "in_trajectories": in_trajectories,
        }

    def set_value(self, value):
        with self.changed.blocked():
            if value == Undefined or value is None:
                self._toggle_switch.value = False
                self._in_opt.value = ""
                self._in_particles.value = ""
                self._in_tomograms.value = ""
                self._in_trajectories.value = ""
            elif isinstance(value, dict):
                self._in_opt.value = value.get("in_optimisation", "")
                self._in_particles.value = value.get("in_particles", "")
                self._in_tomograms.value = value.get("in_tomograms", "")
                self._in_trajectories.value = value.get("in_trajectories", "")
                use_direct = (
                    "in_particles" in value
                    or "in_tomograms" in value
                    or "in_trajectories" in value
                )
                val = value.get("use_direct_entries", use_direct)
                self._toggle_switch.value = parse_string(val, bool)
            else:
                raise ValueError("Value must be a dict or Undefined.")
        self.changed.emit(self.get_value())


class BfactorEdit(ValuedContainerWidget):
    """Widget for entering B-factor related parameters."""

    def __init__(self, **kwargs):
        self._toggle_switch = ToggleSwitch(
            text="Use user-provided B-factor",
            value=False,
            tooltip=(
                "If set to No, then the program will use the automated procedure "
                "described by Rosenthal and Henderson (2003, JMB) to estimate an "
                "overall B-factor for your map, and sharpen it accordingly. Note that "
                "your map must extend well beyond the lowest resolution included in "
                "the procedure below, which should not be set to resolutions much "
                "lower than 10 Angstroms. \n\n"
                "Otherwise, instead of using the automated B-factor estimation, "
                "provide your own value. Use negative values for sharpening the map. "
                "This option is useful if your map does not extend beyond the 10A "
                "needed for the automated procedure, or when the automated procedure "
                "does not give a suitable value (e.g. in more disordered parts of the "
                "map)."
            ),
        )
        self._auto_lowres = FloatEdit(
            label="Lowest resolution (A)",
            value=10.0,
            min=8,
            max=15,
            tooltip=(
                "This is the lowest frequency (in Angstroms) that will be included in "
                "the linear fit of the Guinier plot as described in Rosenthal and "
                "Henderson (2003, JMB). Dont use values much lower or higher than 10 "
                "Angstroms. If your map does not extend beyond 10 Angstroms, then "
                "instead of the automated procedure use your own B-factor."
            ),
        )
        self._user_bfactor = FloatEdit(
            label="B-factor (A^2)",
            value=-1000.0,
            min=-2000,
            max=0,
            tooltip=(
                "Use negative values for sharpening. Be careful: if you over-sharpen "
                "your map, you may end up interpreting noise for signal!"
            ),
        )

        widgets = [self._toggle_switch, self._auto_lowres, self._user_bfactor]
        super().__init__(layout="vertical", labels=True, widgets=widgets, **kwargs)
        self.margins = (0, 0, 0, 0)
        self._toggle_switch.changed.connect(self._on_toggle_switch_changed)
        self._on_toggle_switch_changed(False)

    def _on_toggle_switch_changed(self, user: bool):
        self._auto_lowres.visible = not user
        self._user_bfactor.visible = user

    def get_value(self):
        return {
            "do_auto_bfac": not self._toggle_switch.value,
            "autob_lowres": self._auto_lowres.value,
            "do_adhoc_bfac": self._toggle_switch.value,
            "adhoc_bfac": self._user_bfactor.value,
        }

    def set_value(self, value):
        with self.changed.blocked():
            if value == Undefined or value is None:
                self._toggle_switch.value = False
                self._auto_lowres.value = 10.0
                self._user_bfactor.value = -1000.0
            elif isinstance(value, dict):
                do_auto = value.get("do_auto_bfac", True)
                self._toggle_switch.value = not parse_string(do_auto, bool)
                self._auto_lowres.value = value.get("autob_lowres", 10.0)
                self._user_bfactor.value = value.get("adhoc_bfac", -1000.0)
            else:
                raise ValueError("Value must be a dict or Undefined.")
        self.changed.emit(self.get_value())


class Class2DAlgorithmEdit(ValuedContainerWidget):
    """Widget for selecting 2D classification algorithm."""

    def __init__(self, **kwargs):
        self._algorithm = RadioButtons(
            label="Algorithm",
            choices=["EM", "VDAM"],
            value="VDAM",
            orientation="horizontal",
            tooltip="The optimization algorithm to use.",
        )
        self._niter_em = IntEdit(
            label="EM Iterations",
            value=25,
            min=1,
            max=100,
            tooltip="Number of EM iterations to be performed",
        )
        self._niter_grad = IntEdit(
            label="VDAM mini-batches",
            value=200,
            min=1,
            max=1000,
            tooltip="Number of mini-batches to be processed using the VDAM algorithm.",
        )
        widgets = [self._algorithm, self._niter_em, self._niter_grad]
        super().__init__(layout="vertical", labels=True, widgets=widgets, **kwargs)
        self.margins = (0, 0, 0, 0)
        self._algorithm.changed.connect(self._on_algorithm_changed)

    def get_value(self):
        return {
            "algorithm": self._algorithm.value,
            "niter": (
                self._niter_em.value
                if self._algorithm.value == "EM"
                else self._niter_grad.value
            ),
        }

    def set_value(self, value):
        with self.changed.blocked():
            if value == Undefined or value is None:
                self._algorithm.value = "VDAM"
                self._niter_em.value = 25
                self._niter_grad.value = 200
            elif isinstance(value, dict):
                if set(value.keys()) != {"algorithm", "niter"}:
                    raise ValueError(f"Wrong keys in value dict: {value!r}")
                algorithm = value.get("algorithm", "VDAM")
                self._algorithm.value = algorithm
                niter = value.get("niter", 200 if algorithm == "VDAM" else 25)
                if algorithm == "EM":
                    self._niter_em.value = niter
                else:
                    self._niter_grad.value = niter
            else:
                raise ValueError("Value must be a dict or Undefined.")
        self.changed.emit(self.get_value())

    def _on_algorithm_changed(self, algorithm: str):
        self._niter_em.visible = algorithm == "EM"
        self._niter_grad.visible = algorithm == "VDAM"
