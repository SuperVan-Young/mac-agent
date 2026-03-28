"""Arithmetic dialect operations.

This dialect is the high-level IR layer. It keeps arithmetic structure explicit
and preserves major module boundaries such as:
- partial-product generation
- compressor tree
- carry-propagate adder
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ...compat import XdslRequirement


@dataclass
class PartialProductGeneratorOp:
    name: str = "arith.partial_product_generator"
    a_width: int = 16
    b_width: int = 16
    output_columns: dict[int, list[str]] = field(default_factory=dict)


@dataclass
class CompressorTreeOp:
    name: str = "arith.compressor_tree"
    reduction_type: str = "dadda"
    comp_graph: object | None = None
    asap7_graph: object | None = None
    attributes: dict[str, object] = field(default_factory=dict)


@dataclass
class AdderOp:
    name: str = "arith.adder"
    implementation: str = "cpa"
    attributes: dict[str, object] = field(default_factory=dict)


@dataclass
class MacOp:
    name: str
    ppg: PartialProductGeneratorOp
    compressor_tree: CompressorTreeOp
    adder: AdderOp
    attributes: dict[str, object] = field(default_factory=dict)


@dataclass
class ArithModule:
    top_name: str
    mac: MacOp
    attributes: dict[str, object] = field(default_factory=dict)


def require_xdsl() -> None:
    XdslRequirement("arith dialect definitions").ensure()
