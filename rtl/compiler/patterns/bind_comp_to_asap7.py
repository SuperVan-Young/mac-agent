"""Patterns that map compressor nodes to ASAP7-backed subgraphs."""

from __future__ import annotations

from dataclasses import dataclass

from ..dialects.asap7 import Asap7CellOp, Asap7Graph
from ..dialects.comp import CompGraph, Compressor42Op, FullAdderOp, HalfAdderOp


@dataclass
class BindCompToAsap7Pattern:
    """Bind compressor nodes to simple ASAP7 cell groups without flattening ownership."""

    xor2_cell: str = "XOR2x2_ASAP7_75t_R"
    and2_cell: str = "AND2x2_ASAP7_75t_R"

    def apply(self, graph: CompGraph, owner: str) -> Asap7Graph:
        asap7_graph = Asap7Graph(owner=owner)
        for stage in graph.stages:
            for node in stage.nodes:
                if isinstance(node, (FullAdderOp, HalfAdderOp, Compressor42Op)):
                    asap7_graph.cells.extend(self._map_node(node, owner))
        return asap7_graph

    def _map_node(self, node: FullAdderOp | HalfAdderOp | Compressor42Op, owner: str) -> list[Asap7CellOp]:
        lhs = node.inputs[0]
        rhs = node.inputs[1] if len(node.inputs) > 1 else node.inputs[0]
        sum_out = node.outputs[0]
        carry_out = node.outputs[1] if len(node.outputs) > 1 else f"{node.node_id}_carry"
        base = f"{node.node_id}_asap7"
        return [
            Asap7CellOp(
                op_name="asap7.xor2",
                instance_name=f"{base}_sum",
                cell_name=self.xor2_cell,
                outputs=(sum_out,),
                inputs=(lhs, rhs),
                owner=owner,
            ),
            Asap7CellOp(
                op_name="asap7.and2",
                instance_name=f"{base}_carry",
                cell_name=self.and2_cell,
                outputs=(carry_out,),
                inputs=(lhs, rhs),
                owner=owner,
            ),
        ]
