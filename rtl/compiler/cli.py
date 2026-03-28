"""CLI-facing helpers for the compiler package."""

from __future__ import annotations

from .context import CompilerConfig, CompilerContext
from .lowering.verilog import LoweringResult, lower_to_structural_verilog
from .lowering.xdsl_verilog import XdslLoweringResult
from .pipeline import build_default_pipeline


def run_compiler(config: CompilerConfig) -> CompilerContext:
    """Run the default compiler pipeline and return its populated context."""

    context = CompilerContext(config=config)
    pipeline = build_default_pipeline()
    context.metadata["module"] = pipeline.run(module=None, context=context)
    return context


def compile_to_verilog(config: CompilerConfig) -> LoweringResult:
    """Run the stub compiler pipeline and lower the result to structural Verilog."""

    context = run_compiler(config)
    return lower_to_structural_verilog(context.metadata["module"])


def lower_demo_xdsl_compressor_tree() -> XdslLoweringResult:
    """Run the minimal xDSL lowering demo from arith.compressor_tree to asap7."""

    from .xdsl_pipeline import lower_demo_compressor_tree_to_asap7

    return lower_demo_compressor_tree_to_asap7()
