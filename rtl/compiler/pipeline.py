"""Minimal pipeline for arith.compressor_tree -> logic -> asap7."""

from __future__ import annotations

from dataclasses import dataclass
from io import StringIO

from xdsl.context import Context
from xdsl.dialects.builtin import Builtin, ModuleOp
from xdsl.printer import Printer

from .dialects.arith import ARITH_DIALECT, CompressorTreeOp
from .dialects.asap7 import ASAP7_DIALECT
from .dialects.logic import LOGIC_DIALECT
from .passes.emit_verilog import emit_verilog
from .passes.lower_arith_to_logic import LowerArithToLogicPass
from .passes.lower_logic_to_asap7 import LowerLogicToAsap7Pass

@dataclass(frozen=True)
class PipelineResult:
    ir_text: str
    verilog_text: str


def build_demo_compressor_tree_module(reduction_type: str = "dadda") -> ModuleOp:
    columns = {
        0: ["A[0]", "B[0]"],
        1: ["pp_0_1", "pp_1_0", "C[0]"],
        2: ["pp_0_2", "pp_1_1"],
    }
    return ModuleOp(
        [
            CompressorTreeOp(
                reduction_type=reduction_type,
                columns=columns,
            )
        ]
    )


def build_context() -> Context:
    ctx = Context()
    ctx.load_dialect(Builtin)
    ctx.load_dialect(ARITH_DIALECT)
    ctx.load_dialect(LOGIC_DIALECT)
    ctx.load_dialect(ASAP7_DIALECT)
    return ctx


def render_module(module: ModuleOp) -> str:
    stream = StringIO()
    printer = Printer(stream=stream, print_generic_format=True, print_properties_as_attributes=True)
    printer.print_op(module)
    return stream.getvalue()


def lower_demo_compressor_tree(reduction_type: str = "dadda") -> PipelineResult:
    ctx = build_context()
    module = build_demo_compressor_tree_module(reduction_type=reduction_type)
    LowerArithToLogicPass().apply(ctx, module)
    LowerLogicToAsap7Pass().apply(ctx, module)
    return PipelineResult(
        ir_text=render_module(module),
        verilog_text=emit_verilog(module),
    )
