"""CLI-facing helpers for the compiler package."""

from __future__ import annotations

from .pipeline import lower_demo_compressor_tree
from .pipeline import PipelineResult


def lower_demo_compressor_tree_cli() -> PipelineResult:
    """Run the minimal compiler demo from arith.compressor_tree to asap7."""

    return lower_demo_compressor_tree()
