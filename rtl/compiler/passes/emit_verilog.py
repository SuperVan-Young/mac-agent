"""Emit structural Verilog from the current root module."""

from __future__ import annotations

from xdsl.dialects.builtin import ModuleOp

from ..dialects.asap7 import FullAdderOp, HalfAdderOp


def emit_verilog(module: ModuleOp, top_name: str = "mac16x16p32") -> str:
    wires: set[str] = set()
    referenced_signals: set[str] = set()
    instances: list[str] = []
    for op in module.ops:
        if isinstance(op, FullAdderOp):
            wires.update((op.sum_out.data, op.carry_out.data))
            referenced_signals.update((op.lhs.data, op.rhs.data, op.cin.data))
            instances.append(
                f"  FAx1_ASAP7_75t_R {op.instance_name.data}({op.sum_out.data}, {op.carry_out.data}, {op.lhs.data}, {op.rhs.data}, {op.cin.data});"
            )
        elif isinstance(op, HalfAdderOp):
            wires.update((op.sum_out.data, op.carry_out.data))
            referenced_signals.update((op.lhs.data, op.rhs.data))
            instances.append(
                f"  HAxp5_ASAP7_75t_R {op.instance_name.data}({op.sum_out.data}, {op.carry_out.data}, {op.lhs.data}, {op.rhs.data});"
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
