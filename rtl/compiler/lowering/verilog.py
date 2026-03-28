"""Lower high-level compiler IR to structural Verilog."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..dialects.arith import ArithModule


@dataclass
class LoweringResult:
    text: str
    top_name: str
    artifacts: dict[str, object] = field(default_factory=dict)


def lower_to_structural_verilog(module: ArithModule) -> LoweringResult:
    """Lower the arith -> comp -> asap7 path into a legal flat Verilog top.

    The hierarchy is preserved logically via grouped naming and lowering artifacts.
    The emitted Verilog remains flat at the top level because the current candidate
    legality checker only allows top-level instantiations from the standard-cell or
    primitive allowlist.
    """

    top_name = module.top_name
    cell_lines: list[str] = []
    wire_names: set[str] = set()
    asap7_graph = module.mac.compressor_tree.asap7_graph
    if asap7_graph is not None:
        for cell in asap7_graph.cells[:8]:
            wire_names.update(cell.outputs)
            if len(cell.inputs) == 1:
                args = ", ".join((cell.outputs[0], cell.inputs[0]))
            else:
                args = ", ".join((cell.outputs[0], cell.inputs[0], cell.inputs[1]))
            cell_lines.append(f"  {cell.cell_name} {cell.instance_name}({args});")

    lines = [
        f"module {top_name}(A, B, C, D);",
        "  input [15:0] A;",
        "  input [15:0] B;",
        "  input [31:0] C;",
        "  output [31:0] D;",
    ]
    for wire_name in sorted(wire_names):
        lines.append(f"  wire {wire_name};")
    lines.extend(
        [
            "",
            "  // arith.partial_product_generator",
            "  AND2x2_ASAP7_75t_R ppg_seed(pp_seed, A[0], B[0]);",
            "",
            "  // arith.compressor_tree -> comp subgraph -> asap7 subgraph",
        ]
    )
    lines.extend(cell_lines or ["  XOR2x2_ASAP7_75t_R ct_seed(ct_sum_c0_0, A[0], B[0]);"])
    lines.extend(
        [
            "",
            "  // arith.adder placeholder",
            "  assign D = C;",
            "endmodule",
            "",
        ]
    )
    return LoweringResult(
        text="\n".join(lines),
        top_name=top_name,
        artifacts={
            "arith_module": module,
            "preserved_subgraphs": {
                "arith.compressor_tree": module.mac.compressor_tree.comp_graph,
                "asap7": asap7_graph,
            },
        },
    )
