"""ASAP7-specific cell metadata."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Asap7Cell:
    name: str
    category: str


CORE_CELLS = {
    "fa1": Asap7Cell(name="FAx1_ASAP7_75t_R", category="compressor"),
    "ha": Asap7Cell(name="HAxp5_ASAP7_75t_R", category="compressor"),
    "xor2": Asap7Cell(name="XOR2x2_ASAP7_75t_R", category="logic"),
    "and2": Asap7Cell(name="AND2x2_ASAP7_75t_R", category="logic"),
}
