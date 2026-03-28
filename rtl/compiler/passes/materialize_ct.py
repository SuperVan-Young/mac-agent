"""Materialize a compressor tree from the partial-product graph."""

from __future__ import annotations

from dataclasses import dataclass

from ..context import CompilerContext
from ..dialects.arith import ArithModule
from ..patterns import MaterializeDaddaTreePattern


@dataclass
class MaterializeCompressorTreePass:
    name: str = "materialize_compressor_tree"

    def run(self, module: ArithModule, context: CompilerContext) -> ArithModule:
        pattern = MaterializeDaddaTreePattern()
        module.mac.compressor_tree.comp_graph = pattern.apply(
            module.mac.ppg.output_columns,
            module.mac.compressor_tree.reduction_type,
        )
        context.metadata["ct_materialized"] = True
        return module
