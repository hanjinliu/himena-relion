"""Files of the Select Tomograms job, shared by the job and its widget.

- `tomogram_selection.star`: rlnTomoName and rlnSelected (1 or 0) of all the input
  tomograms. It is written by the job widget when the user saves the selection, and the
  job waits for it to be saved.
- `tomograms_selected.star`: the input tomograms.star with the selected tomograms only.
  This is the output node of the job.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import polars as pl
from starfile_rs import LoopDataBlock, as_star, read_star
from starfile_rs.core import StarDict

from himena_relion._job_dir import JobDirectory
from himena_relion._utils import write_text_atomic

SELECTION_STAR = "tomogram_selection.star"
OUTPUT_STAR = "tomograms_selected.star"
_STAR_HEADER = "\n# version 50001\n"
_TOMO_NAME = "rlnTomoName"
_SELECTED = "rlnSelected"
# columns of the tomogram files, in the order of priority to be shown
_TOMOGRAM_COLUMNS = [
    ("rlnTomoReconstructedTomogramDenoised", "denoised tomogram"),
    ("rlnTomoReconstructedTomogram", "full tomogram"),
]
_HALF_COLUMNS = (
    "rlnTomoReconstructedTomogramHalf1",
    "rlnTomoReconstructedTomogramHalf2",
)


@dataclass
class TomogramEntry:
    """A tomogram to be selected."""

    name: str
    paths: list[Path]
    """Paths of the tomogram (or the two halves) relative to the RELION project."""
    kind: str


@dataclass
class TomogramSet:
    """The tomograms.star file to select tomograms from."""

    star: StarDict
    block_name: str
    table: pl.DataFrame
    """The table of tomograms. All the columns are strings to keep the values."""

    @classmethod
    def from_file(cls, path: str | Path) -> TomogramSet:
        star = read_star(path)
        for name, block in star.items():
            if (loop := block.try_loop()) is not None and _TOMO_NAME in loop.columns:
                table = loop.to_polars(string_columns=loop.columns)
                return cls(star=star, block_name=name, table=table)
        raise ValueError(f"Table with {_TOMO_NAME} not found in {path}.")

    @property
    def tomo_names(self) -> list[str]:
        return self.table[_TOMO_NAME].to_list()

    def entries(self) -> list[TomogramEntry]:
        """List the tomograms, with the files to be shown."""
        columns = self.table.columns
        for col, kind in _TOMOGRAM_COLUMNS:
            if col in columns:
                return [
                    TomogramEntry(name, [Path(p)], kind)
                    for name, p in zip(self.tomo_names, self.table[col])
                ]
        if all(col in columns for col in _HALF_COLUMNS):
            return [
                TomogramEntry(name, [Path(p1), Path(p2)], "half tomograms")
                for name, p1, p2 in self.table.select(_TOMO_NAME, *_HALF_COLUMNS).rows()
            ]
        return [
            TomogramEntry(name, [], "not reconstructed") for name in self.tomo_names
        ]

    def write_subset(self, path: str | Path, names: Iterable[str]) -> int:
        """Write the tomograms of the given names to `path` and return the number."""
        table = self.table.filter(pl.col(_TOMO_NAME).is_in(list(names)))
        star_out = StarDict.from_blocks(list(self.star.values()))
        star_out.with_block(LoopDataBlock.from_polars(self.block_name, table))
        write_text_atomic(path, _STAR_HEADER + star_out.to_string())
        return table.height


def save_selection(job_dir: JobDirectory, selection: dict[str, bool]) -> Path:
    """Save the selection of all the tomograms, which the running job waits for."""
    df = pl.DataFrame(
        {
            _TOMO_NAME: list(selection.keys()),
            _SELECTED: [int(sel) for sel in selection.values()],
        },
        schema={_TOMO_NAME: pl.String, _SELECTED: pl.Int64},
    )
    path = job_dir.path / SELECTION_STAR
    write_text_atomic(path, _STAR_HEADER + as_star({"": df}).to_string())
    return path


def read_selection(job_dir: JobDirectory) -> dict[str, bool] | None:
    """Read the saved selection as {tomo_name: selected}, or None if not available."""
    path = job_dir.path / SELECTION_STAR
    if not path.exists():
        return None
    try:
        df = read_star(path).first().trust_loop().to_polars(string_columns=[_TOMO_NAME])
        return {
            str(name): int(sel) > 0 for name, sel in zip(df[_TOMO_NAME], df[_SELECTED])
        }
    except Exception:
        return None


def last_selection(job_dir: JobDirectory, names: list[str]) -> list[bool]:
    """Selection of the last run: the tomograms written to the output.

    The saved selection is used if the output is not available. It may not be the
    output, if it was saved again after the job read it.
    """
    if (output_path := job_dir.path / OUTPUT_STAR).exists():
        try:
            selected = set(TomogramSet.from_file(output_path).tomo_names)
        except Exception:
            pass
        else:
            return [name in selected for name in names]
    if (selection := read_selection(job_dir)) is not None:
        return [selection.get(name, False) for name in names]
    return [False] * len(names)
