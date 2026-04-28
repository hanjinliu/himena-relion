from pathlib import Path
import subprocess
from typing import Annotated

import polars as pl
import mrcfile
from starfile_rs import as_star
from himena_relion.consts import MenuId
from himena_relion.external import RelionExternalJob
from himena_relion._annotated.io import IN_TILT, DO_F16
from himena_relion.schemas import TSGroupModel, TSModel


class ReconstructTomoIMOD(RelionExternalJob):
    """Reconstruct tomograms using IMOD's `tilt` command."""

    def output_nodes(self):
        return [("tomograms.star", "TomoOptimisationSet.star")]

    @classmethod
    def import_path(cls):
        return f"himena_relion.relion5_tomo:{cls.__name__}"

    @classmethod
    def job_title(cls):
        return "Reconstruct Tomos (IMOD)"

    @classmethod
    def menu_id(cls):
        return MenuId.RELION_TOMO_RECON_JOB

    def provide_widget(self, job_dir):
        from .widgets import QIMODTomogramViewer

        return QIMODTomogramViewer(job_dir)

    def run(
        self,
        in_mics: IN_TILT,  # path,
        outbin: Annotated[int, {"label": "Tomogram binning"}] = 1,
        thickness: Annotated[int, {"label": "Tomogram thickness (unbinned pix)"}] = 600,
        filter_cutoff: float = 0.35,
        filter_falloff: float = 0.035,
        do_float16: DO_F16 = True,
        gpu_id_to_use: str = "",
    ):
        # IMOD's GPU IDs are 1-based, and 0 means "auto"
        gpu_id_imod = 0 if gpu_id_to_use == "" else int(gpu_id_to_use) + 1
        # prepare output directories
        _dir_tomo = self.output_job_dir.path.joinpath("tomograms")
        _dir_tilt_series = self.output_job_dir.path.joinpath("tilt_series")
        _dir_fileinlists = self.output_job_dir.path.joinpath("fileinlists")
        _dir_tomo.mkdir(exist_ok=True)
        _dir_tilt_series.mkdir(exist_ok=True)
        _dir_fileinlists.mkdir(exist_ok=True)

        tsgroup = TSGroupModel.validate_file(self.output_job_dir.resolve_path(in_mics))
        if tsgroup.etomo_directive_file is None:
            raise ValueError(
                "Input STAR file must contain rlnEtomoDirectiveFile column. Please "
                "double check that AlignTiltSeries job has been applied to the input "
                "STAR file."
            )
        num_tomo = len(tsgroup.etomo_directive_file)

        self.console.log(f" --- Reconstruction of {num_tomo} tomograms using IMOD --- ")
        out_size = []
        for ith in range(num_tomo):
            prog = f"({ith + 1}/{num_tomo})"
            tomo_name = tsgroup.tomo_name[ith]
            self.console.log(f"{prog} Start reconstruction of {tomo_name!r}.")
            ts = TSModel.validate_file(tsgroup.tomo_tilt_series_star_file[ith])
            mic_names = ts.ts_paths_sorted(self.output_job_dir.relion_project_dir)
            num_tilts = len(mic_names)
            if num_tilts == 0:
                continue
            fileinlist_path = _dir_fileinlists.joinpath(f"{tomo_name}.txt")
            fileinlist_path.write_text(_fileinlist_text(num_tilts, mic_names))

            with mrcfile.open(mic_names[0], header_only=True) as mrc:
                if ts.need_rot90():
                    tomo_size = int(mrc.header.nx), int(mrc.header.ny), thickness
                else:
                    tomo_size = int(mrc.header.ny), int(mrc.header.nx), thickness

            success = yield from _run_impl(
                edf_path=self.output_job_dir.resolve_path(
                    tsgroup.etomo_directive_file[ith]
                ),
                fileinlist_path=fileinlist_path,
                tomo_name=tomo_name,
                output_tomo_path=_dir_tomo / f"rec_{tomo_name}.mrc",
                tomo_size=tomo_size,
                outbin=outbin,
                do_float16=do_float16,
                filter_cutoff=filter_cutoff,
                filter_falloff=filter_falloff,
                gpu_id_imod=gpu_id_imod,
            )

            if not success:
                self.console.log(f"Failed to reconstruct {tomo_name!r}. Skipping.")
                continue

            out_size.append(tomo_size)
            yield

        self.console.log("Reconstruction finished successfully.")
        tomo_star_path = self.output_job_dir.path.joinpath("tomograms.star")
        df_out = tsgroup.dataframe.with_columns(
            pl.lit(outbin).cast(pl.Float32).alias("rlnTomoTomogramBinning"),
        ).with_columns(
            pl.DataFrame(
                out_size,
                schema=["rlnTomoSizeX", "rlnTomoSizeY", "rlnTomoSizeZ"],
                orient="row",
            ),
        )
        as_star({"global": df_out}).write(tomo_star_path)


