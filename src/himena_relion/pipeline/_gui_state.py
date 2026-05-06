from __future__ import annotations
import datetime
from pathlib import Path
import uuid
from cmap import Color

from pydantic import BaseModel, Field, PrivateAttr

from himena_relion import __version__

_GUI_STATE_FILENAME = ".himena_gui_state.json"


class TagState(BaseModel):
    name: str
    color: str
    id: uuid.UUID = Field(default_factory=uuid.uuid4)


class JobState(BaseModel):
    tags: list[int] = Field(
        default_factory=lambda: [],
        description="The list of tag indices assigned to this job.",
    )


def _default_tag_choices() -> list[TagState]:
    return [
        TagState(name="Tag-1", color=Color("turquoise").hex),
        TagState(name="Tag-2", color=Color("plum").hex),
        TagState(name="Tag-3", color=Color("lightsalmon").hex),
        TagState(name="Tag-4", color=Color("khaki").hex),
        TagState(name="Tag-5", color=Color("lightsteelblue").hex),
    ]


class HimenaRelionGuiState(BaseModel):
    """The state of the Himena Relion GUI saved to JSON."""

    model_config = {"extra": "allow"}

    jobs: dict[str, JobState] = Field(
        default_factory=dict,
        description="A mapping from job IDs to their information.",
    )
    tag_choices: list[TagState] = Field(
        default_factory=_default_tag_choices,
        description="The list of available tags that can be assigned to jobs.",
    )
    version: str = Field(
        default=__version__,
        description="The version of the Himena Relion GUI.",
    )
    _write_time: datetime.datetime = PrivateAttr(
        default=datetime.datetime.now(),
        init=False,
    )

    @classmethod
    def try_from_project_directory(cls, d: str | Path) -> HimenaRelionGuiState | None:
        """Try to read the GUI state from a RELION project directory. Return None if the file does not exist."""
        path = Path(d) / _GUI_STATE_FILENAME
        if not path.exists():
            return None
        js = path.read_text()
        self = cls.model_validate_json(js)
        self._write_time = datetime.datetime.fromtimestamp(path.stat().st_mtime)
        return self

    @classmethod
    def from_project_directory(cls, d: str | Path) -> HimenaRelionGuiState:
        """Read the GUI state from a RELION project directory."""
        if (self := cls.try_from_project_directory(d)) is None:
            return cls()
        return self

    def dump_to_project_directory(self, project_directory: str | Path):
        """Dump the GUI state to a JSON file in the given project directory."""

        rln_dir = Path(project_directory)
        if not rln_dir.joinpath("default_pipeline.star").exists():
            raise FileNotFoundError(
                f"The directory {project_directory} does not appear to be a RELION "
                "project directory."
            )
        path = Path(project_directory) / _GUI_STATE_FILENAME
        js = self.model_dump_json(indent=2)
        path.write_text(js)
