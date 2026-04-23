"""Normalization functions for different version of RELION."""

from __future__ import annotations
from typing import Any
import warnings
from himena_relion._version import relion_version_info


def norm_blush_reg(kwargs: dict[str, Any]) -> dict[str, Any]:
    ver = relion_version_info("5.0.0").version
    if ver.major == 5:
        blush_reg = kwargs.pop("blush_reg", "No")
        kwargs["do_blush"] = blush_reg != "No"
        if ver.minor == 0:
            if blush_reg == "amy-v1.0":
                warnings.warn(
                    "Blush regularisation method 'amy-v1.0' is selected but is not "
                    "supported in RELION 5.0",
                    UserWarning,
                    stacklevel=1,
                )
        elif ver.minor >= 1:
            kwargs["blush_version"] = blush_reg if blush_reg != "No" else "v1.0"
    return kwargs


def norm_blush_reg_inv(kwargs: dict[str, Any]) -> dict[str, Any]:
    do_blush = kwargs.pop("do_blush", False)
    blush_version = kwargs.pop("blush_version", "v1.0")
    kwargs["blush_reg"] = "No" if not do_blush else blush_version
    return kwargs


def norm_extract_subtomo(kwargs: dict[str, Any]) -> dict[str, Any]:
    ver = relion_version_info("5.0.0").version
    if ver.major == 5:
        if ver.minor == 0:
            subtomo_format = kwargs.pop("subtomo_format", "2D stacks")
            if subtomo_format == "3D subtomos":
                warnings.warn(
                    "Subtomogram format '3D subtomos' is selected but is not "
                    "supported in RELION 5.0",
                    UserWarning,
                    stacklevel=1,
                )
            kwargs["do_stack2d"] = subtomo_format == "2D stacks"
    return kwargs


def norm_extract_subtomo_inv(kwargs: dict[str, Any]) -> dict[str, Any]:
    ver = relion_version_info("5.0.0").version
    if ver.major == 5:
        if ver.minor == 0:
            do_stack2d = kwargs.pop("do_stack2d", True)
            kwargs["subtomo_format"] = (
                "2D stacks" if do_stack2d else "3D pseudo-subtomos"
            )
    return kwargs


def norm_reconstruct_tomo(kwargs: dict[str, Any]) -> dict[str, Any]:
    ver = relion_version_info("5.0.0").version
    if ver.major == 5:
        if ver.minor == 0:
            if kwargs.pop("do_skip_wiener", False):
                warnings.warn(
                    "Option 'Skip Wiener filtering' is selected but is not "
                    "supported in RELION 5.0",
                    UserWarning,
                    stacklevel=1,
                )
    return kwargs


def norm_aligntilts(kwargs: dict[str, Any]) -> dict[str, Any]:
    ver = relion_version_info("5.0.0").version
    if ver.major == 5:
        if ver.minor == 0:
            if kwargs.pop("do_aretomo_reconstruct", False):
                warnings.warn(
                    "Option 'Reconstruct with AreTomo' is selected but is not "
                    "supported in RELION 5.0",
                    UserWarning,
                    stacklevel=1,
                )
            if kwargs.pop("do_skip_aretomo_align", False):
                warnings.warn(
                    "Option 'Skip AreTomo alignment' is selected but is not "
                    "supported in RELION 5.0",
                    UserWarning,
                    stacklevel=1,
                )
            kwargs.pop("aretomo_VolZ", None)
            kwargs.pop("aretomo_OutBin", None)
        else:
            kwargs["do_skip_aretomo_align"] = False
    return kwargs
