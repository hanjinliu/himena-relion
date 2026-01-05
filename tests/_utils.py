from pathlib import Path
from typing import Iterable

def assert_param_name_match(a, b, allowed_diffs: Iterable[str] = ("other_args",)):
    a_set = set(a)
    b_set = set(b)
    allowed_diffs_set = set(allowed_diffs)
    only_in_a = a_set - b_set - allowed_diffs_set
    only_in_b = b_set - a_set - allowed_diffs_set
    assert len(only_in_a | only_in_b) == 0, (
        f"Parameter names do not match.\n"
        f"Only in first: {only_in_a}\n"
        f"Only in second: {only_in_b}"
    )

JOBS_DIR_SPA = Path(__file__).parent / "jobs_spa"
JOBS_DIR_TOMO = Path(__file__).parent / "jobs_tomo"
DEFAULT_PIPELINES_DIR = Path(__file__).parent / "default_pipelines"

def iter_spa_job_dirs():
    yield from _iter_job_dirs(JOBS_DIR_SPA)

def iter_tomo_job_dirs():
    yield from _iter_job_dirs(JOBS_DIR_TOMO)

def _iter_job_dirs(jobs_dir: Path) -> Iterable[str]:
    for file in jobs_dir.iterdir():
        if file.is_file():
            continue
        for subdir in file.iterdir():
            if subdir.is_dir() and subdir.name.startswith("job"):
                if (subdir / "job.star").exists():
                    yield subdir.relative_to(jobs_dir).as_posix()
