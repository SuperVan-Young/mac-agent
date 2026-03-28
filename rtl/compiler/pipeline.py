"""Minimal pipeline for arith.compressor_tree -> comp -> asap7."""

from __future__ import annotations

from io import StringIO

from xdsl.context import Context
from xdsl.dialects.builtin import Builtin, ModuleOp
from xdsl.printer import Printer

from .dialects.arith import ARITH_DIALECT, CompressorTreeOp
from .dialects.asap7 import ASAP7_DIALECT
from .dialects.comp import COMP_DIALECT
from .lowering.verilog import LoweringResult, lower_module_to_verilog
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


def build_context() -> Context:
    ctx = Context()
    ctx.load_dialect(Builtin)
    ctx.load_dialect(ARITH_DIALECT)
    ctx.load_dialect(COMP_DIALECT)
    ctx.load_dialect(ASAP7_DIALECT)
    return ctx


def render_module(module: ModuleOp) -> str:
    stream = StringIO()
    printer = Printer(stream=stream, print_generic_format=True, print_properties_as_attributes=True)
    printer.print_op(module)
    return stream.getvalue()


def lower_demo_compressor_tree(reduction_type: str = "dadda") -> LoweringResult:
    ctx = build_context()
    module = build_demo_compressor_tree_module(reduction_type=reduction_type)
    LowerArithCompressorTreeToCompPass().apply(ctx, module)
    LowerCompToAsap7Pass().apply(ctx, module)
    return LoweringResult(
        ir_text=render_module(module),
        verilog_text=lower_module_to_verilog(module),
    )
