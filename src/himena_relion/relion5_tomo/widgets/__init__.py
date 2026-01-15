from himena_relion.relion5 import widgets  # install SPA widgets
from himena_relion.relion5_tomo.widgets import (
    _aligntilt,
    _ctf,
    _import,
    _extract,
    _tilt_series,
    _tomogram,
    _reconstruct,
    _polish,
)

del (
    widgets,
    _aligntilt,
    _ctf,
    _tomogram,
    _import,
    _extract,
    _reconstruct,
    _tilt_series,
    _polish,
)
