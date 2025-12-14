from pathlib import Path
from typing import Any, get_origin


def _split_list_and_arg(typ: Any) -> tuple[Any, Any]:
    if getattr(typ, "__origin__", None) is list:
        args = typ.__args__
        if len(args) != 1:
            raise TypeError(f"Unsupported list type with multiple args: {typ}")
        return list, args[0]
    else:
        return typ, str


def parse_string(s: str, typ: Any) -> Any:
    if isinstance(typ, str):
        raise TypeError("Type annotation cannot be a string instance")
    if typ is str:
        return s
    elif typ is int:
        return int(s)
    elif typ is float:
        return float(s)
    elif typ is bool:
        if s == "0":
            return False
        elif s == "1":
            return True
        else:
            raise ValueError(f"Cannot parse boolean from string: {s}")
    elif typ is Path:
        return Path(s)
    elif get_origin(typ) is list:
        _, elem = _split_list_and_arg(typ)
        return [parse_string(part, elem) for part in s.split(",")]
    else:
        raise TypeError(f"Unsupported type for parsing: {typ}")
