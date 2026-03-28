"""Bind eligible nodes to ASAP7 implementations."""

from __future__ import annotations

from dataclasses import dataclass

from ..context import CompilerContext
from ..dialects.arith import ArithModule
from ..patterns import BindCompToAsap7Pattern


@dataclass
class BindAsap7Pass:
    name: str = "bind_asap7_cells"

    def run(self, module: ArithModule, context: CompilerContext) -> ArithModule:
        comp_graph = module.mac.compressor_tree.comp_graph
        if comp_graph is not None:
            module.mac.compressor_tree.asap7_graph = BindCompToAsap7Pattern().apply(
                comp_graph,
                owner=module.mac.compressor_tree.name,
            )
        context.metadata["pdk_binding"] = context.config.pdk
        return module