class ReconstructHalfTomoIMOD(RelionExternalJob):
    def output_nodes(self):
        return [("tomograms.star", "TomoOptimisationSet.star")]

    @classmethod
    def import_path(cls):
        return f"himena_relion.relion5_tomo:{cls.__name__}"

    @classmethod
    def job_title(cls):
        return "Reconstruct Tomos (IMOD)"

    @classmethod
    def menu_id(cls):
        return MenuId.RELION_TOMO_RECON_JOB

    def provide_widget(self, job_dir):
        from .widgets import QIMODTomogramHalvesViewer

        return QIMODTomogramHalvesViewer(job_dir)

    def run(
        self,
        in_mics: IN_TILT,  # path,
        outbin: Annotated[int, {"label": "Tomogram binning"}] = 1,
        thickness: Annotated[int, {"label": "Tomogram thickness (unbinned pix)"}] = 600,
        filter_cutoff: float = 0.35,
        filter_falloff: float = 0.035,
        do_float16: DO_F16 = True,
        gpu_id_to_use: str = "",
    ):
        # IMOD's GPU IDs are 1-based, and 0 means "auto"
        gpu_id_imod = 0 if gpu_id_to_use == "" else int(gpu_id_to_use) + 1
        # prepare output directories
        _dir_tomo = self.output_job_dir.path.joinpath("tomograms")
        _dir_tilt_series = self.output_job_dir.path.joinpath("tilt_series")
        _dir_fileinlists = self.output_job_dir.path.joinpath("fileinlists")
        _dir_tomo.mkdir(exist_ok=True)
        _dir_tilt_series.mkdir(exist_ok=True)
        _dir_fileinlists.mkdir(exist_ok=True)

        tsgroup = TSGroupModel.validate_file(self.output_job_dir.resolve_path(in_mics))
        if tsgroup.etomo_directive_file is None:
            raise ValueError(
                "Input STAR file must contain rlnEtomoDirectiveFile column. Please "
                "double check that AlignTiltSeries job has been applied to the input "
                "STAR file."
            )
        num_tomo = len(tsgroup.etomo_directive_file)

        self.console.log(f" --- Reconstruction of {num_tomo} tomograms using IMOD --- ")
        out_size = []
        for ith in range(num_tomo):
            prog = f"({ith + 1}/{num_tomo})"
            tomo_name = tsgroup.tomo_name[ith]
            self.console.log(f"{prog} Start reconstruction of {tomo_name!r}.")
            ts = TSModel.validate_file(tsgroup.tomo_tilt_series_star_file[ith])

            even_names, odd_names = ts.ts_even_odd_paths_sorted(
                self.output_job_dir.relion_project_dir
            )
            num_tilts = len(even_names)
            if num_tilts == 0:
                continue

            fileinlist_path_even = _dir_fileinlists.joinpath(f"{tomo_name}_EVN.txt")
            fileinlist_path_even.write_text(_fileinlist_text(num_tilts, even_names))
            fileinlist_path_odd = _dir_fileinlists.joinpath(f"{tomo_name}_ODD.txt")
            fileinlist_path_odd.write_text(_fileinlist_text(num_tilts, odd_names))

            with mrcfile.open(even_names[0], header_only=True) as mrc:
                if ts.need_rot90():
                    tomo_size = int(mrc.header.nx), int(mrc.header.ny), thickness
                else:
                    tomo_size = int(mrc.header.ny), int(mrc.header.nx), thickness

            for fpath, half in [(fileinlist_path_even, 1), (fileinlist_path_odd, 2)]:
                success = yield from _run_impl(
                    edf_path=self.output_job_dir.resolve_path(
                        tsgroup.etomo_directive_file[ith]
                    ),
                    fileinlist_path=fpath,
                    tomo_name=tomo_name,
                    output_tomo_path=_dir_tomo / f"rec_{tomo_name}_half{half}.mrc",
                    tomo_size=tomo_size,
                    outbin=outbin,
                    do_float16=do_float16,
                    filter_cutoff=filter_cutoff,
                    filter_falloff=filter_falloff,
                    gpu_id_imod=gpu_id_imod,
                )

                if not success:
                    self.console.log(f"Failed to reconstruct {tomo_name!r}. Skipping.")
                    continue

            out_size.append(tomo_size)
            yield

        self.console.log("Reconstruction finished successfully.")
        tomo_star_path = self.output_job_dir.path.joinpath("tomograms.star")
        df_out = tsgroup.dataframe.with_columns(
            pl.lit(outbin).cast(pl.Float32).alias("rlnTomoTomogramBinning"),
        ).with_columns(
            pl.DataFrame(
                out_size,
                schema=["rlnTomoSizeX", "rlnTomoSizeY", "rlnTomoSizeZ"],
                orient="row",
            ),
        )
        as_star({"global": df_out}).write(tomo_star_path)


