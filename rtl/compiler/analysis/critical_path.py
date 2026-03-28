"""Critical-path reporting helpers."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CriticalPathPoint:
    name: str
    arrival: float


@dataclass
class CriticalPathReport:
    total_delay: float
    points: list[CriticalPathPoint] = field(default_factory=list)

    def to_text(self) -> str:
        lines = [f"total_delay={self.total_delay:.3f}"]
        for point in self.points:
            lines.append(f"{point.name}: {point.arrival:.3f}")
        return "\n".join(lines)
