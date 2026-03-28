"""Compiler package for xDSL-based MAC generation experiments."""

from .pipeline import (
    PipelineResult,
    build_context,
    compile_file,
    compile_text,
    emit_verilog_file,
    emit_verilog_text,
    parse_module,
    render_module,
    run_pass_pipeline,
    run_pass_pipeline_file,
    run_pass_pipeline_text,
)

__all__ = [
    "PipelineResult",
    "build_context",
    "compile_file",
    "compile_text",
    "emit_verilog_file",
    "emit_verilog_text",
    "parse_module",
    "render_module",
    "run_pass_pipeline",
    "run_pass_pipeline_file",
    "run_pass_pipeline_text",
]
