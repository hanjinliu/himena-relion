from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Sequence

# Example output:
# RELION version: 5.0.0-commit-85db73
# Precision: BASE=double


@dataclass
class RelionVersion:
    major: int
    minor: int
    micro: int

    @classmethod
    def from_string(cls, version_str: str) -> RelionVersion:
        parts = version_str.strip().split(".")
        if len(parts) != 3:
            raise ValueError(f"Invalid version string: {version_str}")
        return cls(major=int(parts[0]), minor=int(parts[1]), micro=int(parts[2]))

    def __iter__(self):
        yield self.major
        yield self.minor
        yield self.micro

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.micro}"

    def __lt__(self, other: Sequence[int]) -> bool:
        return all(a < b for a, b in zip(self, other))

    def __le__(self, other: Sequence[int]) -> bool:
        return all(a <= b for a, b in zip(self, other))

    def __gt__(self, other: Sequence[int]) -> bool:
        return all(a > b for a, b in zip(self, other))

    def __ge__(self, other: Sequence[int]) -> bool:
        return all(a >= b for a, b in zip(self, other))

    def __eq__(self, other: object) -> bool:
        return all(a == b for a, b in zip(self, other))


@dataclass
class RelionVersionInfo:
    version: RelionVersion
    commit: str


def relion_version() -> str:
    """Return the output of `relion --version`."""
    res = subprocess.run(["relion", "--version"], capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError("Failed to get RELION version info: " + res.stderr)
    return res.stdout.strip()


def relion_version_info() -> RelionVersionInfo:
    stdout = relion_version()
    lines = stdout.splitlines()
    if lines[0].startswith("RELION version: "):
        version_str, commit = lines[0][len("RELION version: ") :].split("-commit-")
        version = RelionVersion.from_string(version_str)
        return RelionVersionInfo(version=version, commit=commit.strip())
    raise RuntimeError("Unexpected RELION version output: " + stdout)
