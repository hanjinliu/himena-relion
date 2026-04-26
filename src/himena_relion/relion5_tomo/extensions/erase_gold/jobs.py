from pathlib import Path
from typing import Annotated

import imodmodel
import mrcfile
import numpy as np
import polars as pl
from starfile_rs import as_star, read_star
from himena_relion import _job_dir
from himena_relion.external import RelionExternalJob
from himena_relion._job_class import connect_jobs
from himena_relion.relion5_tomo._builtins import (
    ReconstructTomogramJob,
    ReconstructHalfTomogramJob,
    ReconstructTomoByAreTomo2,
)
from himena_relion._annotated.io import IN_TILT
from himena_relion.relion5_tomo.extensions.erase_gold.widgets import (
    QFindBeads3DViewer,
    QEraseGoldViewer,
)
from himena_relion.relion5_tomo.extensions.erase_gold import _impl
from himena_relion.relion5_tomo._tomo_utils import project_fiducials
from himena_relion.consts import MenuId

TILT_ANGLE = "rlnTomoNominalStageTiltAngle"
TILT_STAR = "rlnTomoTiltSeriesStarFile"
ETOMO_FILE = "rlnEtomoDirectiveFile"
MIC_NAME = "rlnMicrographName"
MIC_ODD = "rlnMicrographNameOdd"
MIC_EVEN = "rlnMicrographNameEven"


class FindBeads3D(RelionExternalJob):
    """Run findbeads3d on tomograms to locate gold fiducials."""

    def output_nodes(self):
        return [("tomograms.star", "TomogramGroupMetadata.star")]

    @classmethod
    def import_path(cls):
        return f"himena_relion.relion5_tomo:{cls.__name__}"

    @classmethod
    def job_title(cls):
        return "Find Beads 3D"

    @classmethod
    def menu_id(cls):
        return MenuId.RELION_TILT_ALIGN_JOB

    def run(
        self,
        in_mics: IN_TILT,  # path
        gold_nm: Annotated[float, {"label": "Gold diameter (nm)"}] = 10.0,
        findbeads3d_exe: Annotated[
            str, {"label": "findbeads3d executable"}
        ] = "findbeads3d",
    ):
        out_job_dir = self.output_job_dir
        models_dir = out_job_dir.path.joinpath("models")
        models_dir.mkdir(exist_ok=True, parents=True)
        rln_dir = out_job_dir.relion_project_dir
        df_tomo = (
            read_star(out_job_dir.resolve_path(in_mics))
            .first()
            .trust_loop()
            .to_polars()
        )

        model_paths = []
        for row in df_tomo.iter_rows(named=True):
            info = _job_dir.TomogramInfo.from_dict(row)
            path_star = out_job_dir.resolve_path(info.tilt_series_star_file)
            tomo_path = info.reconstructed_tomogram[0]
            size_pix = gold_nm / info.tomo_pixel_size * 10
            tilt_star_df = read_star(path_star).first().trust_loop().to_polars()
            angrange = tilt_star_df[TILT_ANGLE].min(), tilt_star_df[TILT_ANGLE].max()
            model_path = models_dir / f"{info.tomo_name}.mod"
            model_paths.append(model_path.relative_to(rln_dir).as_posix())
            self.console.log(f"Running findbeads3d for tomogram {info.tomo_name}")
            _impl.findbeads3d_wrapped(
                findbeads3d_exe, tomo_path, model_path, size_pix, angrange
            )
            yield

        df_tomo = df_tomo.with_columns(
            pl.Series("TomoBeadModel", model_paths),
            pl.lit(gold_nm).alias("TomoBeadSize"),
        )
        output_node_path = out_job_dir.path / "tomograms.star"
        as_star({"global": df_tomo}).write(output_node_path)
        self.console.log(
            f"findbeads3d jobs finished successfully, output saved to {output_node_path}"
        )

    def provide_widget(self, job_dir) -> QFindBeads3DViewer:
        return QFindBeads3DViewer(job_dir)


