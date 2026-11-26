import time
from typing import Annotated

from himena_relion._job_class import connect_jobs
from himena_relion._utils import file_stamp, is_file_updated
from himena_relion._widgets._magicgui import PathDrop
from himena_relion.consts import MenuId
from himena_relion.external import RelionExternalContinue, RelionExternalJob
import himena_relion.relion5_tomo._builtins as _tomo
from himena_relion.relion5_tomo.extensions.erase_gold import FindBeads3D
from himena_relion.relion5_tomo.extensions.inspect_particles import InspectParticles
from himena_relion.relion5_tomo.extensions.reconstruct import (
    ReconstructTomoIMOD,
    ReconstructHalfTomoIMOD,
)
from ._impl import (
    OUTPUT_STAR,
    SELECTION_STAR,
    TomogramSet,
    last_selection,
    read_selection,
)

_IN_TOMOGRAMS = Annotated[
    str,
    {
        "label": "Input tomograms",
        "widget_type": PathDrop,
        "type_label": ["TomogramGroupMetadata", "TomoOptimisationSet"],
        "allowed_extensions": [".star"],
        "tooltip": (
            "The tomograms.star file with the reconstructed tomograms, such as the "
            "output of a Reconstruct tomograms or Denoise tomograms job. Tomograms are "
            "selected in the job window while this job is running."
        ),
        "group": "I/O",
    },
]


class SelectTomograms(RelionExternalJob):
    """Select tomograms to keep, by checking them in the job window.

    While this job is running, the input tomograms are shown in the job window. Check
    the tomograms to keep and click "Save selection". The selected tomograms are saved
    as tomograms_selected.star.
    """

    _max_wait_time_sec = 24 * 3600  # 24 hours
    _poll_interval_sec = 1.0

    def output_nodes(self):
        return [(OUTPUT_STAR, "TomogramGroupMetadata.star")]

    @classmethod
    def import_path(cls):
        return f"himena_relion.relion5_tomo:{cls.__name__}"

    @classmethod
    def job_title(cls):
        return "Select Tomos"

    @classmethod
    def menu_id(cls):
        return MenuId.RELION_TOMO_RECON_JOB

    def provide_widget(self, job_dir):
        from .widgets import QSelectTomogramsViewer

        return QSelectTomogramsViewer(job_dir)

    def run(self, in_mics: _IN_TOMOGRAMS):
        yield from _select_tomograms(self, in_mics)


class SelectTomogramsContinue(RelionExternalContinue):
    """Select the tomograms again, starting from the last selection."""

    original_class = SelectTomograms

    @classmethod
    def import_path(cls):
        return f"himena_relion.relion5_tomo:{cls.__name__}"

    def run(self, in_mics: _IN_TOMOGRAMS):
        yield from _select_tomograms(self, in_mics, continued=True)


def _select_tomograms(job: RelionExternalJob, in_mics: str, continued: bool = False):
    """Wait for the user to save the selection, and write the selected tomograms."""
    job_dir = job.output_job_dir
    tomo_set = TomogramSet.from_file(job_dir.resolve_path(in_mics))
    names = tomo_set.tomo_names
    if len(names) == 0:
        raise ValueError(f"No tomograms found in {in_mics}.")
    job.console.log(f"{len(names)} tomograms found in {in_mics}.")

    # The selection saved before this run (by the last run, if continued) is not used.
    selection_path = job_dir.path / SELECTION_STAR
    stamp = file_stamp(selection_path)
    if continued:
        num_last = sum(last_selection(job_dir, names))
        job.console.log(f"Starting from the last selection of {num_last} tomograms.")
    job.console.log(
        "Waiting for the user to select tomograms. Check the tomograms to keep in the "
        "job window and click 'Save selection'."
    )
    time_0 = time.time()
    while not is_file_updated(selection_path, stamp):
        if time.time() - time_0 > SelectTomograms._max_wait_time_sec:
            job.console.log("Tomogram selection timed out.")
            raise TimeoutError("Tomogram selection timed out.")
        time.sleep(SelectTomograms._poll_interval_sec)
        yield

    if (selection := read_selection(job_dir)) is None:
        raise ValueError(f"Failed to read {SELECTION_STAR}.")
    if unknown := sorted(name for name, sel in selection.items() if name not in names):
        job.console.log(f"WARNING: Tomograms not in the input are ignored: {unknown}")
    selected = [name for name in names if selection.get(name, False)]
    if len(selected) == 0:
        raise ValueError("No tomograms selected. Please select one or more tomograms.")
    num_out = tomo_set.write_subset(job_dir.path / OUTPUT_STAR, selected)
    job.console.log(f"Saved {num_out} of {len(names)} tomograms to {OUTPUT_STAR}.")


# NOTE: ReconstructHalfTomogramJob is not listed, because it is the same job type as
# ReconstructTomogramJob and the job would be suggested twice.
for _job_cls in [
    _tomo.ReconstructTomogramJob,
    _tomo.ReconstructTomoByAreTomo2,
    _tomo.DenoisePredict,
    ReconstructTomoIMOD,
    ReconstructHalfTomoIMOD,
]:
    connect_jobs(
        _job_cls,
        SelectTomograms,
        node_mapping={"tomograms.star": "in_mics"},
    )

for _job_cls in [_tomo.PickJob, _tomo.DenoiseTrain, _tomo.DenoisePredict]:
    connect_jobs(
        SelectTomograms,
        _job_cls,
        node_mapping={OUTPUT_STAR: "in_tomoset"},
    )

for _job_cls in [FindBeads3D, InspectParticles]:
    connect_jobs(
        SelectTomograms,
        _job_cls,
        node_mapping={OUTPUT_STAR: "in_mics"},
    )

del _job_cls
