from __future__ import annotations
from contextlib import contextmanager

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
        self.setMinimumSize(300, 200)
        self.clear()

    def clear(self):
        """Clear the plot."""
        with self._plot_style():
            fig = hplt.figure()
            self.update_model(WidgetDataModel(value=fig, type=StandardType.PLOT))

    def plot_defocus(self, df: pd.DataFrame):
        with self._plot_style():
            fig = hplt.figure()

            tilt_angle = df["rlnTomoNominalStageTiltAngle"]
            defocus_u_um = df["rlnDefocusU"] / 10000
            defocus_v_um = df["rlnDefocusV"] / 10000
            fig.plot(tilt_angle, defocus_u_um, name="U", width=1)
            fig.plot(tilt_angle, defocus_v_um, name="V", width=1)
            fig.x.label = "Nominal stage tilt angle (°)"
            fig.y.label = "Def. (µm)"
            fig.set_legend(font_size=9.0, location="top_right")
            self.update_model(WidgetDataModel(value=fig, type=StandardType.PLOT))
            self.tight_layout()

    def plot_ctf_scale(self, df: pd.DataFrame):
        return self._plot_single(df, "rlnCtfScalefactor", "Scale")

    def plot_ctf_astigmatism(self, df: pd.DataFrame):
        return self._plot_single(df, "rlnCtfAstigmatism", "Ast. (A)")

    def plot_ctf_defocus_angle(self, df: pd.DataFrame):
        return self._plot_single(df, "rlnDefocusAngle", "Angle (°)")

    def plot_ctf_max_resolution(self, df: pd.DataFrame):
        return self._plot_single(df, "rlnCtfMaxResolution", "Res. (Å)")

    def _plot_single(self, df: pd.DataFrame, ycol: str, ylabel: str):
        with self._plot_style():
            fig = hplt.figure()

            tilt_angle = df["rlnTomoNominalStageTiltAngle"]
            yvals = df[ycol]
            fig.plot(tilt_angle, yvals, width=1)
            fig.x.label = "Nominal stage tilt angle (°)"
            fig.y.label = ylabel
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
            self._fsc_finalize(fig)

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
            fig.set_legend(font_size=9.0)
            self._fsc_finalize(fig)

    def tight_layout(self):
        """Tighten the layout of the plot."""
        self.figure.tight_layout(pad=1.05)
        self._canvas.draw()

    @contextmanager
    def _plot_style(self):
        yield  # implement in the future

    def _fsc_finalize(self, fig: hplt.SingleAxes):
        fig.x.label = "Resolution (Å)"
        fig.y.label = "FSC"
        fig.y.lim = (-0.04, 1.04)
        self.update_model(WidgetDataModel(value=fig, type=StandardType.PLOT))
        self.tight_layout()


def _res_to_str(res: float):
    if res >= 998.9:
        # RELION uses 999 to indicate infinity
        return "Inf"
    return f"{res:.1f}"
