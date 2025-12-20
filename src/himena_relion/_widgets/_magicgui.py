from __future__ import annotations

from magicgui.widgets.bases import ValuedContainerWidget
from magicgui.types import Undefined
from himena.qt.magicgui import ToggleSwitch, FloatEdit
from ._path_input import PathDrop


class OptimisationSetEdit(ValuedContainerWidget):
    """Widget for selecting a optimisation set or direct entries."""

    def __init__(self, **kwargs):
        self._toggle_switch = ToggleSwitch(text="Use direct entries", value=False)
        self._in_opt = PathDrop("", "TomoOptimisationSet")
        self._in_particles = PathDrop("", "ParticleGroupMetadata")
        self._in_tomograms = PathDrop("", "TomogramGroupMetadata")
        self._in_trajectories = PathDrop("", "TomoTrajectoryData")
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
        return {
            "in_optimisation": self._in_opt.value,
            "use_direct_entries": self._toggle_switch.value,
            "in_particles": self._in_particles.value,
            "in_tomograms": self._in_tomograms.value,
            "in_trajectories": self._in_trajectories.value,
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
                self._toggle_switch.value = value.get("use_direct_entries", use_direct)
            else:
                raise ValueError("Value must be a dict or Undefined.")
        self.changed.emit(self.get_value())


class BfactorEdit(ValuedContainerWidget):
    """Widget for entering B-factor related parameters."""

    def __init__(self, **kwargs):
        self._toggle_switch = ToggleSwitch(
            text="Use user-provided B-factor", value=False
        )
        self._auto_lowres = FloatEdit(
            label="Lowest resolution for auto-B fit (A)", value=10.0, min=8, max=15
        )
        self._user_bfactor = FloatEdit(
            label="B-factor (A^2)", value=-1000.0, min=-2000, max=0
        )

        widgets = [self._toggle_switch, self._auto_lowres, self._user_bfactor]
        super().__init__(layout="vertical", labels=False, widgets=widgets, **kwargs)
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
                self._toggle_switch.value = not do_auto
                self._auto_lowres.value = value.get("autob_lowres", 10.0)
                self._user_bfactor.value = value.get("adhoc_bfac", -1000.0)
            else:
                raise ValueError("Value must be a dict or Undefined.")
        self.changed.emit(self.get_value())
