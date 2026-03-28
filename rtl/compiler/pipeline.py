"""Compiler pipeline for arith -> logic -> asap7."""

from __future__ import annotations

from dataclasses import dataclass
from io import StringIO
from pathlib import Path

from xdsl.context import Context
from xdsl.dialects.builtin import Builtin, ModuleOp
from xdsl.dialects.func import Func
from xdsl.parser import Parser
from xdsl.printer import Printer

from .dialects.arith import ARITH_DIALECT
from .dialects.asap7 import ASAP7_DIALECT
from .dialects.logic import LOGIC_DIALECT
from .passes.annotate_func_port_criticality import AnnotateFuncPortCriticalityPass
from .passes.emit_verilog import emit_verilog
from .passes.lower_arith_to_logic import LowerArithToLogicPass
from .passes.lower_logic_to_asap7 import LowerLogicToAsap7Pass
from .passes.lower_multiplier_to_arith_parts import LowerMultiplierToArithPartsPass
from .passes.region_scoped_cell_sizing import RegionScopedCellSizingPass
from .passes.verify_post_arith_to_logic import PostArithToLogicVerificationPass
from .passes.verify_post_logic_to_physical import PostLogicToPhysicalVerificationPass

@dataclass(frozen=True)
class PipelineResult:
    ir_text: str
    verilog_text: str


PASS_REGISTRY = {
    "lower-multiplier-to-arith-parts": LowerMultiplierToArithPartsPass,
    "lower-arith-to-logic": LowerArithToLogicPass,
    "verify-post-arith-to-logic": PostArithToLogicVerificationPass,
    "lower-logic-to-asap7": LowerLogicToAsap7Pass,
    "annotate-func-port-criticality": AnnotateFuncPortCriticalityPass,
    "region-scoped-cell-sizing": RegionScopedCellSizingPass,
    "verify-post-logic-to-physical": PostLogicToPhysicalVerificationPass,
}


def build_context() -> Context:
    ctx = Context()
    ctx.load_dialect(Builtin)
    ctx.load_dialect(Func)
    ctx.load_dialect(ARITH_DIALECT)
    ctx.load_dialect(LOGIC_DIALECT)
    ctx.load_dialect(ASAP7_DIALECT)
    return ctx


def render_module(module: ModuleOp) -> str:
    stream = StringIO()
    printer = Printer(stream=stream, print_generic_format=True, print_properties_as_attributes=True)
    printer.print_op(module)
    return stream.getvalue()


def parse_module(text: str) -> ModuleOp:
    return Parser(build_context(), text, name="<input>").parse_module()


def run_pass_pipeline(module: ModuleOp, passes: tuple[str, ...]) -> ModuleOp:
    ctx = build_context()
    for pass_name in passes:
        pass_type = PASS_REGISTRY.get(pass_name)
        if pass_type is None:
            raise AssertionError(f"Unsupported pass {pass_name!r}")
        pass_type().apply(ctx, module)
    return module


def run_pass_pipeline_text(input_text: str, passes: tuple[str, ...]) -> str:
    module = parse_module(input_text)
    run_pass_pipeline(module, passes)
    return render_module(module)


def run_pass_pipeline_file(input_path: Path, output_path: Path, passes: tuple[str, ...]) -> None:
    output_path.write_text(
        run_pass_pipeline_text(input_path.read_text(encoding="utf-8"), passes),
        encoding="utf-8",
    )


def emit_verilog_text(input_text: str, passes: tuple[str, ...]) -> str:
    module = parse_module(input_text)
    run_pass_pipeline(module, passes)
    return emit_verilog(module)


def emit_verilog_file(input_path: Path, output_path: Path, passes: tuple[str, ...]) -> None:
    output_path.write_text(
        emit_verilog_text(input_path.read_text(encoding="utf-8"), passes),
        encoding="utf-8",
    )


def compile_text(input_text: str, passes: tuple[str, ...]) -> PipelineResult:
    module = parse_module(input_text)
    run_pass_pipeline(module, passes)
    return PipelineResult(
        ir_text=render_module(module),
        verilog_text=emit_verilog(module),
    )


def compile_file(input_path: Path, passes: tuple[str, ...]) -> PipelineResult:
    return compile_text(input_path.read_text(encoding="utf-8"), passes)
