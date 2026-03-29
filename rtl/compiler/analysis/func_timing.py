"""Reusable hierarchical timing analysis for ASAP7-lowered func regions."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
import re

from xdsl.dialects.builtin import ArrayAttr, ModuleOp, StringAttr
from xdsl.dialects.func import FuncOp

from ..dialects.asap7 import And2Op, Ao21Op, Or2Op, Xor2Op
from ..dialects.logic import ConstantOp, InputPortOp, InstanceOp, decode_port_names
from ..ir import require_wire_name
from ..signals import SignalDecl, decode_signal_decls
from .liberty_model import LibertyModel


_LOGIC_INPUT_PORTS_ATTR = "logic.input_ports"
_LOGIC_OUTPUT_PORTS_ATTR = "logic.output_ports"
_LOGIC_REGION_KIND_ATTR = "logic.region_kind"
_BIT_SELECT_RE = re.compile(r"^(?P<base>[A-Za-z_]\w*)\[(?P<index>\d+)\]$")
FUNC_TIMING_CRITICAL_PORT_PAIRS_ATTR = "timing.critical_port_pairs"
FUNC_TIMING_KEEP_FAST_INSTANCES_ATTR = "timing.keep_fast_instances"
FUNC_TIMING_RECLAIM_INSTANCES_ATTR = "timing.reclaim_instances"
FUNC_TIMING_MAX_DELAY_ATTR = "timing.max_delay"

_DEFAULT_INPUT_SLEW_NS = 0.005
_NEAR_CRITICAL_MARGIN_NS = 0.02
_TOP_PAIR_LIMIT = 4


@dataclass(frozen=True)
class GateArc:
    instance_name: str
    cell: str
    output_signal: str
    output_pin: str
    inputs: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class PortPath:
    input_ref: str
    output_ref: str
    delay_ns: float
    instances: tuple[str, ...]

    def encode(self) -> str:
        return f"{self.input_ref}->{self.output_ref}:{self.delay_ns:.4f}"


@dataclass
class FuncTimingReport:
    func_name: str
    instance_names: tuple[str, ...] = ()
    port_paths: list[PortPath] = field(default_factory=list)
    output_arrivals_ns: dict[str, float] = field(default_factory=dict)
    output_slews_ns: dict[str, float] = field(default_factory=dict)
    input_tails_ns: dict[str, float] = field(default_factory=dict)
    instance_scores_ns: dict[str, float] = field(default_factory=dict)
    signal_arrivals_ns: dict[str, float] = field(default_factory=dict)
    signal_tails_ns: dict[str, float] = field(default_factory=dict)
    signal_scores_ns: dict[str, float] = field(default_factory=dict)

    @property
    def max_delay_ns(self) -> float:
        return max((path.delay_ns for path in self.port_paths), default=0.0)

    @property
    def critical_port_pairs(self) -> list[PortPath]:
        return sorted(self.port_paths, key=lambda path: path.delay_ns, reverse=True)[:_TOP_PAIR_LIMIT]

    @property
    def keep_fast_instances(self) -> tuple[str, ...]:
        if self.instance_scores_ns:
            max_score = max(self.instance_scores_ns.values(), default=0.0)
            keep = [
                name
                for name, score in self.instance_scores_ns.items()
                if score + 1e-12 >= max_score - _NEAR_CRITICAL_MARGIN_NS
            ]
            return tuple(keep)
        if not self.port_paths:
            return ()
        max_delay = self.max_delay_ns
        keep: list[str] = []
        seen: set[str] = set()
        for path in self.port_paths:
            if path.delay_ns + 1e-12 < max_delay - _NEAR_CRITICAL_MARGIN_NS:
                continue
            for instance_name in path.instances:
                if instance_name in seen:
                    continue
                seen.add(instance_name)
                keep.append(instance_name)
        return tuple(keep)

    @property
    def reclaim_instances(self) -> tuple[str, ...]:
        keep = set(self.keep_fast_instances)
        return tuple(name for name in self.instance_names if name not in keep)


@dataclass
class ModuleTimingAnalysis:
    func_reports: dict[str, FuncTimingReport] = field(default_factory=dict)


def analyze_module_timing(module: ModuleOp, liberty_model: LibertyModel) -> ModuleTimingAnalysis:
    func_ops = {func_op.sym_name.data: func_op for func_op in module.ops if isinstance(func_op, FuncOp)}
    internal_input_loads = {
        name: _compute_internal_input_loads(func_op, liberty_model)
        for name, func_op in func_ops.items()
    }

    top_net_loads: dict[str, float] = defaultdict(float)
    for op in module.ops:
        if not isinstance(op, InstanceOp):
            continue
        for port_name, top_ref in _expand_grouped_port_refs(decode_port_names(op.input_ports), op.inputs):
            top_net_loads[top_ref] += internal_input_loads[op.callee.data].get(port_name, 0.0)

    external_loads: dict[str, dict[str, float]] = {name: defaultdict(float) for name in func_ops}
    for op in module.ops:
        if not isinstance(op, InstanceOp):
            continue
        for port_name, top_ref in _expand_grouped_port_refs(decode_port_names(op.output_ports), op.outputs):
            external_loads[op.callee.data][port_name] += top_net_loads.get(top_ref, 0.0)

    instance_ops = [op for op in module.ops if isinstance(op, InstanceOp)]
    top_net_arrivals: dict[str, float] = {}
    top_net_slews: dict[str, float] = {}
    top_input_ports, _ = _read_top_signature(module)
    for signal in top_input_ports:
        for ref in _expand_signal_decl(signal):
            top_net_arrivals[ref] = 0.0
            top_net_slews[ref] = _DEFAULT_INPUT_SLEW_NS

    ordered_instances = _topologically_sort_instances(instance_ops)
    instance_inputs: dict[str, tuple[dict[str, float], dict[str, float]]] = {}
    for op in ordered_instances:
        input_arrivals_ns: dict[str, float] = {}
        input_slews_ns: dict[str, float] = {}
        for port_name, top_ref in _expand_grouped_port_refs(decode_port_names(op.input_ports), op.inputs):
            input_arrivals_ns[port_name] = top_net_arrivals.get(top_ref, 0.0)
            input_slews_ns[port_name] = top_net_slews.get(top_ref, _DEFAULT_INPUT_SLEW_NS)
        instance_inputs[op.instance_name.data] = (input_arrivals_ns, input_slews_ns)

        report = analyze_func_timing(
            func_ops[op.callee.data],
            liberty_model,
            dict(external_loads.get(op.callee.data, {})),
            input_arrivals_ns=input_arrivals_ns,
            input_slews_ns=input_slews_ns,
        )

        for port_name, top_ref in _expand_grouped_port_refs(decode_port_names(op.output_ports), op.outputs):
            if port_name not in report.output_arrivals_ns:
                continue
            top_net_arrivals[top_ref] = report.output_arrivals_ns[port_name]
            top_net_slews[top_ref] = report.output_slews_ns.get(port_name, _DEFAULT_INPUT_SLEW_NS)

    reports: dict[str, FuncTimingReport] = {}
    top_net_tails: dict[str, float] = {}
    _, top_output_ports = _read_top_signature(module)
    for signal in top_output_ports:
        for ref in _expand_signal_decl(signal):
            top_net_tails[ref] = 0.0

    for op in reversed(ordered_instances):
        input_arrivals_ns, input_slews_ns = instance_inputs[op.instance_name.data]
        output_tail_ns: dict[str, float] = {}
        for port_name, top_ref in _expand_grouped_port_refs(decode_port_names(op.output_ports), op.outputs):
            output_tail_ns[port_name] = top_net_tails.get(top_ref, 0.0)

        report = analyze_func_timing(
            func_ops[op.callee.data],
            liberty_model,
            dict(external_loads.get(op.callee.data, {})),
            input_arrivals_ns=input_arrivals_ns,
            input_slews_ns=input_slews_ns,
            output_tail_ns=output_tail_ns,
        )
        reports[op.callee.data] = report

        for port_name, top_ref in _expand_grouped_port_refs(decode_port_names(op.input_ports), op.inputs):
            top_net_tails[top_ref] = max(
                top_net_tails.get(top_ref, 0.0),
                report.input_tails_ns.get(port_name, 0.0),
            )

    return ModuleTimingAnalysis(func_reports=reports)


def analyze_func_timing(
    func_op: FuncOp,
    liberty_model: LibertyModel,
    external_output_loads_ff: dict[str, float] | None = None,
    input_arrivals_ns: dict[str, float] | None = None,
    input_slews_ns: dict[str, float] | None = None,
    output_tail_ns: dict[str, float] | None = None,
) -> FuncTimingReport:
    func_name, input_ports, output_ports = _read_func_signature(func_op)
    gate_arcs = _iter_gate_arcs(func_op)
    external_output_loads_ff = external_output_loads_ff or {}
    input_arrivals_ns = input_arrivals_ns or {}
    input_slews_ns = input_slews_ns or {}
    output_tail_ns = output_tail_ns or {}
    input_refs = {ref for signal in input_ports for ref in _expand_signal_decl(signal)}
    output_refs = [ref for signal in output_ports for ref in _expand_signal_decl(signal)]
    net_loads = _compute_net_loads(func_op, liberty_model)
    for ref, load_ff in external_output_loads_ff.items():
        net_loads[ref] += load_ff

    arrivals: dict[str, float] = {ref: input_arrivals_ns.get(ref, 0.0) for ref in input_refs}
    slews: dict[str, float] = {ref: input_slews_ns.get(ref, _DEFAULT_INPUT_SLEW_NS) for ref in input_refs}
    predecessors: dict[str, tuple[str, str] | None] = {ref: None for ref in input_refs}

    for gate in gate_arcs:
        load_ff = net_loads.get(gate.output_signal, 0.0)
        best_input_signal = gate.inputs[0][1]
        best_arrival = float("-inf")
        best_slew = _DEFAULT_INPUT_SLEW_NS
        for pin_name, input_signal in gate.inputs:
            if _is_literal(input_signal):
                input_arrival = 0.0
                input_slew = _DEFAULT_INPUT_SLEW_NS
            else:
                input_arrival = arrivals.get(input_signal, 0.0)
                input_slew = slews.get(input_signal, _DEFAULT_INPUT_SLEW_NS)
            candidate_delay = liberty_model.delay(gate.cell, (pin_name, gate.output_pin), input_slew, load_ff)
            candidate_arrival = input_arrival + candidate_delay
            if candidate_arrival <= best_arrival:
                continue
            best_arrival = candidate_arrival
            best_input_signal = input_signal
            best_slew = liberty_model.transition(gate.cell, (pin_name, gate.output_pin), input_slew, load_ff)
        arrivals[gate.output_signal] = best_arrival
        slews[gate.output_signal] = best_slew
        predecessors[gate.output_signal] = (best_input_signal, gate.instance_name)

    port_paths: list[PortPath] = []
    for output_ref in output_refs:
        if output_ref not in arrivals:
            continue
        trace_input, instances = _trace_port_path(output_ref, predecessors, input_refs)
        if trace_input is None:
            continue
        port_paths.append(
            PortPath(
                input_ref=trace_input,
                output_ref=output_ref,
                delay_ns=arrivals[output_ref] + output_tail_ns.get(output_ref, 0.0),
                instances=instances,
            )
        )

    reverse_tails: dict[str, float] = {
        output_ref: output_tail_ns.get(output_ref, 0.0) for output_ref in output_refs
    }
    instance_scores_ns: dict[str, float] = {}
    for gate in reversed(gate_arcs):
        output_tail = reverse_tails.get(gate.output_signal)
        if output_tail is None:
            continue
        instance_scores_ns[gate.instance_name] = max(
            instance_scores_ns.get(gate.instance_name, 0.0),
            arrivals.get(gate.output_signal, 0.0) + output_tail,
        )
        load_ff = net_loads.get(gate.output_signal, 0.0)
        for pin_name, input_signal in gate.inputs:
            if _is_literal(input_signal):
                continue
            input_slew = slews.get(input_signal, _DEFAULT_INPUT_SLEW_NS)
            gate_delay = liberty_model.delay(gate.cell, (pin_name, gate.output_pin), input_slew, load_ff)
            reverse_tails[input_signal] = max(
                reverse_tails.get(input_signal, 0.0),
                gate_delay + output_tail,
            )

    return FuncTimingReport(
        func_name=func_name,
        instance_names=tuple(gate.instance_name for gate in gate_arcs),
        port_paths=port_paths,
        output_arrivals_ns={output_ref: arrivals[output_ref] for output_ref in output_refs if output_ref in arrivals},
        output_slews_ns={output_ref: slews[output_ref] for output_ref in output_refs if output_ref in slews},
        input_tails_ns={ref: reverse_tails.get(ref, 0.0) for ref in input_refs},
        instance_scores_ns=instance_scores_ns,
        signal_arrivals_ns=dict(arrivals),
        signal_tails_ns=dict(reverse_tails),
        signal_scores_ns={
            signal: arrivals.get(signal, 0.0) + reverse_tails.get(signal, 0.0)
            for signal in set(arrivals) | set(reverse_tails)
        },
    )


def _compute_internal_input_loads(func_op: FuncOp, liberty_model: LibertyModel) -> dict[str, float]:
    loads = _compute_net_loads(func_op, liberty_model)
    _, input_ports, _ = _read_func_signature(func_op)
    refs = {ref for signal in input_ports for ref in _expand_signal_decl(signal)}
    return {ref: loads.get(ref, 0.0) for ref in refs}


def _compute_net_loads(func_op: FuncOp, liberty_model: LibertyModel) -> dict[str, float]:
    loads: dict[str, float] = defaultdict(float)
    for gate in _iter_gate_arcs(func_op):
        for pin_name, signal_name in gate.inputs:
            if _is_literal(signal_name):
                continue
            loads[signal_name] += liberty_model.pin_capacitance(gate.cell, pin_name)
    return loads


def _trace_port_path(
    output_ref: str,
    predecessors: dict[str, tuple[str, str] | None],
    input_refs: set[str],
) -> tuple[str | None, tuple[str, ...]]:
    instances: list[str] = []
    cursor = output_ref
    while True:
        if cursor in input_refs:
            instances.reverse()
            return cursor, tuple(instances)
        predecessor = predecessors.get(cursor)
        if predecessor is None:
            return None, ()
        prev_signal, instance_name = predecessor
        instances.append(instance_name)
        if _is_literal(prev_signal):
            return None, ()
        cursor = prev_signal


def _read_top_signature(module: ModuleOp) -> tuple[list[SignalDecl], list[SignalDecl]]:
    input_ports_attr = module.attributes.get("input_ports")
    output_ports_attr = module.attributes.get("output_ports")
    if not isinstance(input_ports_attr, ArrayAttr):
        raise AssertionError("builtin.module is missing 'input_ports'")
    if not isinstance(output_ports_attr, ArrayAttr):
        raise AssertionError("builtin.module is missing 'output_ports'")
    return decode_signal_decls(input_ports_attr), decode_signal_decls(output_ports_attr)


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


def _topologically_sort_instances(instance_ops: list[InstanceOp]) -> list[InstanceOp]:
    drivers: dict[str, str] = {}
    for op in instance_ops:
        for value in op.outputs:
            drivers[require_wire_name(value)] = op.instance_name.data

    incoming_count: dict[str, int] = defaultdict(int)
    dependents: dict[str, list[str]] = defaultdict(list)
    op_by_name = {op.instance_name.data: op for op in instance_ops}
    for op in instance_ops:
        incoming_count.setdefault(op.instance_name.data, 0)
        for value in op.inputs:
            producer = drivers.get(require_wire_name(value))
            if producer is None or producer == op.instance_name.data:
                continue
            dependents[producer].append(op.instance_name.data)
            incoming_count[op.instance_name.data] += 1

    queue = deque(sorted(name for name, degree in incoming_count.items() if degree == 0))
    ordered_names: list[str] = []
    while queue:
        name = queue.popleft()
        ordered_names.append(name)
        for consumer in dependents[name]:
            incoming_count[consumer] -= 1
            if incoming_count[consumer] == 0:
                queue.append(consumer)

    if len(ordered_names) != len(instance_ops):
        raise AssertionError("Top-level instance graph contains a cycle")
    return [op_by_name[name] for name in ordered_names]


def _expand_signal_decl(signal: SignalDecl) -> tuple[str, ...]:
    if signal.width == 1:
        return (signal.name,)
    return tuple(f"{signal.name}[{index}]" for index in range(signal.width))


def _expand_grouped_port_refs(port_names: list[str], values) -> list[tuple[str, str]]:
    connections: list[tuple[str, str]] = []
    signal_refs = [require_wire_name(value) for value in values]
    used: set[int] = set()
    for port_name in port_names:
        exact = [(idx, signal) for idx, signal in enumerate(signal_refs) if signal == port_name and idx not in used]
        indexed = []
        for idx, signal in enumerate(signal_refs):
            if idx in used:
                continue
            match = _BIT_SELECT_RE.match(signal)
            if match is None or match.group("base") != port_name:
                continue
            indexed.append((int(match.group("index")), idx, signal))
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


def _iter_gate_arcs(func_op: FuncOp) -> list[GateArc]:
    arcs: list[GateArc] = []
    value_names: dict = {}
    for op in func_op.body.block.ops:
        if isinstance(op, InputPortOp):
            value_names[op.output] = require_wire_name(op.output)
            continue
        if isinstance(op, ConstantOp):
            value_names[op.output] = op.value.data
            continue
        if isinstance(op, And2Op):
            output_name = require_wire_name(op.output)
            arcs.append(
                GateArc(
                    instance_name=op.instance_name.data,
                    cell=op.cell.data,
                    output_signal=output_name,
                    output_pin="Y",
                    inputs=(("A", value_names[op.lhs]), ("B", value_names[op.rhs])),
                )
            )
            value_names[op.output] = output_name
            continue
        if isinstance(op, Or2Op):
            output_name = require_wire_name(op.output)
            arcs.append(
                GateArc(
                    instance_name=op.instance_name.data,
                    cell=op.cell.data,
                    output_signal=output_name,
                    output_pin="Y",
                    inputs=(("A", value_names[op.lhs]), ("B", value_names[op.rhs])),
                )
            )
            value_names[op.output] = output_name
            continue
        if isinstance(op, Xor2Op):
            output_name = require_wire_name(op.output)
            arcs.append(
                GateArc(
                    instance_name=op.instance_name.data,
                    cell=op.cell.data,
                    output_signal=output_name,
                    output_pin="Y",
                    inputs=(("A", value_names[op.lhs]), ("B", value_names[op.rhs])),
                )
            )
            value_names[op.output] = output_name
            continue
        if isinstance(op, Ao21Op):
            output_name = require_wire_name(op.output)
            arcs.append(
                GateArc(
                    instance_name=op.instance_name.data,
                    cell=op.cell.data,
                    output_signal=output_name,
                    output_pin="Y",
                    inputs=(
                        ("A1", value_names[op.and_lhs]),
                        ("A2", value_names[op.and_rhs]),
                        ("B", value_names[op.or_rhs]),
                    ),
                )
            )
            value_names[op.output] = output_name
    return arcs


def _is_literal(signal: str) -> bool:
    return "'" in signal or signal.isdigit()
