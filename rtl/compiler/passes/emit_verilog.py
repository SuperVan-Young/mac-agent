"""Emit structural Verilog from the current root module."""

from __future__ import annotations

import re

from xdsl.dialects.builtin import ArrayAttr, ModuleOp, StringAttr

from ..dialects.asap7 import And2Op, FullAdderOp, HalfAdderOp, Or2Op, Xor2Op
from ..signals import SignalDecl, decode_signal_decls


_BIT_SELECT_RE = re.compile(r"^(?P<base>[A-Za-z_]\w*)\[(?P<index>\d+)\]$")


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


def _is_literal(signal: str) -> bool:
    return "'" in signal or signal.isdigit()


def _collect_wire_base(signal: str, declared_ports: set[str], widths: dict[str, int]) -> None:
    if _is_literal(signal):
        return
    match = _BIT_SELECT_RE.match(signal)
    if match is not None:
        base = match.group("base")
        if base in declared_ports:
            return
        widths[base] = max(widths.get(base, 0), int(match.group("index")) + 1)
        return
    if signal in declared_ports:
        return
    widths[signal] = max(widths.get(signal, 0), 1)


def emit_verilog(module: ModuleOp) -> str:
    top_name, input_ports, output_ports = _read_module_signature(module)
    declared_ports = {signal.name for signal in input_ports + output_ports}
    wire_widths: dict[str, int] = {}
    instances: list[str] = []

    for op in module.ops:
        if isinstance(op, And2Op):
            _collect_wire_base(op.output.data, declared_ports, wire_widths)
            _collect_wire_base(op.lhs.data, declared_ports, wire_widths)
            _collect_wire_base(op.rhs.data, declared_ports, wire_widths)
            instances.append(
                f"  AND2x2_ASAP7_75t_R {op.instance_name.data}({op.output.data}, {op.lhs.data}, {op.rhs.data});"
            )
            continue
        if isinstance(op, Or2Op):
            _collect_wire_base(op.output.data, declared_ports, wire_widths)
            _collect_wire_base(op.lhs.data, declared_ports, wire_widths)
            _collect_wire_base(op.rhs.data, declared_ports, wire_widths)
            instances.append(
                f"  OR2x2_ASAP7_75t_R {op.instance_name.data}({op.output.data}, {op.lhs.data}, {op.rhs.data});"
            )
            continue
        if isinstance(op, Xor2Op):
            _collect_wire_base(op.output.data, declared_ports, wire_widths)
            _collect_wire_base(op.lhs.data, declared_ports, wire_widths)
            _collect_wire_base(op.rhs.data, declared_ports, wire_widths)
            instances.append(
                f"  XOR2x2_ASAP7_75t_R {op.instance_name.data}({op.output.data}, {op.lhs.data}, {op.rhs.data});"
            )
            continue
        if isinstance(op, FullAdderOp):
            _collect_wire_base(op.sum_out.data, declared_ports, wire_widths)
            _collect_wire_base(op.carry_out.data, declared_ports, wire_widths)
            _collect_wire_base(op.lhs.data, declared_ports, wire_widths)
            _collect_wire_base(op.rhs.data, declared_ports, wire_widths)
            _collect_wire_base(op.cin.data, declared_ports, wire_widths)
            instances.append(
                f"  FAx1_ASAP7_75t_R {op.instance_name.data}({op.carry_out.data}, {op.sum_out.data}, {op.lhs.data}, {op.rhs.data}, {op.cin.data});"
            )
            continue
        if isinstance(op, HalfAdderOp):
            _collect_wire_base(op.sum_out.data, declared_ports, wire_widths)
            _collect_wire_base(op.carry_out.data, declared_ports, wire_widths)
            _collect_wire_base(op.lhs.data, declared_ports, wire_widths)
            _collect_wire_base(op.rhs.data, declared_ports, wire_widths)
            instances.append(
                f"  HAxp5_ASAP7_75t_R {op.instance_name.data}({op.carry_out.data}, {op.sum_out.data}, {op.lhs.data}, {op.rhs.data});"
            )
            continue

    port_names = ", ".join(signal.name for signal in input_ports + output_ports)
    lines = [f"module {top_name}({port_names});"]
    for signal in input_ports:
        lines.append(_emit_port_decl(signal))
    for signal in output_ports:
        lines.append(_emit_port_decl(signal))
    for wire_name in sorted(wire_widths):
        width = wire_widths[wire_name]
        if width == 1:
            lines.append(f"  wire {wire_name};")
            continue
        lines.append(f"  wire [{width - 1}:0] {wire_name};")
    lines.append("")
    lines.extend(instances)
    lines.append("")
    lines.append("endmodule")
    lines.append("")
    return "\n".join(lines)
