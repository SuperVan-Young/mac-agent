"""ASAP7 cell-bound operations.

This dialect keeps the lowered standard-cell subgraph grouped under the original
arithmetic/compressor owner instead of flattening the whole compiler IR.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ...compat import XdslRequirement


@dataclass(frozen=True)
class Asap7CellOp:
    op_name: str
    instance_name: str
    cell_name: str
    outputs: tuple[str, ...]
    inputs: tuple[str, ...]
    owner: str
    attributes: dict[str, object] = field(default_factory=dict)


@dataclass
class Asap7Graph:
    owner: str
    cells: list[Asap7CellOp] = field(default_factory=list)
    attributes: dict[str, object] = field(default_factory=dict)


def require_xdsl() -> None:
    XdslRequirement("asap7 dialect definitions").ensure()
