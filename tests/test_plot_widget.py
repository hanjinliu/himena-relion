import polars as pl
import pandas as pd
from himena_relion._widgets._plot import QPlotCanvas

def test_plot_widget(qtbot):
    widget = QPlotCanvas()
    qtbot.addWidget(widget)
    df = pl.DataFrame({
        "rlnTomoNominalStageTiltAngle": [0, 10, 20, 30],
        "rlnDefocusU": [10000, 20000, 15000, 25000],
        "rlnDefocusV": [12000, 22000, 17000, 27000],
    })
    widget.plot_defocus(df)
    df = pl.DataFrame({
        "rlnDefocusU": [10000, 20000, 15000, 25000],
        "rlnDefocusV": [12000, 22000, 17000, 27000],
    })
    widget.plot_defocus(df)

    df = pl.DataFrame({"rlnCtfScalefactor": [1.0, 0.8, 1.2, 0.9]})
    widget.plot_ctf_scale(df)
    df = pl.DataFrame({"rlnCtfAstigmatism": [500, 300, 700, 400]})
    widget.plot_ctf_astigmatism(df)
    df = pl.DataFrame({"rlnDefocusAngle": [0, 45, 90, 135]})
    widget.plot_ctf_defocus_angle(df)
    df = pl.DataFrame({"rlnCtfMaxResolution": [3.0, 4.0, 2.5, 3.5]})
    widget.plot_ctf_max_resolution(df)

    ycol = "val-test"
    df_train = pd.DataFrame({
        "epoch": [1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 4],
        ycol: [0.5, 0.6, 0.55, 0.4, 0.45, 0.42, 0.35, 0.38, 0.36, 0.3, 0.32, 0.31],
    })
    df_test = pd.DataFrame({
        "epoch": [1, 2, 3, 4],
        ycol: [0.52, 0.43, 0.37, 0.33],
    })
    widget.plot_topaz_train(df_train, df_test, ycol)

    df = pl.DataFrame({
        "rlnResolution": [0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4],
        "rlnAngstromResolution": [10.0, 9.9, 9.8, 9.7, 9.6, 9.5, 9.4, 9.3],
        "rlnGoldStandardFsc": [0.9, 0.7, 0.5, 0.3, 0.25, 0.2, 0.1, 0.05],
    })
    widget.plot_fsc_refine(df, 0.25)

    widget.plot_hist([1, 2, 2, 3, 3, 3, 4, 4, 4, 4], "X", bins=3)
