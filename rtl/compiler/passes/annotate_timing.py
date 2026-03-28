"""Annotate estimated timing information."""

from __future__ import annotations

from dataclasses import dataclass

from ..analysis.timing_graph import TimingGraph
from ..context import CompilerContext
from ..dialects.arith import ArithModule


@dataclass
class AnnotateTimingPass:
    name: str = "annotate_estimated_timing"

    def run(self, module: ArithModule, context: CompilerContext) -> ArithModule:
        graph = TimingGraph()
        asap7_graph = module.mac.compressor_tree.asap7_graph
        if asap7_graph is not None:
            for cell in asap7_graph.cells:
                for signal_in in cell.inputs:
                    for signal_out in cell.outputs:
                        graph.add_edge(signal_in, signal_out, delay=1.0)
        context.metadata["timing_graph"] = graph
        return module
