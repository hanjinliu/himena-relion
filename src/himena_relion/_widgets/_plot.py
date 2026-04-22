from __future__ import annotations
from typing import Any
import numpy as np
import pandas as pd
import polars as pl
from himena.style import Theme
from himena.widgets import current_instance
from himena import StandardType, WidgetDataModel
from himena.standards import plotting as hplt
from himena_builtins.qt.plot._canvas import QModelMatplotlibCanvas


class QPlotCanvas(QModelMatplotlibCanvas):
    """A matplotlib canvas widget for plotting."""

    def __init__(self, parent=None):
        super().__init__()
        self.setParent(parent)
        self.setMaximumSize(400, 280)
        self.setMinimumSize(300, 200)
        self._size = 3
        self.clear()

    def clear(self):
        """Clear the plot."""
        fig = hplt.figure(self._main_theme().background)
        self.update_model(WidgetDataModel(value=fig, type=StandardType.PLOT))

    def plot_defocus(self, df: pl.DataFrame):
        theme = self._main_theme()
        fig = hplt.figure(theme.background)

        if "rlnTomoNominalStageTiltAngle" in df.columns:
            # this is a tilt series
            x = df["rlnTomoNominalStageTiltAngle"]
            xlabel = "Nominal stage tilt angle (°)"
        else:
            # just micrographs
            x = np.arange(len(df))
            xlabel = "Micrograph"
        defocus_u_um = df["rlnDefocusU"] / 10000
        defocus_v_um = df["rlnDefocusV"] / 10000
        color_u = "#1f17f483" if theme.is_light_background() else "#00ced183"
        color_v = "#ff77b483" if theme.is_light_background() else "#ff69b483"
        fig.scatter(
            x, defocus_u_um, name="U", size=self._size, width=0.5, color=color_u
        )
        fig.scatter(
            x, defocus_v_um, name="V", size=self._size, width=0.5, color=color_v
        )
        fig.x.label = xlabel
        fig.y.label = "Def. (µm)"
        self.update_model(WidgetDataModel(value=fig, type=StandardType.PLOT))
        self.tight_layout()

    def plot_ctf_scale(self, df: pl.DataFrame):
        return self._plot_single(df, "rlnCtfScalefactor", "Scale")

    def plot_ctf_astigmatism(self, df: pl.DataFrame):
        return self._plot_single(df, "rlnCtfAstigmatism", "Ast. (A)")

    def plot_ctf_defocus_angle(self, df: pl.DataFrame):
        return self._plot_single(df, "rlnDefocusAngle", "Angle (°)")

    def plot_ctf_max_resolution(self, df: pl.DataFrame):
        return self._plot_single(df, "rlnCtfMaxResolution", "Res. (Å)")

    def _plot_single(self, df: pl.DataFrame, ycol: str, ylabel: str):
        theme = self._main_theme()
        fig = hplt.figure(theme.background)

        if "rlnTomoNominalStageTiltAngle" in df.columns:
            # this is a tilt series
            xvals = df["rlnTomoNominalStageTiltAngle"]
            xlabel = "Nominal stage tilt angle (°)"
        else:
            # just micrographs
            xvals = np.arange(len(df))
            xlabel = "Micrograph"
        if ycol in df.columns:
            yvals = df[ycol]
            color_u = "#1f17f483" if theme.is_light_background() else "#00ced183"
            fig.scatter(xvals, yvals, size=self._size, width=0.5, color=color_u)
        fig.x.label = xlabel
        fig.y.label = ylabel
        self.update_model(WidgetDataModel(value=fig, type=StandardType.PLOT))
        self.tight_layout()

    def plot_topaz_train(
        self, df_train: pd.DataFrame, df_test: pd.DataFrame, ycol: str
    ):
        theme = self._main_theme()
        fig = hplt.figure(theme.background)
        epoch = df_test["epoch"]
        y_train_group = df_train.groupby("epoch", sort=True)[ycol]
        y_test = df_test[ycol]
        color_test = "#ff7f0e" if theme.is_light_background() else "#ff69b4"
        color_train = "#1f77b4" if theme.is_light_background() else "#00ced1"
        fig.plot(epoch, y_test, name="Test", color=color_test)
        fig.errorbar(
            epoch,
            y_train_group.mean(),
            y_error=y_train_group.std(),
            capsize=2,
            name="Train",
            color=color_train,
            edge_width=1,
        )
        fig.x.label = "Epoch"
        fig.set_legend(font_size=9.0)
        self.update_model(WidgetDataModel(value=fig, type=StandardType.PLOT))
        self.tight_layout()

    def plot_cryocare_train(self, hist: dict, ycol: str):
        theme = self._main_theme()
        fig = hplt.figure(theme.background)
        ytrain = hist[ycol]
        yval = hist[f"val_{ycol}"]
        epoch = np.arange(1, len(ytrain) + 1)
        color_train = "#ff7f0e" if theme.is_light_background() else "#ff69b4"
        color_val = "#1f77b4" if theme.is_light_background() else "#00ced1"
        fig.plot(epoch, ytrain, name="Train", color=color_train)
        fig.plot(epoch, yval, name="Validation", color=color_val)
        fig.x.label = "Epoch"
        fig.set_legend(font_size=9.0)
        self.update_model(WidgetDataModel(value=fig, type=StandardType.PLOT))
        self.tight_layout()

    def plot_fsc_refine(self, df: pl.DataFrame, resolution: float | None = None):
        x = df["rlnResolution"]
        xticklabels = df["rlnAngstromResolution"]
        fsc = df["rlnGoldStandardFsc"]
        theme = self._main_theme()
        fig = hplt.figure(theme.background)
        color = "#161692" if theme.is_light_background() else "#00ced1"
        fig.plot(x, fsc, color=color, name="FSC", width=1.5)
        fig.x.set_ticks(
            x[:: len(x) // 5],
            labels=[_res_to_str(r) for r in xticklabels[:: len(x) // 5]],
        )
        if resolution is not None and np.isfinite(resolution):
            text = format(resolution, ".2f") + " Å"
            text_color = theme.foreground
            fig.text(
                [0.0], [0.0], [text], anchor="bottom_left", size=10, color=text_color
            )
        self._fsc_finalize(fig)

    def plot_fsc_postprocess(self, df: pl.DataFrame, general: dict[str, Any]):
        x = df["rlnResolution"]
        xticklabels = df["rlnAngstromResolution"]
        fsc_corrected = df["rlnFourierShellCorrelationCorrected"]
        fsc_unmask = df["rlnFourierShellCorrelationUnmaskedMaps"]
        fsc_mask = df["rlnFourierShellCorrelationMaskedMaps"]
        res = float(general["rlnFinalResolution"])
        theme = self._main_theme()
        fig = hplt.figure(theme.background)
        fig.plot(x, fsc_unmask, name="Unmasked")
        fig.plot(x, fsc_mask, name="Masked")
        fig.plot(x, fsc_corrected, name="Corrected")
        fig.x.set_ticks(
            x[:: len(x) // 5],
            labels=[_res_to_str(r) for r in xticklabels[:: len(x) // 5]],
        )
        text = format(res, ".2f") + " Å"
        text_color = theme.foreground
        fig.text([0.0], [0.0], [text], anchor="bottom_left", size=10, color=text_color)
        fig.set_legend(font_size=9.0)
        self._fsc_finalize(fig)

    def plot_hist(
        self,
        arr,
        xlabel: str,
        bins: int = 50,
        range: tuple[float, float] | None = None,
    ):
        theme = self._main_theme()
        bincolor = "#1f77b4" if theme.is_light_background() else "#00ced1"
        fig = hplt.figure()
        fig.hist(
            arr, bins=bins, color=bincolor, edge_color=theme.foreground, range=range
        )
        fig.x.label = xlabel
        fig.y.label = "Count"
        self.update_model(WidgetDataModel(value=fig, type=StandardType.PLOT))
        self.tight_layout()

    def tight_layout(self):
        """Tighten the layout of the plot."""
        self.figure.tight_layout(pad=1.05)
        self._canvas.draw()

    def _fsc_finalize(self, fig: hplt.SingleAxes):
        fig.x.label = "Resolution (Å)"
        fig.y.label = "FSC"
        fig.y.lim = (-0.04, 1.04)
        self.update_model(WidgetDataModel(value=fig, type=StandardType.PLOT))
        self.tight_layout()

    def _main_theme(self) -> Theme:
        try:
            return current_instance().theme
        except Exception:
            # No current instance, return a default theme
            return Theme.from_global("light-blue")


def _res_to_str(res: float):
    if res >= 998.9:
        # RELION uses 999 to indicate infinity
        return "Inf"
    return f"{res:.1f}"
