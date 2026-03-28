"""Compiler package for xDSL-based MAC generation experiments."""

from .cli import compile_to_verilog
from .cli import lower_demo_xdsl_compressor_tree
from .context import CompilerConfig, CompilerContext
from .pipeline import PassManager, build_default_pipeline

__all__ = [
    "CompilerConfig",
    "CompilerContext",
    "PassManager",
    "build_default_pipeline",
    "compile_to_verilog",
    "lower_demo_xdsl_compressor_tree",
]
