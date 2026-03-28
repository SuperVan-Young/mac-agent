"""Compiler package for xDSL-based MAC generation experiments."""

from .pipeline import build_context, build_demo_compressor_tree_module, lower_demo_compressor_tree, render_module
from .pipeline import PipelineResult

__all__ = [
    "PipelineResult",
    "build_context",
    "build_demo_compressor_tree_module",
    "lower_demo_compressor_tree",
    "render_module",
]
