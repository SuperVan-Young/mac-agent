"""Import OpenSTA/OpenROAD timing reports for IR back-annotation."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class StaPathPoint:
    name: str
    cell: str | None = None
    arrival: float | None = None


@dataclass
class StaPath:
    points: list[StaPathPoint] = field(default_factory=list)


def parse_critical_path_report(path: Path) -> StaPath:
    """Parse a critical-path report.

    This is currently a placeholder so we can stabilize interfaces before
    depending on exact OpenSTA report formatting.
    """

    _ = path
    return StaPath()
