"""CLI-facing helpers for the compiler package."""

from __future__ import annotations

from .lowering.verilog import LoweringResult
from .pipeline import lower_demo_compressor_tree


def lower_demo_compressor_tree_cli() -> LoweringResult:
    """Run the minimal compiler demo from arith.compressor_tree to asap7."""

    return lower_demo_compressor_tree()
