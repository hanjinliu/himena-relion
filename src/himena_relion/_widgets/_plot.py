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
        # xlabels = df["rlnAngstromResolution"]
        fsc = df["rlnGoldStandardFsc"]
        fig = hplt.figure()
        fig.plot(x, fsc, name="FSC")
        self.update_model(WidgetDataModel(value=fig, type=StandardType.PLOT))

    def plot_fsc_postprocess(self, df: pd.DataFrame):
        fig = hplt.figure()
        x = df["rlnResolution"]
        # xlabels = df["rlnAngstromResolution"]
        fsc_corrected = df["rlnFourierShellCorrelationCorrected"]
        # df["rlnFourierShellCorrelationParticleMaskFraction"]
        fsc_unmask = df["rlnFourierShellCorrelationUnmaskedMaps"]
        fsc_mask = df["rlnFourierShellCorrelationMaskedMaps"]
        # df["rlnCorrectedFourierShellCorrelationPhaseRandomizedMaskedMaps"]
        fig.plot(x, fsc_unmask, name="Unmasked")
        fig.plot(x, fsc_mask, name="Masked")
        fig.plot(x, fsc_corrected, name="Corrected")
        self.update_model(WidgetDataModel(value=fig, type=StandardType.PLOT))
        fig.x.ticks

    def _prep_toolbar(self, cls):
        return FakeToolbar()


class FakeToolbar:
    def pan(self, *args, **kwargs):
        pass
