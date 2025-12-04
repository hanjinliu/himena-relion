from __future__ import annotations
from typing import Sequence
from enum import Enum
from pathlib import Path
from dataclasses import dataclass
import starfile
import pandas as pd


class RelionPipeline(Sequence["RelionJobInfo"]):
    def __init__(self, nodes: list[RelionJobInfo]):
        self._nodes = nodes

    def __len__(self) -> int:
        return len(self._nodes)

    def __getitem__(self, index: int) -> RelionJobInfo:
        return self._nodes[index]

    def __iter__(self):
        return iter(self._nodes)

    @classmethod
    def from_pipeline_star(cls, star_path: Path) -> RelionPipeline:
        dfs = starfile.read(star_path, always_dict=True)

        # |rlnPipeLineProcessName|rlnPipeLineProcessAlias|rlnPipeLineProcessTypeLabel|rlnPipeLineProcessStatusLabel
        # |       Import/job001/ |                  None |         relion.importtomo | Succeeded
        processes: pd.DataFrame = dfs["pipeline_processes"]

        # |        rlnPipeLineEdgeFromNode | rlnPipeLineEdgeProcess |
        # | Import/job001/tilt_series.star | MotionCorr/job004/     |
        mappers: pd.DataFrame = dfs["pipeline_input_edges"]

        nodes: dict[Path, RelionJobInfo] = {}
        for path, type_label, status in zip(
            processes["rlnPipeLineProcessName"],
            processes["rlnPipeLineProcessTypeLabel"],
            processes["rlnPipeLineProcessStatusLabel"],
            strict=True,
        ):
            node = RelionJobInfo(
                path=Path(path),
                type_label=type_label,
                parents=[],
                status=NodeStatus(NodeStatus(status.lower())),
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


@dataclass
class RelionJobInfo:
    path: Path
    type_label: str
    parents: list[RelionOutputFile]
    status: NodeStatus = NodeStatus.SUCCEEDED


@dataclass
class RelionOutputFile:
    node: RelionJobInfo
    filename: str
