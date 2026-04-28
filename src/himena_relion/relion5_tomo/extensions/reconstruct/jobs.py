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

    # def provide_widget(self, job_dir) -> QInspectViewer:
    #     return QInspectViewer(job_dir)

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
        gpu_id_imod = (
            0 if gpu_id_to_use == "" else int(gpu_id_to_use) + 1
        )  # IMOD's GPU IDs are 1-based, and 0 means "auto"
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
        for ith, tomo_name, ts_path, edf_path in zip(
            range(num_tomo),
            tsgroup.tomo_name,
            tsgroup.tomo_tilt_series_star_file,
            tsgroup.etomo_directive_file,
        ):
            prog = f"({ith + 1}/{num_tomo})"
            self.console.log(f"{prog} Start reconstruction of {tomo_name!r}.")
            ts = TSModel.validate_file(ts_path)
            mic_names = ts.dataframe.sort("rlnTomoNominalStageTiltAngle")[
                "rlnMicrographName"
            ]
            if len(mic_names) == 0:
                continue
            fileinlist_lines = [str(tsgroup.dataframe.height)]
            for mic_name in mic_names:
                fileinlist_lines.append(str(self.output_job_dir.resolve_path(mic_name)))
                fileinlist_lines.append("0")
            fileinlist_path = _dir_fileinlists.joinpath(f"{tomo_name}.txt")
            fileinlist_path.write_text("\n".join(fileinlist_lines))
            temp_stack_path = _dir_fileinlists.joinpath(f"{tomo_name}_stack.mrc")
            temp_rec_path = _dir_fileinlists.joinpath(f"{tomo_name}.mrc")
            temp_ali_path = _dir_fileinlists.joinpath(f"{tomo_name}_ali.mrc")

            imod_dir: Path = self.output_job_dir.resolve_path(edf_path).parent
            tlt_path = imod_dir / f"{imod_dir.name}.tlt"
            xtilt_path = imod_dir / f"{imod_dir.name}.xtilt"

            with mrcfile.open(mic_names[0], header_only=True) as mrc:
                if ts.need_rot90():
                    size = int(mrc.header.nx), int(mrc.header.ny)
                else:
                    size = int(mrc.header.ny), int(mrc.header.nx)

            out_size.append(size + (thickness,))
            # NOTE: newstack may not work properly if the file list is directly used
            # for alignment.
            result = _run_create_stack(
                fileinlist_path,
                output_path=temp_stack_path,
            )
            fileinlist_path.unlink()
            if result.returncode != 0:
                self.console.log(
                    f"Failed to create stack for {tomo_name!r}. Skipping this tomogram."
                )
                continue
            yield
            _run_final_alignment(
                temp_stack_path,
                imod_dir / f"{imod_dir.name}.xf",
                size=size,
                output_path=temp_ali_path,
                outbin=outbin,
            )
            temp_stack_path.unlink()
            if result.returncode != 0:
                self.console.log(
                    f"Failed to create aligned stack for {tomo_name!r}. Skipping this tomogram."
                )
                continue
            yield
            self.console.log(f"{prog} Aligned stack for {tomo_name!r} created.")
            _run_tilt(
                temp_ali_path,
                output_path=temp_rec_path,
                tlt_path=tlt_path,
                size=size,
                thickness=thickness,
                xtilt_path=xtilt_path,
                do_float16=do_float16,
                filter_cutoff=filter_cutoff,
                filter_falloff=filter_falloff,
                bin_of_input=outbin,
                gpu_id_imod=gpu_id_imod,
            )
            temp_ali_path.unlink()
            if result.returncode != 0:
                self.console.log(
                    f"Failed in back-projection for {tomo_name!r}. Skipping this tomogram."
                )
                continue
            _run_rotx(
                temp_rec_path,
                output_path=_dir_tomo / f"rec_{tomo_name}.mrc",
            )
            temp_rec_path.unlink()
            self.console.log(f"Finished backprojection for {tomo_name!r}.")
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


# class ReconstructTomoHalvesIMOD(RelionExternalJob):
#     ...


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
    subprocess.run(args, stdout=subprocess.PIPE)
    if outbin > 1:
        args = [
            "binvol",
            "-input",
            str(output_path),
            "-output",
            str(output_path),
            "-bin",
            str(outbin),
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
