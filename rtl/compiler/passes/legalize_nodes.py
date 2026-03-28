"""Legalize abstract compressor nodes into allowed primitives."""

from __future__ import annotations

from dataclasses import dataclass

from ..context import CompilerContext
from ..dialects.arith import ArithModule


@dataclass
class LegalizeCompressorNodesPass:
    name: str = "legalize_compressor_nodes"

    def run(self, module: ArithModule, context: CompilerContext) -> ArithModule:
        comp_graph = module.mac.compressor_tree.comp_graph
        if comp_graph is not None:
            comp_graph.attributes["legalized_ops"] = ("comp.fa", "comp.ha", "comp.compressor_4_2")
        context.metadata["compressor_nodes_legalized"] = True
        return module
