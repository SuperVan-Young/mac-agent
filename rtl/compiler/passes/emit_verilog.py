"""Emit structural Verilog from the current root module."""

from __future__ import annotations

from collections.abc import Iterable
import re

from xdsl.dialects.builtin import ArrayAttr, ModuleOp, StringAttr
from xdsl.dialects.func import FuncOp, ReturnOp

from ..dialects.asap7 import And2Op, Ao21Op, FullAdderOp, HalfAdderOp, Or2Op, Xor2Op
from ..dialects.logic import ConstantOp, InputPortOp, InstanceOp, OutputPortOp
from ..ir import get_wire_width, require_wire_name
from ..signals import SignalDecl, decode_signal_decls


_BIT_SELECT_RE = re.compile(r"^(?P<base>[A-Za-z_]\w*)\[(?P<index>\d+)\]$")
_LOGIC_INPUT_PORTS_ATTR = "logic.input_ports"
_LOGIC_OUTPUT_PORTS_ATTR = "logic.output_ports"


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


def _read_func_signature(func_op: FuncOp) -> tuple[str, list[SignalDecl], list[SignalDecl]]:
    input_ports_attr = func_op.attributes.get(_LOGIC_INPUT_PORTS_ATTR)
    output_ports_attr = func_op.attributes.get(_LOGIC_OUTPUT_PORTS_ATTR)
    if not isinstance(input_ports_attr, ArrayAttr):
        raise AssertionError(f"{func_op.sym_name.data} is missing {_LOGIC_INPUT_PORTS_ATTR!r}")
    if not isinstance(output_ports_attr, ArrayAttr):
        raise AssertionError(f"{func_op.sym_name.data} is missing {_LOGIC_OUTPUT_PORTS_ATTR!r}")
    return (
        func_op.sym_name.data,
        decode_signal_decls(input_ports_attr),
        decode_signal_decls(output_ports_attr),
    )


def _func_port_names(func_op: FuncOp) -> tuple[list[str], list[str]]:
    _, input_ports, output_ports = _read_func_signature(func_op)
    return ([signal.name for signal in input_ports], [signal.name for signal in output_ports])


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


def _collect_wire_value(value, declared_ports: set[str], widths: dict[str, int]) -> None:
    signal = require_wire_name(value)
    if _BIT_SELECT_RE.match(signal) is not None:
        _collect_wire_base(signal, declared_ports, widths)
        return
    if signal in declared_ports:
        return
    widths[signal] = max(widths.get(signal, 0), get_wire_width(value))


def _expand_signal_decl(signal: SignalDecl) -> list[str]:
    if signal.width == 1:
        return [signal.name]
    return [f"{signal.name}[{index}]" for index in range(signal.width)]


def _emit_instance(
    *,
    callee: str,
    instance_name: str,
    connections: list[tuple[str, str]],
) -> str:
    rendered = ", ".join(f".{port}({signal})" for port, signal in connections)
    return f"  {callee} {instance_name}({rendered});"


def _split_ref(ref: str) -> tuple[str, int | None]:
    match = _BIT_SELECT_RE.match(ref)
    if match is None:
        return ref, None
    return match.group("base"), int(match.group("index"))


def _compress_instance_connections(connections: list[tuple[str, str]]) -> list[tuple[str, str]]:
    grouped: list[tuple[str, list[tuple[str, str]]]] = []
    for port_ref, signal_ref in connections:
        port_base, _ = _split_ref(port_ref)
        if grouped and grouped[-1][0] == port_base:
            grouped[-1][1].append((port_ref, signal_ref))
            continue
        grouped.append((port_base, [(port_ref, signal_ref)]))

    compressed: list[tuple[str, str]] = []
    for port_base, items in grouped:
        if len(items) == 1:
            compressed.append(items[0])
            continue
        port_parts = [_split_ref(port_ref) for port_ref, _ in items]
        signal_parts = [_split_ref(signal_ref) for _, signal_ref in items]
        if any(index is None for _, index in port_parts):
            compressed.extend(items)
            continue
        if any(index is None for _, index in signal_parts):
            compressed.extend(items)
            continue
        signal_bases = {base for base, _ in signal_parts}
        if len(signal_bases) != 1:
            compressed.extend(items)
            continue
        if any(port_index != signal_index for (_, port_index), (_, signal_index) in zip(port_parts, signal_parts)):
            compressed.extend(items)
            continue
        sorted_port_indices = [index for _, index in port_parts]
        if sorted_port_indices != list(range(len(items))):
            compressed.extend(items)
            continue
        compressed.append((port_base, next(iter(signal_bases))))
    return compressed


