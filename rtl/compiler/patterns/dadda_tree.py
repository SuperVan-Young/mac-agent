"""Patterns that build a Dadda-style compressor-tree subgraph."""

from __future__ import annotations

from dataclasses import dataclass

from ..dialects.comp import ColumnBundleOp, CompGraph, CompStage, FullAdderOp, HalfAdderOp


@dataclass
class MaterializeDaddaTreePattern:
    """Create a coarse compressor subgraph while preserving the parent arith op."""

    def apply(self, columns: dict[int, list[str]], reduction_type: str) -> CompGraph:
        bundle = ColumnBundleOp(columns={column: list(bits) for column, bits in columns.items()})
        graph = CompGraph(reduction_type=reduction_type, column_bundle=bundle)
        for column, bits in sorted(columns.items()):
            nodes = []
            if len(bits) >= 3:
                nodes.append(
                    FullAdderOp(
                        node_id=f"ct_s0_c{column}_fa0",
                        column=column,
                        stage=0,
                        inputs=tuple(bits[:3]),
                        outputs=(f"ct_sum_c{column}_0", f"ct_carry_c{column + 1}_0"),
                    )
                )
            elif len(bits) == 2:
                nodes.append(
                    HalfAdderOp(
                        node_id=f"ct_s0_c{column}_ha0",
                        column=column,
                        stage=0,
                        inputs=tuple(bits[:2]),
                        outputs=(f"ct_sum_c{column}_0", f"ct_carry_c{column + 1}_0"),
                    )
                )
            if nodes:
                graph.stages.append(CompStage(stage=0, nodes=nodes))
        graph.attributes["shape"] = "dadda"
        return graph
