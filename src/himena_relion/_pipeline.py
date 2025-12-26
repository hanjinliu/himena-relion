from __future__ import annotations
from typing import Iterator, Sequence
import logging
from enum import Enum
from pathlib import Path
from dataclasses import dataclass, field
from starfile_rs.schema import ValidationError
import pandas as pd
from himena_relion.consts import FileNames
from himena_relion.schemas import RelionPipelineModel

_LOGGER = logging.getLogger(__name__)


class RelionDefaultPipeline(Sequence["RelionJobInfo"]):
    def __init__(self, nodes: list[RelionJobInfo]):
        self._nodes = nodes

    def __len__(self) -> int:
        return len(self._nodes)

    def __getitem__(self, index: int) -> RelionJobInfo:
        return self._nodes[index]

    def __iter__(self):
        return iter(self._nodes)

    def iter_nodes(self) -> Iterator[RelionJobInfo]:
        yield from self._nodes

    @classmethod
    def from_pipeline_star(cls, star_path: Path) -> RelionDefaultPipeline:
        try:
            pipeline_star = RelionPipelineModel.validate_file(star_path)
        except ValidationError:
            return cls([])  # project without any jobs
        processes = pipeline_star.processes
        mappers = pipeline_star.input_edges
        # mappers = pipeline_star["pipeline_input_edges"].trust_loop().to_pandas()

        nodes: dict[Path, RelionJobInfo] = {}
        for path, alias, type_label, status in zip(
            processes.process_name,
            processes.alias,
            processes.type_label,
            processes.status_label,
            strict=True,
        ):
            if alias == "None":
                _alias = None
            elif isinstance(alias, str):
                _alias = alias.split("/")[-1]
            node = RelionJobInfo(
                path=Path(path),
                type_label=type_label,
                alias=_alias,
                parents=[],
                status=NodeStatus(status.lower()),
            )
            nodes[Path(path)] = node

        for from_node, to_node in zip(
            mappers.from_node,
            mappers.process,
            strict=True,
        ):
            from_path = Path(from_node)
            to_path = Path(to_node)
            if to_path in nodes and from_path.parent in nodes:
                job = RelionOutputFile(nodes[from_path.parent], from_path.name)
                nodes[to_path].parents.append(job)

        return cls(list(nodes.values()))


