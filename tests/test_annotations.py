from types import ModuleType
from typing import Annotated
from himena_relion import _annotated as _a

_AnnotatedType = type(Annotated[int, ""])

def test_tooltips_are_string():
    for val in _a.__dict__.values():
        if isinstance(val, ModuleType):
            for subval in val.__dict__.values():
                if isinstance(subval, _AnnotatedType):
                    metadata = subval.__metadata__[0]
                    assert isinstance(metadata, dict)
                    tooltip = metadata.get("tooltip", "")
                    assert isinstance(tooltip, str), f"Tooltip for {subval} is not a string"
