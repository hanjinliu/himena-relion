from pathlib import Path
import subprocess

import imodmodel
import mrcfile
import pandas as pd
import numpy as np
from numpy.typing import NDArray
import starfile
from himena_relion import _job, _utils
from himena_relion.external import RelionExternalJob
from .widgets import QFindBeads3DViewer, QEraseGoldViewer


def _xf_to_array(xf: str | Path) -> NDArray[np.floating]:
    with open(xf) as f:
        arr_str = [line.split() for line in f]
    return np.array(arr_str, dtype=np.float32)


def project_fiducials(
    fid: NDArray[np.floating],
    tomo_center: NDArray[np.floating],
    deg: NDArray[np.floating],
    xf: NDArray[np.floating],
    tilt_center: NDArray[np.floating],
) -> NDArray[np.floating]:
    fid_center = fid - tomo_center
    out = []
    for i, d in enumerate(deg):
        a11, a12, a21, a22, tx, ty = xf[i]
        mat_al = np.linalg.inv(np.array([[a22, a21], [a12, a11]]))
        for zyx in fid_center:
            zyx0 = _utils.make_tilt_projection_mat(d) @ zyx + tomo_center
            zyx0[1:] = mat_al @ (zyx0[1:] - [ty, tx] - tomo_center[1:]) + tilt_center
            zyx0[0] = i
            out.append(zyx0)
    return np.stack(out, axis=0)


def _findbeads3d_wrapped(
    exe: str,
    tomo_path: str | Path,
    out_path: str | Path,
    size_pix: float,
    angle_range: tuple[float, float] = (-60.0, 60.0),
):
    # rec_TS_01_half1.mrc out.mod -angle "-60.0,60.0" -si 12
    a0, a1 = angle_range
    stdout_path = Path(out_path).with_suffix(".out")
    stderr_path = Path(out_path).with_suffix(".err")
    with open(stdout_path, "w") as stdout_file, open(stderr_path, "w") as stderr_file:
        out = subprocess.run(
            [
                exe,
                str(tomo_path),
                str(out_path),
                "-angle",
                f"{a0},{a1}",
                "-si",
                str(size_pix),
            ],
            stdout=stdout_file,
            stderr=stderr_file,
        )
    if out.returncode != 0:
        raise RuntimeError(f"findbeads3d failed with return code {out.returncode}")


def _erase_gold(
    img: NDArray[np.floating],  # (H, W)
    pos: NDArray[np.floating],  # (N, 2)
    rng: np.random.Generator,
    gold_px: float = 10.0,
):
    # NOTE: float16 sometimes causes overflow in mean/std calculation
    img = img.astype(np.float32, copy=True)
    mask = np.zeros_like(img, dtype=bool)
    gold_px_int = int(np.ceil(gold_px))
    yy, xx = np.indices((gold_px_int, gold_px_int))
    yy = yy - gold_px / 2
    xx = xx - gold_px / 2
    rr: NDArray[np.floating] = np.sqrt(yy**2 + xx**2)
    circle_mask = rr <= (gold_px / 2)
    for yc, xc in pos:
        y0 = int(yc - gold_px / 2)
        x0 = int(xc - gold_px / 2)
        y_start = max(0, y0)
        x_start = max(0, x0)
        y_end = min(mask.shape[0], y0 + gold_px_int)
        x_end = min(mask.shape[1], x0 + gold_px_int)
        if x_end <= x_start or y_end <= y_start:
            continue

        mask_y_start = y_start - y0
        mask_x_start = x_start - x0
        mask_y_end = mask_y_start + (y_end - y_start)
        mask_x_end = mask_x_start + (x_end - x_start)
        mask_cropped = circle_mask[mask_y_start:mask_y_end, mask_x_start:mask_x_end]
        ref = img[y_start:y_end, x_start:x_end][~mask_cropped]
        if ref.size == 0:
            continue  # should never happen, but just in case
        mean = np.mean(ref)
        std = np.std(ref, mean=mean)
        img[y_start:y_end, x_start:x_end][mask_cropped] = rng.normal(
            mean, std, size=mask_cropped.sum()
        )

    return img.astype(np.float16)


TILT_ANGLE = "rlnTomoNominalStageTiltAngle"
TILT_STAR = "rlnTomoTiltSeriesStarFile"
ETOMO_FILE = "rlnEtomoDirectiveFile"
MIC_NAME = "rlnMicrographName"
MIC_ODD = "rlnMicrographNameOdd"
MIC_EVEN = "rlnMicrographNameEven"


