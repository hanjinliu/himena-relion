from __future__ import annotations
from typing import Sequence
from enum import Enum
from pathlib import Path
from dataclasses import dataclass, field
import starfile
import pandas as pd


class RelionDefaultPipeline(Sequence["RelionJobInfo"]):
    def __init__(self, nodes: list[RelionJobInfo]):
        self._nodes = nodes

    def __len__(self) -> int:
        return len(self._nodes)

    def __getitem__(self, index: int) -> RelionJobInfo:
        return self._nodes[index]

    def __iter__(self):
        return iter(self._nodes)

    @classmethod
    def from_pipeline_star(cls, star_path: Path) -> RelionDefaultPipeline:
        dfs = starfile.read(star_path, always_dict=True)

        # |rlnPipeLineProcessName|rlnPipeLineProcessAlias|rlnPipeLineProcessTypeLabel|rlnPipeLineProcessStatusLabel
        # |       Import/job001/ |                  None |         relion.importtomo | Succeeded
        processes: pd.DataFrame = dfs["pipeline_processes"]

        # |        rlnPipeLineEdgeFromNode | rlnPipeLineEdgeProcess |
        # | Import/job001/tilt_series.star | MotionCorr/job004/     |
        mappers: pd.DataFrame = dfs["pipeline_input_edges"]

        nodes: dict[Path, RelionJobInfo] = {}
        for path, alias, type_label, status in zip(
            processes["rlnPipeLineProcessName"],
            processes["rlnPipeLineProcessAlias"],
            processes["rlnPipeLineProcessTypeLabel"],
            processes["rlnPipeLineProcessStatusLabel"],
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
            mappers["rlnPipeLineEdgeFromNode"],
            mappers["rlnPipeLineEdgeProcess"],
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
    path: Path
    type_label: str
    alias: str | None
    parents: list[RelionOutputFile]
    status: NodeStatus = NodeStatus.SUCCEEDED


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
        df_all = starfile.read(path, always_dict=True)
        assert isinstance(df_all, dict)
        df_general = df_all.get("pipeline_general")
        df_processes = df_all.get("pipeline_processes")
        assert isinstance(df_processes, pd.DataFrame)
        process_name = df_processes["rlnPipeLineProcessName"].iloc[0]
        process_alias = df_processes["rlnPipeLineProcessAlias"].iloc[0]
        process_type_label = df_processes["rlnPipeLineProcessTypeLabel"].iloc[0]
        process_status_label = df_processes["rlnPipeLineProcessStatusLabel"].iloc[0]

        # construct type map
        df_type_map = df_all.get("pipeline_nodes")
        assert isinstance(df_type_map, pd.DataFrame)
        _type_map = {}
        for _, row in df_type_map.iterrows():
            _type_map[row["rlnPipeLineNodeName"]] = row["rlnPipeLineNodeTypeLabel"]

        df_in = df_all.get("pipeline_input_edges")
        if isinstance(df_in, pd.DataFrame):
            inputs = [
                RelionJobPipelineNode.from_file_path(
                    input_path_rel,
                    _type_map.get(input_path_rel, None),
                )
                for input_path_rel in df_in["rlnPipeLineEdgeFromNode"]
            ]
        else:
            inputs = []

        df_out = df_all.get("pipeline_output_edges")
        if isinstance(df_out, pd.DataFrame):
            outputs = [
                RelionJobPipelineNode.from_file_path(
                    output_path_rel,
                    _type_map.get(output_path_rel, None),
                )
                for output_path_rel in df_out["rlnPipeLineEdgeToNode"]
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
        df_all = {
            "pipeline_general": self.general,
            "pipeline_processes": pd.DataFrame(
                {
                    "rlnPipeLineProcessName": [self.process_name],
                    "rlnPipeLineProcessAlias": [self.process_alias or ""],
                    "rlnPipeLineProcessTypeLabel": [self.process_type_label],
                    "rlnPipeLineProcessStatusLabel": [self.status_label or ""],
                }
            ),
            "pipeline_nodes": pd.DataFrame(
                {
                    "rlnPipeLineNodeName": [node.path.as_posix() for node in nodes],
                    "rlnPipeLineNodeTypeLabel": [
                        node.type_label or "" for node in nodes
                    ],
                    "rlnPipeLineNodeTypeLabelDepth": [1 for _ in nodes],
                }
            ),
            "pipeline_input_edges": pd.DataFrame(
                {
                    "rlnPipeLineEdgeFromNode": [
                        node.path.as_posix() for node in self.inputs
                    ],
                    "rlnPipeLineEdgeProcess": [self.process_name for _ in self.inputs],
                }
            ),
            "pipeline_output_edges": pd.DataFrame(
                {
                    "rlnPipeLineEdgeProcess": [self.process_name for _ in self.outputs],
                    "rlnPipeLineEdgeToNode": [
                        node.path.as_posix() for node in self.outputs
                    ],
                }
            ),
        }
        starfile.write(df_all, path)
        return


@dataclass
class RelionOptimisationSet:
    tomogram_star: Path
    particles_star: Path

    @classmethod
    def from_file(cls, path: str | Path) -> RelionOptimisationSet:
        df = starfile.read(path)
        if isinstance(df, pd.DataFrame):
            tomo_star_path: str = df["rlnTomoTomogramsFile"][0]
            particles_path: str = df["rlnTomoParticlesFile"][0]
        else:
            tomo_star_path: str = df["rlnTomoTomogramsFile"]
            particles_path: str = df["rlnTomoParticlesFile"]

        return cls(Path(tomo_star_path), Path(particles_path))
