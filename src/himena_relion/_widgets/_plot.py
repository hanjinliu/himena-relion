from __future__ import annotations
from contextlib import contextmanager

import matplotlib.pyplot as plt
from himena import StandardType, WidgetDataModel
from himena.standards import plotting as hplt
from himena_builtins.qt.plot._canvas import QModelMatplotlibCanvas
import pandas as pd


class QPlotCanvas(QModelMatplotlibCanvas):
    """A matplotlib canvas widget for plotting."""

    def __init__(self, parent):
        super().__init__()
        self.setParent(parent)
        self.setMaximumSize(400, 280)

    def plot_defocus(self, df: pd.DataFrame):
        with self._plot_style():
            fig = hplt.figure()

            tilt_angle = df["rlnTomoNominalStageTiltAngle"]
            defocus_u_um = df["rlnDefocusU"] / 10000
            defocus_v_um = df["rlnDefocusV"] / 10000
            fig.plot(tilt_angle, defocus_u_um, name="U")
            fig.plot(tilt_angle, defocus_v_um, name="V")
            fig.x.label = "Nominal stage tilt angle (°)"
            fig.y.label = "Defocus (µm)"
            fig.set_legend(font_size=9.0)
            self.update_model(WidgetDataModel(value=fig, type=StandardType.PLOT))
            self.tight_layout()

    def plot_fsc_refine(self, df: pd.DataFrame):
        x = df["rlnResolution"]
        xticklabels = df["rlnAngstromResolution"]
        fsc = df["rlnGoldStandardFsc"]
        with self._plot_style():
            fig = hplt.figure()
            fig.plot(x, fsc, name="FSC")
            fig.x.set_ticks(
                x[:: len(x) // 5],
                labels=[_res_to_str(r) for r in xticklabels[:: len(x) // 5]],
            )
            fig.x.label = "Resolution (Å)"
            fig.y.label = "FSC"
            self.update_model(WidgetDataModel(value=fig, type=StandardType.PLOT))
            self.tight_layout()

    def plot_fsc_postprocess(self, df: pd.DataFrame):
        x = df["rlnResolution"]
        xticklabels = df["rlnAngstromResolution"]
        fsc_corrected = df["rlnFourierShellCorrelationCorrected"]
        # df["rlnFourierShellCorrelationParticleMaskFraction"]
        fsc_unmask = df["rlnFourierShellCorrelationUnmaskedMaps"]
        fsc_mask = df["rlnFourierShellCorrelationMaskedMaps"]
        # df["rlnCorrectedFourierShellCorrelationPhaseRandomizedMaskedMaps"]
        with self._plot_style():
            fig = hplt.figure()
            fig.plot(x, fsc_unmask, name="Unmasked")
            fig.plot(x, fsc_mask, name="Masked")
            fig.plot(x, fsc_corrected, name="Corrected")
            fig.x.set_ticks(
                x[:: len(x) // 5],
                labels=[_res_to_str(r) for r in xticklabels[:: len(x) // 5]],
            )
            fig.x.label = "Resolution (Å)"
            fig.y.label = "FSC"
            fig.set_legend(font_size=9.0)
            self.update_model(WidgetDataModel(value=fig, type=StandardType.PLOT))
            self.tight_layout()

    def tight_layout(self):
        """Tighten the layout of the plot."""
        self.figure.tight_layout(pad=1.05)
        self._canvas.draw()

    @contextmanager
    def _plot_style(self):
        if widget := self.parentWidget():
            background_color = widget.palette().color(widget.backgroundRole())
        else:
            background_color = self.palette().color(self.backgroundRole())
        if background_color.lightness() < 128:
            style = "dark_background"
        else:
            style = "default"
        with plt.style.context(style):
            yield
            self.figure.set_facecolor(background_color.getRgbF())

            for ax in self.figure.axes:
                ax.set_facecolor(background_color.getRgbF())
                tick_color = ax.xaxis.label.get_color()
                for spine in ax.spines.values():
                    spine.set_color(tick_color)


def _res_to_str(res: float):
    if res >= 998.9:
        # RELION uses 999 to indicate infinity
        return "Inf"
    return f"{res:.1f}"