def _expand_grouped_port_connections(
    port_names: list[str],
    signal_refs: list[str],
) -> list[tuple[str, str]]:
    connections: list[tuple[str, str]] = []
    used: set[int] = set()
    for port_name in port_names:
        exact = [(idx, signal) for idx, signal in enumerate(signal_refs) if signal == port_name and idx not in used]
        indexed = []
        for idx, signal in enumerate(signal_refs):
            if idx in used:
                continue
            base, index = _split_ref(signal)
            if base != port_name or index is None:
                continue
            indexed.append((index, idx, signal))
        if exact:
            idx, signal = exact[0]
            used.add(idx)
            connections.append((port_name, signal))
            continue
        if not indexed:
            fallback = next((idx for idx in range(len(signal_refs)) if idx not in used), None)
            if fallback is None:
                raise AssertionError(f"Missing connection for scalar port {port_name!r}")
            used.add(fallback)
            connections.append((port_name, signal_refs[fallback]))
            continue
        indexed.sort(key=lambda item: item[0])
        for index, idx, signal in indexed:
            used.add(idx)
            connections.append((f"{port_name}[{index}]", signal))
    return connections


def _emit_module(
    *,
    module_name: str,
    input_ports: list[SignalDecl],
    output_ports: list[SignalDecl],
    ops: Iterable,
    func_signatures: dict[str, tuple[list[str], list[str]]],
    entry_args: tuple = (),
) -> str:
    declared_ports = {signal.name for signal in input_ports + output_ports}
    wire_widths: dict[str, int] = {}
    instances: list[str] = []
    assigns: list[str] = []
    value_names: dict = {}
    output_port_index = 0
    output_bit_index = 0
    input_refs = [ref for signal in input_ports for ref in _expand_signal_decl(signal)]
    if entry_args:
        if len(entry_args) != len(input_refs):
            raise AssertionError(f"{module_name} block args do not match input signature")
        for arg, ref in zip(entry_args, input_refs):
            value_names[arg] = ref

    for op in ops:
        if isinstance(op, FuncOp):
            continue
        if isinstance(op, ReturnOp):
            for value in op.arguments:
                if output_port_index >= len(output_ports):
                    raise AssertionError("Too many func.return values for module signature")
                target_port = output_ports[output_port_index]
                source = value_names[value]
                target = (
                    target_port.name
                    if target_port.width == 1
                    else f"{target_port.name}[{output_bit_index}]"
                )
                output_bit_index += 1
                if output_bit_index == target_port.width:
                    output_port_index += 1
                    output_bit_index = 0
                if source != target:
                    _collect_wire_base(source, declared_ports, wire_widths)
                    assigns.append(f"  assign {target} = {source};")
            continue
        if isinstance(op, InputPortOp):
            value_names[op.output] = require_wire_name(op.output)
            _collect_wire_value(op.output, declared_ports, wire_widths)
            continue
        if isinstance(op, ConstantOp):
            value_names[op.output] = op.value.data
            continue
        if isinstance(op, OutputPortOp):
            if output_port_index >= len(output_ports):
                raise AssertionError("Too many logic.output ops for module signature")
            target_port = output_ports[output_port_index]
            source = value_names[op.value]
            source_width = get_wire_width(op.value)
            if source_width == target_port.width and require_wire_name(op.value) == target_port.name:
                target = target_port.name
                output_port_index += 1
                output_bit_index = 0
            else:
                target = (
                    target_port.name
                    if target_port.width == 1
                    else f"{target_port.name}[{output_bit_index}]"
                )
                output_bit_index += 1
                if output_bit_index == target_port.width:
                    output_port_index += 1
                    output_bit_index = 0
            if source != target:
                _collect_wire_base(source, declared_ports, wire_widths)
                assigns.append(f"  assign {target} = {source};")
            continue
        if isinstance(op, InstanceOp):
            input_ports_for_op, output_ports_for_op = func_signatures[op.callee.data]
            raw_connections = _expand_grouped_port_connections(
                input_ports_for_op,
                [value_names[value] for value in op.inputs],
            )
            raw_connections.extend(
                _expand_grouped_port_connections(
                    output_ports_for_op,
                    [require_wire_name(value) for value in op.outputs],
                )
            )
            for value in op.inputs:
                _collect_wire_value(value, declared_ports, wire_widths)
            for value in op.outputs:
                _collect_wire_value(value, declared_ports, wire_widths)
            for _, signal in raw_connections:
                _collect_wire_base(signal, declared_ports, wire_widths)
            connections = _compress_instance_connections(raw_connections)
            instances.append(
                _emit_instance(
                    callee=op.callee.data,
                    instance_name=op.instance_name.data,
                    connections=connections,
                )
            )
            for result in op.outputs:
                value_names[result] = require_wire_name(result)
            continue
        if isinstance(op, And2Op):
            output = require_wire_name(op.output)
            lhs = value_names[op.lhs]
            rhs = value_names[op.rhs]
            _collect_wire_base(output, declared_ports, wire_widths)
            _collect_wire_base(lhs, declared_ports, wire_widths)
            _collect_wire_base(rhs, declared_ports, wire_widths)
            instances.append(f"  {op.cell.data} {op.instance_name.data}({output}, {lhs}, {rhs});")
            value_names[op.output] = output
            continue
        if isinstance(op, Or2Op):
            output = require_wire_name(op.output)
            lhs = value_names[op.lhs]
            rhs = value_names[op.rhs]
            _collect_wire_base(output, declared_ports, wire_widths)
            _collect_wire_base(lhs, declared_ports, wire_widths)
            _collect_wire_base(rhs, declared_ports, wire_widths)
            instances.append(f"  {op.cell.data} {op.instance_name.data}({output}, {lhs}, {rhs});")
            value_names[op.output] = output
            continue
        if isinstance(op, Ao21Op):
            output = require_wire_name(op.output)
            and_lhs = value_names[op.and_lhs]
            and_rhs = value_names[op.and_rhs]
            or_rhs = value_names[op.or_rhs]
            _collect_wire_base(output, declared_ports, wire_widths)
            _collect_wire_base(and_lhs, declared_ports, wire_widths)
            _collect_wire_base(and_rhs, declared_ports, wire_widths)
            _collect_wire_base(or_rhs, declared_ports, wire_widths)
            instances.append(
                f"  {op.cell.data} {op.instance_name.data}({output}, {and_lhs}, {and_rhs}, {or_rhs});"
            )
            value_names[op.output] = output
            continue
        if isinstance(op, Xor2Op):
            output = require_wire_name(op.output)
            lhs = value_names[op.lhs]
            rhs = value_names[op.rhs]
            _collect_wire_base(output, declared_ports, wire_widths)
            _collect_wire_base(lhs, declared_ports, wire_widths)
            _collect_wire_base(rhs, declared_ports, wire_widths)
            instances.append(f"  {op.cell.data} {op.instance_name.data}({output}, {lhs}, {rhs});")
            value_names[op.output] = output
            continue
        if isinstance(op, FullAdderOp):
            sum_out = require_wire_name(op.sum_out)
            carry_out = require_wire_name(op.carry_out)
            lhs = value_names[op.lhs]
            rhs = value_names[op.rhs]
            cin = value_names[op.cin]
            _collect_wire_base(sum_out, declared_ports, wire_widths)
            _collect_wire_base(carry_out, declared_ports, wire_widths)
            _collect_wire_base(lhs, declared_ports, wire_widths)
            _collect_wire_base(rhs, declared_ports, wire_widths)
            _collect_wire_base(cin, declared_ports, wire_widths)
            instances.append(
                f"  FAx1_ASAP7_75t_R {op.instance_name.data}({carry_out}, {sum_out}, {lhs}, {rhs}, {cin});"
            )
            value_names[op.sum_out] = sum_out
            value_names[op.carry_out] = carry_out
            continue
        if isinstance(op, HalfAdderOp):
            sum_out = require_wire_name(op.sum_out)
            carry_out = require_wire_name(op.carry_out)
            lhs = value_names[op.lhs]
            rhs = value_names[op.rhs]
            _collect_wire_base(sum_out, declared_ports, wire_widths)
            _collect_wire_base(carry_out, declared_ports, wire_widths)
            _collect_wire_base(lhs, declared_ports, wire_widths)
            _collect_wire_base(rhs, declared_ports, wire_widths)
            instances.append(
                f"  HAxp5_ASAP7_75t_R {op.instance_name.data}({carry_out}, {sum_out}, {lhs}, {rhs});"
            )
            value_names[op.sum_out] = sum_out
            value_names[op.carry_out] = carry_out
            continue
        raise AssertionError(f"Unsupported op {op.name!r} during Verilog emission")

    port_names = ", ".join(signal.name for signal in input_ports + output_ports)
    lines = [f"module {module_name}({port_names});"]
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
    if assigns:
        lines.append("")
        lines.extend(assigns)
    lines.append("")
    lines.append("endmodule")
    return "\n".join(lines)


def emit_verilog(module: ModuleOp) -> str:
    top_name, input_ports, output_ports = _read_module_signature(module)
    func_signatures = {
        func_op.sym_name.data: _func_port_names(func_op)
        for func_op in module.ops
        if isinstance(func_op, FuncOp)
    }
    top_ops = [op for op in module.ops if not isinstance(op, FuncOp)]
    lines = [
        _emit_module(
            module_name=top_name,
            input_ports=input_ports,
            output_ports=output_ports,
            ops=top_ops,
            func_signatures=func_signatures,
        )
    ]

    for op in module.ops:
        if not isinstance(op, FuncOp):
            continue
        func_name, func_inputs, func_outputs = _read_func_signature(op)
        lines.append("")
        lines.append(
            _emit_module(
                module_name=func_name,
                input_ports=func_inputs,
                output_ports=func_outputs,
                ops=op.body.block.ops,
                func_signatures=func_signatures,
                entry_args=op.args,
            )
        )

    lines.append("")
    return "\n".join(lines)
