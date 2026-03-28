"""Minimal xDSL pipeline for arith.compressor_tree -> comp -> asap7."""

from __future__ import annotations

from io import StringIO

from xdsl.context import Context
from xdsl.dialects.builtin import Builtin, ModuleOp
from xdsl.printer import Printer

from .dialects.arith.xdsl import ARITH_DIALECT, CompressorTreeOp
from .dialects.asap7.xdsl import ASAP7_DIALECT
from .dialects.comp.xdsl import COMP_DIALECT
from .lowering.xdsl_verilog import XdslLoweringResult, lower_xdsl_asap7_module_to_verilog
from .passes.lower_arith_ct_to_comp import LowerArithCompressorTreeToCompPass
from .passes.lower_comp_to_asap7 import LowerCompToAsap7Pass


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


def build_xdsl_context() -> Context:
    ctx = Context()
    ctx.load_dialect(Builtin)
    ctx.load_dialect(ARITH_DIALECT)
    ctx.load_dialect(COMP_DIALECT)
    ctx.load_dialect(ASAP7_DIALECT)
    return ctx


def render_module_ir(module: ModuleOp) -> str:
    stream = StringIO()
    printer = Printer(stream=stream, print_generic_format=True, print_properties_as_attributes=True)
    printer.print_op(module)
    return stream.getvalue()


def lower_demo_compressor_tree_to_asap7(reduction_type: str = "dadda") -> XdslLoweringResult:
    ctx = build_xdsl_context()
    module = build_demo_compressor_tree_module(reduction_type=reduction_type)
    LowerArithCompressorTreeToCompPass().apply(ctx, module)
    LowerCompToAsap7Pass().apply(ctx, module)
    ir_text = render_module_ir(module)
    verilog_text = lower_xdsl_asap7_module_to_verilog(module)
    return XdslLoweringResult(ir_text=ir_text, verilog_text=verilog_text)