class FindBeads3D(RelionExternalJob):
    def output_nodes(self):
        return [("tomograms.star", "TomogramGroupMetadata.star")]

    @classmethod
    def import_path(cls):
        return ".".join(cls.__module__.split(".")[:-1]) + f":{cls.__name__}"

    def run(
        self,
        in_mics: str,  # path
        gold_nm: float = 10.0,
        findbeads3d_exe: str = "findbeads3d",
    ):
        df_tomo = starfile.read(in_mics)
        assert isinstance(df_tomo, pd.DataFrame)
        out_job_dir = self.output_job_dir
        models_dir = out_job_dir.path.joinpath("models")
        models_dir.mkdir(exist_ok=True, parents=True)

        model_paths = []
        for _, row in df_tomo.iterrows():
            info = _job.TomogramInfo.from_series(row)
            path_star = info.tilt_series_star_file
            tomo_path = info.reconstructed_tomogram[0]
            size_pix = gold_nm / info.tomo_pixel_size * 10
            tilt_star_df = starfile.read(path_star)
            angrange = tilt_star_df[TILT_ANGLE].min(), tilt_star_df[TILT_ANGLE].max()
            model_path = models_dir / f"{info.tomo_name}.mod"
            model_paths.append(model_path.relative_to(out_job_dir.relion_project_dir))
            self.console.log(f"Running findbeads3d for tomogram {info.tomo_name}")
            _findbeads3d_wrapped(
                findbeads3d_exe, tomo_path, model_path, size_pix, angrange
            )
            yield

        df_tomo["TomoBeadModel"] = model_paths
        df_tomo["TomoBeadSize"] = gold_nm
        output_node_path = out_job_dir.path / "tomograms.star"
        starfile.write(df_tomo, output_node_path)
        self.console.log(
            f"findbeads3d jobs finished successfully, output saved to {output_node_path}"
        )

    def provide_widget(self, job_dir) -> QFindBeads3DViewer:
        return QFindBeads3DViewer(job_dir)


class EraseGold(RelionExternalJob):
    def output_nodes(self):
        return [("tilt_series.star", "MicrographGroupMetadata.star")]

    @classmethod
    def import_path(cls):
        return ".".join(cls.__module__.split(".")[:-1]) + f":{cls.__name__}"

    def run(
        self,
        in_mics: str,  # path
        seed: int = 1427,
        mask_expand_factor: float = 1.2,
        process_halves: bool = False,
    ):
        """Erase gold fiducials from tilt series using the output model files."""
        df_tomo = starfile.read(in_mics)
        assert isinstance(df_tomo, pd.DataFrame)
        out_job_dir = self.output_job_dir

        tilt_save_dir = out_job_dir.path / "tilt_series"
        tilt_save_dir.mkdir(exist_ok=True, parents=True)
        frame_save_dir = out_job_dir.path / "frames"
        frame_save_dir.mkdir(exist_ok=True, parents=True)
        rln_dir = out_job_dir.relion_project_dir

        output_node_path = out_job_dir.path.joinpath("tilt_series.star")
        for _, row in df_tomo.iterrows():
            info = _job.TomogramInfo.from_series(row)
            model_path = rln_dir / str(row["TomoBeadModel"])
            edf_path = rln_dir / str(row[ETOMO_FILE])
            gold_nm = row["TomoBeadSize"]
            tilt_star_df = starfile.read(info.tomo_tilt_series_star_file)
            assert isinstance(tilt_star_df, pd.DataFrame)
            tomo_center = (np.array(info.tomo_shape, dtype=np.float32) - 1) / 2
            rng = np.random.default_rng(seed)
            mic_paths = tilt_star_df[MIC_NAME]
            with mrcfile.open(mic_paths[0], header_only=True) as mrc:
                tilt_shape = (mrc.header.ny, mrc.header.nx)
            tilt_center = (np.array(tilt_shape, dtype=np.float32) - 1) / 2
            fid = imodmodel.read(model_path)[["z", "y", "x"]].to_numpy(np.float32)
            fid *= info.tomogram_binning
            deg = tilt_star_df[TILT_ANGLE].to_numpy(dtype=np.float32)
            xf = _xf_to_array(edf_path.with_suffix(".xf"))
            self.console.log(
                f"{fid.shape[0]} fiducials found for tomogram {info.tomo_name}"
            )
            fid_tr = project_fiducials(fid, tomo_center, deg, xf, tilt_center)
            yield
            if process_halves:
                col_list = [MIC_NAME, MIC_ODD, MIC_EVEN]
            else:
                col_list = [MIC_NAME]
            for col in col_list:
                if col not in tilt_star_df.columns:
                    self.console.log(
                        f"Column {col} not found in {info.tomo_name}, skipping."
                    )
                _to_update = []
                for ith, mic_path in enumerate(mic_paths):
                    mic_path = Path(mic_path)
                    with mrcfile.open(mic_path, mode="r") as mrc:
                        img = mrc.data
                        voxel_size = mrc.voxel_size
                    z_matches = abs(fid_tr[:, 0] - ith) < 0.01
                    yield
                    img_erased = _erase_gold(
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
                tilt_star_df[col] = _to_update

            star_save_path = tilt_save_dir / info.tomo_tilt_series_star_file.name
            starfile.write(tilt_star_df, star_save_path)
            self.console.log(f"Erased tilt series starfile saved to {star_save_path}")
            yield

        df_tomo[TILT_STAR] = [
            tilt_save_dir.relative_to(rln_dir)
            / f"{_job.TomogramInfo.from_series(row).tomo_name}.star"
            for _, row in df_tomo.iterrows()
        ]
        starfile.write(df_tomo, output_node_path)
        self.console.log(
            f"EraseGold jobs finished successfully, output saved to {output_node_path}"
        )

    def provide_widget(self, job_dir):
        return QEraseGoldViewer(job_dir)
