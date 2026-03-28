"""Compressor-tree dialect operations.

This dialect models the internal reduction subgraph of a compressor tree without
forcing the outer arithmetic IR to flatten.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ...compat import XdslRequirement


@dataclass(frozen=True, kw_only=True)
class CompNode:
    op_name: str
    node_id: str
    column: int
    stage: int
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    attributes: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, kw_only=True)
class FullAdderOp(CompNode):
    op_name: str = "comp.fa"


@dataclass(frozen=True, kw_only=True)
class HalfAdderOp(CompNode):
    op_name: str = "comp.ha"


@dataclass(frozen=True, kw_only=True)
class Compressor42Op(CompNode):
    op_name: str = "comp.compressor_4_2"


@dataclass
class ColumnBundleOp:
    name: str = "comp.column_bundle"
    columns: dict[int, list[str]] = field(default_factory=dict)


@dataclass
class CompStage:
    stage: int
    nodes: list[CompNode] = field(default_factory=list)


@dataclass
class CompGraph:
    reduction_type: str
    column_bundle: ColumnBundleOp
    stages: list[CompStage] = field(default_factory=list)
    attributes: dict[str, object] = field(default_factory=dict)


def require_xdsl() -> None:
    XdslRequirement("comp dialect definitions").ensure()
