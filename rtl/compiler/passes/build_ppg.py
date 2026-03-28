"""Build the initial partial-product graph."""

from __future__ import annotations

from dataclasses import dataclass

from ..context import CompilerContext
from ..dialects.arith import AdderOp, ArithModule, CompressorTreeOp, MacOp, PartialProductGeneratorOp


@dataclass
class BuildPartialProductGraphPass:
    name: str = "build_partial_product_graph"

    def run(self, module: object, context: CompilerContext) -> ArithModule:
        columns = {
            column: [
                f"pp_a{row}_b{column - row}"
                for row in range(context.config.a_width)
                if 0 <= column - row < context.config.b_width
            ]
            for column in range(context.config.a_width + context.config.b_width - 1)
        }
        ppg = PartialProductGeneratorOp(
            a_width=context.config.a_width,
            b_width=context.config.b_width,
            output_columns=columns,
        )
        mac = MacOp(
            name="arith.mac",
            ppg=ppg,
            compressor_tree=CompressorTreeOp(reduction_type=context.config.reduction_type),
            adder=AdderOp(),
        )
        return ArithModule(
            top_name=context.config.top_name,
            mac=mac,
            attributes={
                "acc_width": context.config.acc_width,
                "ppg_built": True,
            },
        )
