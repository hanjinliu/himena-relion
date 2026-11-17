from __future__ import annotations
from pathlib import Path
from typing import Callable
import logging

from qtpy import QtCore
from himena_relion import _job_dir

_LOGGER = logging.getLogger(__name__)
RETRY_INTERVAL_MSEC = 1000
MAX_RETRY = 5


class QRetryTimer(QtCore.QTimer):
    """Timer to retry reading a file, such as when RELION has not finished writing it.

    A file event may come before the file is completely written. If reading the file
    failed, call `retry` to call `callback(job_dir)` again after the interval. Call
    `reset` before a new attempt (not a retry), or after reading succeeded.
    """

    def __init__(
        self,
        callback: Callable[[_job_dir.JobDirectory], object],
        parent: QtCore.QObject | None = None,
        interval_msec: int = RETRY_INTERVAL_MSEC,
        max_retry: int = MAX_RETRY,
    ):
        super().__init__(parent)
        self.setSingleShot(True)
        self.setInterval(interval_msec)
        self._callback = callback
        self._max_retry = max_retry
        self._num_retry = 0
        self._job_dir_to_retry: _job_dir.JobDirectory | None = None
        self.timeout.connect(self._on_timeout)

    @property
    def num_retry(self) -> int:
        """Number of retries scheduled since the last reset."""
        return self._num_retry

    @property
    def max_retry(self) -> int:
        return self._max_retry

    def reset(self):
        """Cancel the pending retry and reset the retry count."""
        self.stop()
        self._job_dir_to_retry = None
        self._num_retry = 0

    def retry(self, job_dir: _job_dir.JobDirectory, path: Path, error: Exception):
        """Retry after reading `path` failed with `error`.

        A warning is logged instead if the maximum number of retries is reached.
        """
        if self._num_retry < self._max_retry:
            self._num_retry += 1
            _LOGGER.debug(
                "Failed to read %s. Retry in %d ms (%d/%d).",
                path,
                self.interval(),
                self._num_retry,
                self._max_retry,
                exc_info=error,
            )
            self._job_dir_to_retry = job_dir
            self.start()
        else:
            _LOGGER.warning("Failed to read %s.", path, exc_info=error)

    def _on_timeout(self):
        if (job_dir := self._job_dir_to_retry) is not None:
            self._job_dir_to_retry = None
            self._callback(job_dir)
