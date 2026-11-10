from __future__ import annotations
from pathlib import Path
import uuid
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
        try:
            title = ExternalJobDirectory(job.path).job_title()
        except Exception:
            title = "!" + job.type_label
    else:
        title = JOB_ID_MAP.get(job.type_label, "!" + job.type_label)
    return jobxxx, title


class RelionJobNodeItem(BaseNodeItem):
    def __init__(self, job: RelionJobInfo):
        self._job = job

    def text(self) -> str:
        """Return the text of the node"""
        jobxxx, title = split_job_info(self._job)
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
        return ""

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


class RelionJobGroupNodeItem(BaseNodeItem):
    """A node that represents a group of collapsed jobs."""

    def __init__(self, group_id: uuid.UUID, name: str, jobs: list[RelionJobInfo]):
        self._group_id = group_id
        self._name = name
        self._jobs = jobs

    @property
    def group_id(self) -> uuid.UUID:
        return self._group_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def jobs(self) -> list[RelionJobInfo]:
        """The jobs in this group that exist in the pipeline."""
        return self._jobs

    def text(self) -> str:
        num = len(self._jobs)
        summary = [f"{num} job" if num == 1 else f"{num} jobs"]
        for status in [NodeStatus.RUNNING, NodeStatus.SCHEDULED, NodeStatus.FAILED]:
            if count := sum(1 for job in self._jobs if job.status is status):
                summary.append(f"{count} {status.value}")
        return f"{self._name}\n({', '.join(summary)})"

    def color(self):
        return Color("#A8A8A8")

    def tooltip(self) -> str:
        lines = []
        for job in self._jobs:
            jobxxx, title = split_job_info(job)
            if job.alias:
                title = f"{job.alias} ({title})"
            lines.append(f"{jobxxx}: {title} [{job.status.value}]")
        return "\n".join(lines)

    def id(self) -> str:
        return f"group:{self._group_id}"

    def content(self) -> str:
        return f"{self.text()}\n{self.tooltip()}"
