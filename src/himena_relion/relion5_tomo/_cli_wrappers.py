from __future__ import annotations

import subprocess
from pathlib import Path

from dataclasses import dataclass
from himena.plugins import register_config, config_field, get_config


@dataclass
class RelionConfig:
    motioncor2 = config_field(default="", tooltip="Path to the MotionCor2 executable")
    batchruntomo = config_field(
        default="", tooltip="Path to the batchruntomo executable"
    )


register_config("himena-relion", "RELION", RelionConfig())


def import_tomogram(
    tilt_image_movie_pattern: str,
    mdoc_file_pattern: str,
    nominal_tilt_axis_angle: float = 90,
    nominal_pixel_size: float = 2.6,
    voltage: float = 200,
    spherical_aberration: float = 2.7,
    amplitude_contrast: float = 0.1,
    optics_group_name: str = "",
    dose_per_tilt_image: float = 3.1,
    invert_defocus_handledness: bool = True,
    output_directory: str = "Import/job001/",
):
    out_dir = Path(output_directory)
    if out_dir.exists():
        raise FileExistsError(
            f"Output directory {out_dir} already exists. Please choose a different directory."
        )
    args = [
        "relion_python_tomo_import",
        "SerialEM",
        "--tilt-image-movie-pattern",
        tilt_image_movie_pattern,
        "--mdoc-file-pattern",
        mdoc_file_pattern,
        "--nominal-tilt-axis-angle",
        str(nominal_tilt_axis_angle),
        "--nominal-pixel-size",
        str(nominal_pixel_size),
        "--use-motioncor2",
        "--voltage",
        str(voltage),
        "--spherical-aberration",
        str(spherical_aberration),
        "--amplitude-contrast",
        str(amplitude_contrast),
        "--tilt-image-movie-pattern",
        tilt_image_movie_pattern,
        "--optics-group-name",
        optics_group_name,
        "--dose-per-tilt-image",
        str(dose_per_tilt_image),
        "--output-directory",
        output_directory,
        "--pipeline_control",
        output_directory,
    ]

    if invert_defocus_handledness:
        args.append("--invert-defocus-handedness")
    subprocess.Popen(args, check=True)


def motion_correction_motioncor2(
    input_star: str,
    output_directory: str = "MotionCorr/job010/",
    even_odd_split: bool = True,
    gpu: list[int] = [0],
    defect_file: str = "",
    bin_factor: int = 1,
    bfactor: int = 150,
    patch_x: int = 5,
    patch_y: int = 5,
    eer_grouping: int = 32,
    pipeline_control: str = "MotionCorr/job010/",
):
    gpu_ids = ",".join(map(str, gpu))
    cfg = get_config(RelionConfig) or RelionConfig()
    motioncor2_exe = cfg.motioncor2
    if not motioncor2_exe:
        raise ValueError("MotionCor2 executable path is not set in the configuration.")
    args = [
        "relion_run_motioncorr_mpi",
        "--i",
        input_star,
        "--o",
        output_directory,
        "--motioncor2_exe",
        motioncor2_exe,
        "--gpu",
        gpu_ids,
        "--defect_file",
        defect_file,
        "--bin_factor",
        str(bin_factor),
        "--bfactor",
        str(bfactor),
        "--patch_x",
        str(patch_x),
        "--patch_y",
        str(patch_y),
        "--eer_grouping",
        str(eer_grouping),
        "--pipeline_control",
        pipeline_control,
    ]
    if even_odd_split:
        args.append("--even_odd_split")
    subprocess.Popen(args, check=True)


def motion_correction_relion(
    input_star: str,
    output_directory: str = "MotionCorr/job004/",
    even_odd_split: bool = True,
    j: int = 4,
    float16: bool = True,
    bin_factor: int = 1,
    bfactor: int = 150,
    patch_x: int = 5,
    patch_y: int = 5,
    eer_grouping: int = 32,
    grouping_for_ps: int = 4,
    only_do_unfinished: bool = False,
    pipeline_control: str = "MotionCorr/job004/",
):
    cfg = get_config(RelionConfig) or RelionConfig()
    relion_exe = cfg.motioncor2
    if not relion_exe:
        raise ValueError("RELION executable path is not set in the configuration.")

    args = [
        "relion_run_motioncorr_mpi",
        "--i",
        input_star,
        "--o",
        output_directory,
        "--relion_exe",
        relion_exe,
        "--even_odd_split" if even_odd_split else "",
        "--j",
        str(j),
        "--bin_factor",
        str(bin_factor),
        "--bfactor",
        str(bfactor),
        "--patch_x",
        str(patch_x),
        "--patch_y",
        str(patch_y),
        "--eer_grouping",
        str(eer_grouping),
        "--grouping_for_ps",
        str(grouping_for_ps),
        "--pipeline_control",
        pipeline_control,
    ]
    if float16:
        args.append("--float16")
    if only_do_unfinished:
        args.append("--only_do_unfinished")
    subprocess.Popen(args, check=True)