def _run_impl(
    edf_path: Path,
    fileinlist_path: Path,
    tomo_name: str,
    output_tomo_path: Path,
    tomo_size: tuple[int, int, int],
    outbin: int,
    do_float16: bool,
    filter_cutoff: float,
    filter_falloff: float,
    gpu_id_imod: int | None,
):
    _dir_fileinlists = fileinlist_path.parent
    temp_stack_path = _dir_fileinlists.joinpath(f"{tomo_name}_stack.mrc")
    temp_rec_path = _dir_fileinlists.joinpath(f"{tomo_name}.mrc")
    temp_ali_path = _dir_fileinlists.joinpath(f"{tomo_name}_ali.mrc")

    tlt_path = edf_path.with_suffix(".tlt")
    xtilt_path = edf_path.with_suffix(".xtilt")

    # NOTE: newstack may not work properly if the file list is directly used
    # for alignment.
    result = _run_create_stack(
        fileinlist_path,
        output_path=temp_stack_path,
    )
    fileinlist_path.unlink()
    if result.returncode != 0:
        return False
    yield
    _run_final_alignment(
        temp_stack_path,
        edf_path.with_suffix(".xf"),
        size=tomo_size[:2],
        output_path=temp_ali_path,
        outbin=outbin,
    )
    temp_stack_path.unlink()
    if result.returncode != 0:
        return False
    yield
    _run_tilt(
        temp_ali_path,
        output_path=temp_rec_path,
        tlt_path=tlt_path,
        size=tomo_size[:2],
        thickness=tomo_size[2],
        xtilt_path=xtilt_path,
        do_float16=do_float16,
        filter_cutoff=filter_cutoff,
        filter_falloff=filter_falloff,
        bin_of_input=outbin,
        gpu_id_imod=gpu_id_imod,
    )
    temp_ali_path.unlink()
    if result.returncode != 0:
        return False
    _run_rotx(
        temp_rec_path,
        output_path=output_tomo_path,
    )
    temp_rec_path.unlink()
    return True


def _fileinlist_text(num_tilts: int, mic_names: list[str]):
    fileinlist_lines = [str(num_tilts)]
    for mic_name in mic_names:
        fileinlist_lines.append(mic_name)
        fileinlist_lines.append("0")
    return "\n".join(fileinlist_lines)


def _run_create_stack(
    fileinlist: Path,
    output_path: Path,
):
    args = [
        "newstack",
        "-fileinlist",
        str(fileinlist),
        "-output",
        str(output_path),
    ]
    return subprocess.run(args, stdout=subprocess.PIPE)


def _run_final_alignment(
    input_path: Path,
    xf_path: Path,
    size: tuple[int, int],
    output_path: Path,
    outbin: int = 1,
):
    args = [
        "newstack",
        "-input",
        str(input_path),
        "-output",
        str(output_path),
        "-xform",
        str(xf_path),
        "-size",
        f"{size[0]},{size[1]}",
    ]
    out = subprocess.run(args, stdout=subprocess.PIPE)
    if out.returncode != 0:
        return out
    if outbin > 1:
        args = [
            "binvol",
            "-input",
            str(output_path),
            "-output",
            str(output_path),
            "-x",
            str(outbin),
            "-y",
            str(outbin),
            "-z",
            "1",
        ]
        out = subprocess.run(args, stdout=subprocess.PIPE)
        if output_path.with_suffix(".mrc~").exists():
            output_path.with_suffix(".mrc~").unlink()
    return out


def _run_tilt(
    input_path: Path,
    output_path: Path,
    tlt_path: Path,
    xtilt_path: Path,
    size: tuple[int, int],
    thickness: int = 600,
    do_float16: bool = True,
    filter_cutoff: float = 0.35,
    filter_falloff: float = 0.035,
    bin_of_input: int = 1,
    gpu_id_imod: int | None = 0,  # 0 -> optimal, 1 -> first GPU, etc.
):
    args = [
        "tilt",
        "-input",
        str(input_path),
        "-output",
        str(output_path),
        "-TILTFILE",
        str(tlt_path),
        "-XTILTFILE",
        str(xtilt_path),
        "-THICKNESS",
        str(thickness),
        "-RADIAL",
        f"{filter_cutoff:.3f},{filter_falloff:.3f}",
        "-FalloffIsTrueSigma",
        "1",
        "-XAXISTILT",
        "0",
        "-MODE",
        "12" if do_float16 else "2",
        "-FULLIMAGE",
        f"{size[0]},{size[1]}",
        "-IMAGEBINNED",
        str(bin_of_input),
    ]
    if gpu_id_imod is not None:
        args += ["-UseGPU", str(gpu_id_imod)]
    return subprocess.run(args, stdout=subprocess.PIPE)


def _run_rotx(
    input_path: Path,
    output_path: Path,
):
    args = [
        "clip",
        "rotx",
        str(input_path),
        str(output_path),
    ]
    return subprocess.run(args, stdout=subprocess.PIPE)
