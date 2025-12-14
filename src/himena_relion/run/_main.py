# Widget to run a job inside himena app
from __future__ import annotations
import inspect
import subprocess
from typing import Callable

from qtpy import QtWidgets as QtW

import starfile


class QJobRunner(QtW.QWidget):
    def __init__(self):
        super().__init__()
        layout = QtW.QVBoxLayout(self)
        self._parameters = QParameters()
        layout.addWidget(self._parameters)
        self._run_btn = QtW.QPushButton("Run")
        self._run_btn.clicked.connect(self._run_job)

    def _run_job(self): ...

    def _build_from_func(self, func: Callable):
        sig = inspect.signature(func)
        for name, param in sig.parameters.items():
            if name == "o":
                pass
            elif name in [
                "in_movies",
                "in_mics",
                "in_parts",
                "in_coords",
                "in_3dref",
                "in_mask",
            ]:
                ...
            else:
                ...


class QParameters(QtW.QWidget):
    def __init__(self):
        super().__init__()
        layout = QtW.QFormLayout(self)
        self._param1 = QtW.QLineEdit()
        layout.addRow("Parameter 1:", self._param1)
        self._param2 = QtW.QSpinBox()
        layout.addRow("Parameter 2:", self._param2)


def run_job(job_directory: str):
    # Running RELION job is like this:
    # relion_pipeliner --RunJobs External/job018/
    subprocess.Popen(
        ["relion_pipeliner", "--RunJobs", job_directory],
        check=True,
    )


def last_job_directory() -> str:
    df = starfile.read("default_pipeline.star")
    path_last = df["pipeline_processes"]["rlnPipeLineProcessName"].iloc[-1]
    return path_last
