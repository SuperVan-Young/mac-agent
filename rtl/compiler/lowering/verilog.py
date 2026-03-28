"""Lower an ASAP7-only module to structural Verilog."""

from __future__ import annotations

from dataclasses import dataclass

from xdsl.dialects.builtin import ModuleOp

from ..dialects.asap7 import And2Op, Xor2Op


@dataclass(frozen=True)
class LoweringResult:
    ir_text: str
    verilog_text: str


def lower_module_to_verilog(module: ModuleOp, top_name: str = "mac16x16p32") -> str:
    wires: set[str] = set()
    referenced_signals: set[str] = set()
    instances: list[str] = []
    for op in module.ops:
        if isinstance(op, Xor2Op):
            out = op.output.data
            lhs = op.lhs.data
            rhs = op.rhs.data
            wires.add(out)
            referenced_signals.update((lhs, rhs))
            instances.append(
                f"  XOR2x2_ASAP7_75t_R {op.instance_name.data}({out}, {lhs}, {rhs});"
            )
        elif isinstance(op, And2Op):
            out = op.output.data
            lhs = op.lhs.data
            rhs = op.rhs.data
            wires.add(out)
            referenced_signals.update((lhs, rhs))
            instances.append(
                f"  AND2x2_ASAP7_75t_R {op.instance_name.data}({out}, {lhs}, {rhs});"
            )

    declared_ports = {"A", "B", "C", "D"}
    for signal in referenced_signals:
        if "[" in signal:
            base = signal.split("[", 1)[0]
            if base not in declared_ports:
                wires.add(base)
        elif signal not in declared_ports:
            wires.add(signal)

    lines = [
        f"module {top_name}(A, B, C, D);",
        "  input [15:0] A;",
        "  input [15:0] B;",
        "  input [31:0] C;",
        "  output [31:0] D;",
    ]
    for wire_name in sorted(wires):
        lines.append(f"  wire {wire_name};")
    lines.append("")
    lines.extend(instances)
    lines.append("")
    lines.append("  assign D = C;")
    lines.append("endmodule")
    lines.append("")
    return "\n".join(lines)
