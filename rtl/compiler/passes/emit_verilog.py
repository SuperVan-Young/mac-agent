"""Emit structural Verilog from the current root module."""

from __future__ import annotations

from xdsl.dialects.builtin import ArrayAttr, ModuleOp, StringAttr

from ..dialects.asap7 import FullAdderOp, HalfAdderOp
from ..signals import SignalDecl, decode_signal_decls


def _read_module_signature(module: ModuleOp) -> tuple[str, list[SignalDecl], list[SignalDecl]]:
    func_name_attr = module.attributes.get("func_name")
    input_ports_attr = module.attributes.get("input_ports")
    output_ports_attr = module.attributes.get("output_ports")
    if not isinstance(func_name_attr, StringAttr):
        raise AssertionError("builtin.module is missing string attribute 'func_name'")
    if not isinstance(input_ports_attr, ArrayAttr):
        raise AssertionError("builtin.module is missing array attribute 'input_ports'")
    if not isinstance(output_ports_attr, ArrayAttr):
        raise AssertionError("builtin.module is missing array attribute 'output_ports'")
    return (
        func_name_attr.data,
        decode_signal_decls(input_ports_attr),
        decode_signal_decls(output_ports_attr),
    )


def _emit_port_decl(signal: SignalDecl) -> str:
    width = "" if signal.width == 1 else f" [{signal.width - 1}:0]"
    return f"  {signal.kind}{width} {signal.name};"


def emit_verilog(module: ModuleOp) -> str:
    top_name, input_ports, output_ports = _read_module_signature(module)
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

    declared_ports = {signal.name for signal in input_ports + output_ports}
    for signal in referenced_signals:
        if "[" in signal:
            base = signal.split("[", 1)[0]
            if base not in declared_ports:
                wires.add(base)
        elif signal not in declared_ports:
            wires.add(signal)

    port_names = ", ".join(signal.name for signal in input_ports + output_ports)
    lines = [
        f"module {top_name}({port_names});",
    ]
    for signal in input_ports:
        lines.append(_emit_port_decl(signal))
    for signal in output_ports:
        lines.append(_emit_port_decl(signal))
    for wire_name in sorted(wires):
        lines.append(f"  wire {wire_name};")
    lines.append("")
    lines.extend(instances)
    lines.append("")
    if output_ports and input_ports:
        lines.append(f"  assign {output_ports[0].name} = {input_ports[-1].name};")
    lines.append("endmodule")
    lines.append("")
    return "\n".join(lines)
