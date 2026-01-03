from __future__ import annotations

from dataclasses import dataclass
import numpy as np


@dataclass
class TubeObject:
    """Data class for cylinder object in BILD file."""

    start: np.ndarray
    end: np.ndarray
    radius: float
    color: np.ndarray
