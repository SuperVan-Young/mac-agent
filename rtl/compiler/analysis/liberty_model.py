"""Placeholder interface for cell delay and transition models."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class LibertyModel:
    search_paths: list[str] = field(default_factory=list)

    def delay(self, cell: str, arc: tuple[str, str], input_slew: float, load: float) -> float:
        """Return an estimated arc delay.

        This will absorb the existing NLDM-based timing logic from `rtl/generate.py`.
        """

        _ = (cell, arc, input_slew, load)
        raise NotImplementedError("liberty delay lookup is not implemented yet")
