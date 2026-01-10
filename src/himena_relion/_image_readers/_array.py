"""An array-like object that supports lazy loading and slicing."""

from __future__ import annotations
from abc import ABC, abstractmethod
from functools import lru_cache, reduce
from io import BytesIO
from pathlib import Path
from typing import Callable, TYPE_CHECKING, Iterator
import numpy as np
from numpy.typing import NDArray
import mrcfile
import tifffile

if TYPE_CHECKING:
    Arr = NDArray[np.number]
    PathLike = str | Path


def _no_filter(x: Arr, i: int) -> Arr:
    return x


class ArrayFilteredView:
    def __init__(
        self,
        view: ArrayViewBase,
        post_filter: Callable[[Arr, int], Arr] | None = None,
    ):
        self._view = view
        if post_filter is None:
            self._post_filter = _no_filter
        else:
            self._post_filter = post_filter

    def get_slice(self, index: int) -> Arr:
        """Get a slice of the filtered array."""
        arr = self._view.get_slice(index)
        return self._post_filter(arr, index)

    def get_scale(self) -> float:
        """Get the scale of the array."""
        return self._view.get_scale()

    def num_slices(self) -> int:
        """Get the number of slices in the array."""
        return self._view.num_slices()

    def with_filter(self, post_filter: Callable[[Arr, int], Arr]) -> ArrayFilteredView:
        return ArrayFilteredView(self._view, post_filter)

    @classmethod
    def from_array(cls, array: Arr) -> ArrayFilteredView:
        return cls(ArrayDirectView(array))

    @classmethod
    def from_mrc(cls, path: PathLike) -> ArrayFilteredView:
        return cls(ArrayFromMrc(path))

    @classmethod
    def from_mrc_splits(cls, paths: list[PathLike]) -> ArrayFilteredView:
        return cls(ArrayFromMrcSplits(paths))

    @classmethod
    def from_mrcs(cls, paths: list[PathLike]) -> ArrayFilteredView:
        return cls(ArrayFromMrcs(paths))

    @classmethod
    def from_tif(cls, path: PathLike, split_into: int = 4) -> ArrayFilteredView:
        """Read a tiff movie"""
        return cls(ArrayFromTif(path, split_into))

    @classmethod
    def from_tif_movies(cls, paths: list[PathLike]) -> ArrayFilteredView:
        """Read tiff movies as a tilt series"""
        return cls(ArrayFromTifMovies(paths))


class ArrayViewBase(ABC):
    @abstractmethod
    def get_slice(self, index: int) -> Arr:
        """Get a slice of the array."""

    @abstractmethod
    def num_slices(self) -> int:
        """Get the number of slices in the array."""

    @abstractmethod
    def get_scale(self) -> float:
        """Get the scale of the array."""


class ArrayDirectView(ArrayViewBase):
    """Array view that directly wraps a numpy array."""

    def __init__(self, array: Arr):
        self._array = array
        if self._array.ndim == 2:
            self._array = self._array[np.newaxis, :, :]

    def get_slice(self, index: int) -> Arr:
        return self._array[index]

    def num_slices(self) -> int:
        return self._array.shape[0]

    def get_scale(self) -> float:
        return 1.0


class ArrayFromMrc(ArrayViewBase):
    """Array view that reads slices from a 3D MRC file."""

    def __init__(self, path):
        self._path = Path(path)

    def get_slice(self, index: int) -> Arr:
        with mrcfile.mmap(self._path, mode="r") as mrc:
            mmap_data = mrc.data
            if mmap_data.ndim == 2:
                data = np.asarray(mmap_data)
            else:
                data = np.asarray(mrc.data[index])
        return data

    def get_scale(self) -> float:
        with mrcfile.open(self._path, header_only=True, mode="r") as mrc:
            return mrc.voxel_size.x

    @lru_cache(maxsize=1)
    def num_slices(self) -> int:
        with mrcfile.open(self._path, mode="r") as mrc:
            return int(mrc.header.nz)