class EraseGold(RelionExternalJob):
    """Replace golds in tilt series with noise."""

    def output_nodes(self):
        return [("tilt_series.star", "TomogramGroupMetadata.star")]

    @classmethod
    def import_path(cls):
        return f"himena_relion.relion5_tomo:{cls.__name__}"

    @classmethod
    def job_title(cls):
        return "Erase Gold"

    @classmethod
    def menu_id(cls):
        return MenuId.RELION_TILT_ALIGN_JOB

    def run(
        self,
        in_mics: IN_TILT,  # path
        seed: Annotated[int, {"label": "Random seed", "max": 99999999}] = 1427,
        mask_expand_factor: Annotated[float, {"label": "Mask expansion factor"}] = 1.2,
        process_halves: Annotated[bool, {"label": "Also process odd/even micrographs"}] = False,
    ):  # fmt: skip
        """Erase gold fiducials from tilt series using the output model files."""
        out_job_dir = self.output_job_dir
        in_mics = out_job_dir.resolve_path(in_mics)
        df_tomo = read_star(in_mics).first().trust_loop().to_polars()

        tilt_save_dir = out_job_dir.path / "tilt_series"
        tilt_save_dir.mkdir(exist_ok=True, parents=True)
        frame_save_dir = out_job_dir.path / "frames"
        frame_save_dir.mkdir(exist_ok=True, parents=True)
        rln_dir = out_job_dir.relion_project_dir

        output_node_path = out_job_dir.path.joinpath("tilt_series.star")
        for row in df_tomo.iter_rows(named=True):
            info = _job_dir.TomogramInfo.from_dict(row)
            model_path = rln_dir / str(row["TomoBeadModel"])
            edf_path = rln_dir / str(row[ETOMO_FILE])
            gold_nm = row["TomoBeadSize"]
            star_path = out_job_dir.resolve_path(info.tomo_tilt_series_star_file)
            tilt_star_df = read_star(star_path).first().trust_loop().to_polars()
            tomo_center = (np.array(info.tomo_shape, dtype=np.float32) - 1) / 2
            rng = np.random.default_rng(seed)
            tilt_center = _tilt_center(rln_dir, tilt_star_df)
            fid = imodmodel.read(model_path)[["z", "y", "x"]].to_numpy(np.float32)
            fid = fid * info.tomogram_binning
            deg = tilt_star_df[TILT_ANGLE].cast(pl.Float32).to_numpy()
            xf = _impl.xf_to_array(edf_path.with_suffix(".xf"))
            self.console.log(
                f"{fid.shape[0]} fiducials found for tomogram {info.tomo_name}"
            )
            fid_tr = project_fiducials(fid, tomo_center, deg, xf, tilt_center)
            yield
            if process_halves:
                col_list = [MIC_NAME, MIC_ODD, MIC_EVEN]
            else:
                col_list = [MIC_NAME]
            new_cols: list[pl.Expr] = []
            for col in col_list:
                if col not in tilt_star_df.columns:
                    self.console.log(
                        f"Column {col} not found in {info.tomo_name}, skipping."
                    )
                _to_update: list[str] = []
                mic_paths = [rln_dir / p for p in tilt_star_df[col]]
                for ith, mic_path in enumerate(mic_paths):
                    mic_path = Path(mic_path)
                    with mrcfile.open(mic_path, mode="r") as mrc:
                        img = mrc.data
                        voxel_size = mrc.voxel_size
                    z_matches = abs(fid_tr[:, 0] - ith) < 0.01
                    yield
                    img_erased = _impl.erase_gold(
                        img,
                        pos=fid_tr[z_matches, 1:],
                        rng=rng,
                        gold_px=gold_nm / voxel_size.x * 10 * mask_expand_factor,
                    )
                    yield
                    save_path = (
                        frame_save_dir.relative_to(rln_dir)
                        / f"{mic_path.stem}_erased{mic_path.suffix}"
                    )
                    _to_update.append(str(save_path))
                    with mrcfile.new(rln_dir / save_path, overwrite=True) as mrc_out:
                        mrc_out.set_data(img_erased)
                        mrc_out.voxel_size = voxel_size
                    yield
                new_cols.append(pl.Series(col, _to_update))

            tilt_star_df = tilt_star_df.with_columns(new_cols)
            star_save_path = tilt_save_dir / info.tomo_tilt_series_star_file.name
            as_star({info.tomo_name: tilt_star_df}).write(star_save_path)
            self.console.log(f"Erased tilt series starfile saved to {star_save_path}")
            yield

        new_columns = [
            tilt_save_dir.relative_to(rln_dir)
            .joinpath(f"{_job_dir.TomogramInfo.from_dict(row).tomo_name}.star")
            .as_posix()
            for row in df_tomo.iter_rows(named=True)
        ]
        df_tomo = df_tomo.with_columns(pl.Series(TILT_STAR, new_columns))
        as_star({"global": df_tomo}).write(output_node_path)
        self.console.log(
            f"EraseGold jobs finished successfully, output saved to {output_node_path}"
        )

    def provide_widget(self, job_dir):
        return QEraseGoldViewer(job_dir)

    @classmethod
    def init_widgets_for_run(cls, widgets):
        widgets["seed"].value = int(np.random.randint(0, 99999999))


def _tilt_center(rln_dir: Path, tilt_star_df: pl.DataFrame) -> np.ndarray:
    mic_paths = [rln_dir / p for p in tilt_star_df[MIC_NAME]]
    with mrcfile.open(mic_paths[0], header_only=True) as mrc:
        tilt_shape = (mrc.header.ny, mrc.header.nx)
    tilt_center = (np.array(tilt_shape, dtype=np.float32) - 1) / 2
    return tilt_center


connect_jobs(
    ReconstructTomogramJob,
    FindBeads3D,
    node_mapping={"tomograms.star": "in_mics"},
)

connect_jobs(
    FindBeads3D,
    EraseGold,
    node_mapping={"tomograms.star": "in_mics"},
)
for job_cls in [
    ReconstructTomogramJob,
    ReconstructHalfTomogramJob,
    ReconstructTomoByAreTomo2,
]:
    connect_jobs(
        EraseGold,
        job_cls,
        node_mapping={"tilt_series.star": "in_tiltseries"},
    )
