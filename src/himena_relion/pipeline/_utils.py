from __future__ import annotations
from pathlib import Path
from cmap import Color

from himena.qt._qflowchart import BaseNodeItem
from himena_relion.consts import JOB_ID_MAP
from himena_relion._job_dir import ExternalJobDirectory, JobDirectory
from himena_relion._pipeline import RelionJobInfo, NodeStatus


def split_job_info(job: RelionJobInfo) -> tuple[str, str]:
    jobxxx = job.path.stem
    if jobxxx.startswith("job"):
        jobxxx = jobxxx[3:]
    if job.type_label == "relion.external":
        title = ExternalJobDirectory(job.path).job_title()
    else:
        title = JOB_ID_MAP.get(job.type_label, job.type_label)
    return jobxxx, title


class RelionJobNodeItem(BaseNodeItem):
    def __init__(self, job: RelionJobInfo):
        self._job = job

    def text(self) -> str:
        """Return the text of the node"""
        jobxxx = self._job.path.stem
        if jobxxx.startswith("job"):
            jobxxx = jobxxx[3:]
        if self._job.type_label == "relion.external":
            title = ExternalJobDirectory(self._job.path).job_title()
        else:
            title = JOB_ID_MAP.get(self._job.type_label, self._job.type_label)
        if alias := self._job.alias:
            return f"{jobxxx}: {alias}\n({title})"
        return f"{jobxxx}: {title}"

    def color(self):
        """Return the color of the node"""
        match self._job.status:
            case NodeStatus.SUCCEEDED:
                return Color("lightgreen")
            case NodeStatus.FAILED:
                return Color("lightcoral")
            case NodeStatus.ABORTED:
                return Color("lightyellow")
            case NodeStatus.RUNNING:
                return Color("lightblue")
            case NodeStatus.SCHEDULED:
                return Color("khaki")
            case _:
                return Color("lightgray")

    def tooltip(self) -> str:
        """Return the tooltip text for the node"""
        return f"Status: {self._job.status.value.capitalize()}"

    def id(self):
        """Return a unique identifier for the node"""
        return self._job.path

    def content(self) -> str:
        """Return the content of the node, default is the text"""
        return self.text()

    def job_dir(self, relion_dir: Path) -> JobDirectory | None:
        """Return the job directory"""
        path = relion_dir / self._job.path
        if path.exists():
            return JobDirectory(relion_dir / self._job.path)
