from __future__ import annotations

from magicgui.widgets.bases import ValuedContainerWidget
from magicgui.types import Undefined
from himena.qt.magicgui import ToggleSwitch
from ._path_input import PathDrop


class OptimisationSetEdit(ValuedContainerWidget):
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
            self._toggle_switch.value = value.get("use_direct_entries", False)
        else:
            raise ValueError("Value must be a dict or Undefined.")