class ArrayFromMrcSplits(ArrayViewBase):
    def __init__(self, paths):
        self._paths = [Path(p) for p in paths]

    def get_slice(self, index: int) -> Arr:
        return reduce(lambda a, b: a + b, self._iter_images(index))

    def get_scale(self) -> float:
        with mrcfile.open(self._paths[0], header_only=True, mode="r") as mrc:
            return mrc.voxel_size.x

    @lru_cache(maxsize=1)
    def num_slices(self) -> int:
        with mrcfile.open(self._paths[0], mode="r") as mrc:
            return mrc.header.nz

    def _iter_images(self, index: int) -> Iterator[Arr]:
        for path in self._paths:
            try:
                with mrcfile.mmap(path, mode="r") as mrc:
                    out = np.asarray(mrc.data[index])
            except Exception:
                pass
            else:
                yield out


class ArrayFromFiles(ArrayViewBase):
    """Array view that reads slices from a list of image files."""

    def __init__(self, paths):
        self._paths = [Path(p) for p in paths]

    def num_slices(self) -> int:
        return len(self._paths)


class ArrayFromMrcs(ArrayFromFiles):
    """Array view that reads slices from a list of MRC files."""

    def get_scale(self) -> float:
        if len(self._paths) == 0:
            return 1.0
        with mrcfile.open(self._paths[0], header_only=True, mode="r") as mrc:
            return mrc.voxel_size.x

    def get_slice(self, index: int) -> Arr:
        path = self._paths[index]
        sl = slice(None)
        if path.name.endswith(":mrc"):  # Ctf
            path = path.with_name(path.name[:-4])
            sl = 0  # CTF files are (1, N, M) arrays
        with mrcfile.mmap(path, mode="r") as mrc:
            data = np.asarray(mrc.data)
        return data[sl]


class ArrayFromTif(ArrayViewBase):
    """Array view that reads a single slice from a TIFF file."""

    def __init__(self, path, split_into):
        self._path = Path(path)
        self._split_into = split_into
        self._arr: NDArray[np.number] | None = None

    def get_slice(self, index: int) -> Arr:
        self._make_cache()
        return self._arr[index]

    def get_scale(self) -> float:
        # with tifffile.TiffFile(self._path) as tif:
        return 1.0  # TODO: read from TIFF metadata

    def num_slices(self) -> int:
        self._make_cache()
        return self._arr.shape[0]

    def _make_cache(self):
        if self._arr is None:
            # Opening the file and decompressing all frames takes time, so this process
            # may interfere with other operations such as the subsequent motion
            # correction. Here, we first copy the file content into memory, then read
            # from the in-memory bytes buffer to avoid holding the file lock for too
            # long.
            with open(self._path, "rb") as f:
                bytes_io = BytesIO(f.read())

            with tifffile.TiffFile(bytes_io) as tif:
                arr = tif.asarray()
            if arr.ndim == 2:
                arr = arr[np.newaxis, :, :]
            if self._split_into > 1:
                start = 0
                num_slice = int(np.ceil(arr.shape[0] / self._split_into))
                groups = []
                while start < arr.shape[0]:
                    end = min(start + num_slice, arr.shape[0])
                    group = arr[start:end].mean(axis=0, dtype=np.float32)
                    groups.append(group)
                    start = end
                arr = np.stack(groups, axis=0)
            self._arr = arr


class ArrayFromTifMovies(ArrayFromFiles):
    def get_scale(self) -> float:
        if len(self._paths) == 0:
            return 1.0
        return 1.0  # TODO: read from TIFF metadata?

    def get_slice(self, index: int) -> Arr:
        path = self._paths[index]
        with tifffile.TiffFile(path) as tif:
            arr = tif.asarray()
        if arr.ndim == 3:
            arr = arr.mean(axis=0)
        return arr