class NodeStatus(Enum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    ABORTED = "aborted"
    RUNNING = "running"
    SCHEDULED = "scheduled"


@dataclass
class RelionJobInfo:
    path: Path  # The relative path
    type_label: str
    alias: str | None
    parents: list[RelionOutputFile]
    status: NodeStatus = NodeStatus.SUCCEEDED

    def __hash__(self):
        return hash(self.path)

    def job_repr(self) -> str:
        """Return a string representation of the job."""
        # mainly for notification
        job_xxx = self.path.resolve().stem
        if job_xxx.startswith("job"):
            job_xxx = job_xxx[3:]
        if als := self.alias:
            return f"{job_xxx} ({als})"
        else:
            return f"{job_xxx}"


@dataclass
class RelionOutputFile:
    node: RelionJobInfo
    filename: str


### job_pipeline.star ###


@dataclass
class RelionJobPipelineNode:
    path_file: Path  # like xxx.star
    path_job: Path | None = None  # relative path like Class3D/job009
    type_label: str | None = None

    @property
    def path(self) -> Path:
        """Return the full path (maybe relative) of the node."""
        if self.path_job is None:
            return self.path_file
        return self.path_job / self.path_file

    @classmethod
    def from_file_path(
        cls,
        path: str,
        type_label: str | None = None,
    ) -> RelionJobPipelineNode:
        path_obj = Path(path)
        if (
            len(path_obj.parts) == 1
            or path_obj.is_absolute()
            or not path_obj.parent.name.startswith("job")
        ):
            # probably not inside a job directory
            return cls(path_obj, None, type_label)
        else:
            return cls(Path(path_obj.name), path_obj.parent, type_label)


@dataclass
class RelionPipeline:
    general: pd.DataFrame
    process_name: str
    process_type_label: str
    process_alias: str | None = None
    status_label: str | None = None
    inputs: list[RelionJobPipelineNode] = field(default_factory=list)
    outputs: list[RelionJobPipelineNode] = field(default_factory=list)

    def get_input_by_type(self, type_label: str) -> RelionJobPipelineNode | None:
        """Get input nodes by type label."""
        for node in self.inputs:
            if node.type_label.startswith(type_label):
                return node
        return None

    def append_output(self, path, type_label: str):
        """Append an output node."""
        node = RelionJobPipelineNode.from_file_path(path, type_label)
        self.outputs.append(node)

    @classmethod
    def from_star(cls, path: str | Path) -> RelionPipeline:
        pipeline = RelionPipelineModel.validate_file(path)
        df_general = pipeline.general.block.to_pandas()
        process_name = pipeline.processes.process_name.iloc[0]
        process_alias = pipeline.processes.alias.iloc[0]
        process_type_label = pipeline.processes.type_label.iloc[0]
        process_status_label = pipeline.processes.status_label.iloc[0]

        # construct type map
        _type_map = dict(zip(pipeline.nodes.name, pipeline.nodes.type_label))

        if pipeline.input_edges is not None:
            inputs = [
                RelionJobPipelineNode.from_file_path(
                    input_path_rel,
                    _type_map.get(input_path_rel, None),
                )
                for input_path_rel in pipeline.input_edges.from_node
            ]
        else:
            inputs = []

        if pipeline.output_edges is not None:
            outputs = [
                RelionJobPipelineNode.from_file_path(
                    output_path_rel,
                    _type_map.get(output_path_rel, None),
                )
                for output_path_rel in pipeline.output_edges.to_node
            ]
        else:
            outputs = []
        return cls(
            df_general,
            process_name,
            process_type_label,
            process_alias,
            process_status_label,
            inputs,
            outputs,
        )

    def write_star(self, path: str | Path):
        nodes = self.inputs + self.outputs
        # TODO: use schema to construct star file
        star = RelionPipelineModel.validate_dict(
            {
                "pipeline_general": self.general,
                "pipeline_processes": {
                    "rlnPipeLineProcessName": [self.process_name],
                    "rlnPipeLineProcessAlias": [self.process_alias or ""],
                    "rlnPipeLineProcessTypeLabel": [self.process_type_label],
                    "rlnPipeLineProcessStatusLabel": [self.status_label or ""],
                },
                "pipeline_nodes": {
                    "rlnPipeLineNodeName": [node.path.as_posix() for node in nodes],
                    "rlnPipeLineNodeTypeLabel": [
                        node.type_label or "" for node in nodes
                    ],
                    "rlnPipeLineNodeTypeLabelDepth": [1 for _ in nodes],
                },
                "pipeline_input_edges": {
                    "rlnPipeLineEdgeFromNode": [
                        node.path.as_posix() for node in self.inputs
                    ],
                    "rlnPipeLineEdgeProcess": [self.process_name for _ in self.inputs],
                },
                "pipeline_output_edges": {
                    "rlnPipeLineEdgeProcess": [self.process_name for _ in self.outputs],
                    "rlnPipeLineEdgeToNode": [
                        node.path.as_posix() for node in self.outputs
                    ],
                },
            },
        )
        return star.write(path)


def is_all_inputs_ready(d: str | Path) -> bool:
    """True if the job at directory `d` has all inputs ready."""
    if (ppath := Path(d) / "job_pipeline.star").exists():
        pipeline = RelionPipeline.from_star(ppath)
        # NOTE: Do NOT check the existence of output files. For example, Extract job
        # writes optimisation_set.star before the job actually finishes.
        not_ready = [
            input_.path_job
            for input_ in pipeline.inputs
            if not input_.path_job.joinpath(FileNames.EXIT_SUCCESS).exists()
        ]
        if not_ready:
            _LOGGER.info(
                "Inputs %s are not ready to start job %s.",
                [p.as_posix() for p in not_ready],
                d,
            )
        else:
            _LOGGER.info("All inputs are ready to start job %s.", d)
        return len(not_ready) == 0
    else:
        _LOGGER.warning(
            "Job pipeline star file %s not found.",
            ppath.as_posix(),
        )
    return False
