from __future__ import annotations

from typing import TYPE_CHECKING
from dataclasses import dataclass
import numpy as np

if TYPE_CHECKING:
    from superqt.utils import GeneratorWorker


@dataclass
class TubeObject:
    """Data class for cylinder object in BILD file."""

    start: np.ndarray
    end: np.ndarray
    radius: float
    color: np.ndarray


@dataclass
class RelionJobIsTesting:
    """Only used as the metadata of WidgetDataModel when testing."""


IS_TESTING = False


def set_is_testing(value: bool):
    global IS_TESTING
    IS_TESTING = value


def start_worker(worker: GeneratorWorker):
    """Start running the worker.

    This function will run the worker synchronously if in testing mode."""
    if IS_TESTING:
        return worker.run()
    return worker.start()
