from __future__ import annotations

from himena import StandardType, WidgetDataModel
from himena.standards import plotting as hplt
from himena_builtins.qt.plot._canvas import QModelMatplotlibCanvas
import pandas as pd


class QPlotCanvas(QModelMatplotlibCanvas):
    """A matplotlib canvas widget for plotting."""

    def __init__(self):
        super().__init__()
        self.setFixedSize(340, 180)

    def plot_fsc_refine(self, df: pd.DataFrame):
        x = df["rlnResolution"]
        xticklabels = df["rlnAngstromResolution"]
        fsc = df["rlnGoldStandardFsc"]
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
        fig = hplt.figure()
        x = df["rlnResolution"]
        xticklabels = df["rlnAngstromResolution"]
        fsc_corrected = df["rlnFourierShellCorrelationCorrected"]
        # df["rlnFourierShellCorrelationParticleMaskFraction"]
        fsc_unmask = df["rlnFourierShellCorrelationUnmaskedMaps"]
        fsc_mask = df["rlnFourierShellCorrelationMaskedMaps"]
        # df["rlnCorrectedFourierShellCorrelationPhaseRandomizedMaskedMaps"]
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
        self.figure.tight_layout(pad=0)
        self._canvas.draw()


def _res_to_str(res: float):
    if res >= 998.9:
        # RELION uses 999 to indicate infinity
        return "Inf"
    return f"{res:.1f}"
