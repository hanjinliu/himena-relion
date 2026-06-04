"""Popup widgets for relion_refine jobs."""

from __future__ import annotations

from pathlib import Path
from qtpy import QtWidgets as QtW
import polars as pl
from starfile_rs import read_star
from himena import MainWindow
from himena.core import create_dataframe_model
from himena_builtins.qt.dataframe import QDataFrameView
from himena_relion._job_dir import JobDirectory
from himena_relion._widgets import QPlotCanvas


class RefineJobPopup(QtW.QWidget):
    def __init__(
        self,
        ui: MainWindow,
        job_dir: JobDirectory,
        include_classes: bool = True,
        model_suffix: str | None = "_half1_model",
    ):
        super().__init__()
        layout = QtW.QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)

        df = collect_for_iters(
            job_dir.path,
            include_classes=include_classes,
            model_suffix=model_suffix,
        )
        df_view = QDataFrameView(ui)
        df_view.update_model(create_dataframe_model(df, editable=False))
        df_view.setMaximumWidth(380)
        widget_right = QtW.QWidget()

        layout.addWidget(df_view)
        layout.addWidget(widget_right)

        layout_right = QtW.QGridLayout(widget_right)
        layout_right.setContentsMargins(0, 0, 0, 0)
        ncols = 2
        ith = 0
        self._canvases: list[QPlotCanvas] = []
        df_it1 = df.filter(pl.col("rlnCurrentIteration") > 0)
        for ycol, ylabel, title in [
            ("rlnChangesOptimalClasses", "Change", "Changes of Optimal Classes"),
            ("rlnCurrentResolution", "Resolution (Å)", "Current Resolution"),
            (
                "rlnOverallAccuracyRotations",
                "Accuracy (°)",
                "Overall Accuracy of Rotations",
            ),
            (
                "rlnOverallAccuracyTranslationsAngst",
                "Accuracy (Å)",
                "Overall Accuracy of Translations",
            ),
            (
                "rlnChangesOptimalOrientations",
                "Change (°)",
                "Changes of Optimal Orientations",
            ),
            ("rlnChangesOptimalOffsets", "Change (pix)", "Changes of Optimal Offsets"),
        ]:
            if ycol not in df_it1.columns:
                continue
            r0 = ith // ncols
            c0 = ith % ncols
            canvas = plot(df_it1, ycol, ylabel, title)
            layout_right.addWidget(canvas, r0, c0)
            self._canvases.append(canvas)
            ith += 1

    def widget_added_callback(self):
        for canvas in self._canvases:
            canvas.widget_added_callback()


def plot(df: pl.DataFrame, ycol: str, ylabel: str, title: str) -> QPlotCanvas:
    canvas = QPlotCanvas()
    df = df.filter(pl.col(ycol).is_not_null())
    canvas._plot_single_impl(
        df["rlnCurrentIteration"],
        df.get_column(ycol, default=None),
        xlabel="Iteration",
        ylabel=ylabel,
        title=title,
    )
    return canvas


def collect_for_iters(
    root: Path,
    include_classes: bool = True,
    model_suffix: str | None = "_model",
) -> pl.DataFrame:
    rows = [
        read_star(path).first().trust_single().to_dict()
        for path in root.glob("run_it*_optimiser.star")
    ]
    columns = [
        pl.col("rlnCurrentIteration"),
        _replace_with_null("rlnOverallAccuracyRotations", 998),
        _replace_with_null("rlnOverallAccuracyTranslationsAngst", 998),
        pl.col("rlnChangesOptimalOrientations"),
        pl.col("rlnChangesOptimalOffsets"),
    ]
    if include_classes:
        columns += [pl.col("rlnChangesOptimalClasses")]
    df = pl.DataFrame(rows).select(*columns).sort("rlnCurrentIteration")
    if model_suffix is not None:
        rows_res = []
        for path in root.glob(f"run_it*{model_suffix}.star"):
            model_dict = read_star(path).first().trust_single().to_dict()
            model_dict["rlnCurrentIteration"] = int(path.stem.split("_")[1][2:])
            rows_res.append(model_dict)
        if len(rows_res) > 0:
            df_res = pl.DataFrame(rows_res).select(
                pl.col("rlnCurrentIteration"),
                pl.col("rlnCurrentResolution").cast(pl.Float32, strict=False),
            )
            df = df.join(df_res, on="rlnCurrentIteration", how="left")
    return df


def _replace_with_null(colname: str, thresh: float):
    return (
        pl.when(pl.col(colname).lt(thresh))
        .then(pl.col(colname))
        .otherwise(pl.lit(float("nan")))
    )
