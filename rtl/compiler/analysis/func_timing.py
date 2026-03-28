"""Reusable hierarchical timing analysis for ASAP7-lowered func regions."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from xdsl.dialects.builtin import ArrayAttr, ModuleOp, StringAttr
from xdsl.dialects.func import FuncOp

from ..dialects.asap7 import And2Op, Ao21Op, Or2Op, Xor2Op
from ..dialects.logic import InstanceOp, decode_connections
from ..signals import SignalDecl, decode_signal_decls
from .liberty_model import LibertyModel


_LOGIC_INPUT_PORTS_ATTR = "logic.input_ports"
_LOGIC_OUTPUT_PORTS_ATTR = "logic.output_ports"
_LOGIC_REGION_KIND_ATTR = "logic.region_kind"
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

    @property
    def max_delay_ns(self) -> float:
        return max((path.delay_ns for path in self.port_paths), default=0.0)

    @property
    def critical_port_pairs(self) -> list[PortPath]:
        return sorted(self.port_paths, key=lambda path: path.delay_ns, reverse=True)[:_TOP_PAIR_LIMIT]

    @property
    def keep_fast_instances(self) -> tuple[str, ...]:
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
    func_ops = {
        func_op.sym_name.data: func_op
        for func_op in module.ops
        if isinstance(func_op, FuncOp)
    }
    signatures = {
        name: _read_func_signature(func_op)
        for name, func_op in func_ops.items()
    }
    internal_input_loads = {
        name: _compute_internal_input_loads(func_op, liberty_model)
        for name, func_op in func_ops.items()
    }

    top_net_loads: dict[str, float] = defaultdict(float)
    for op in module.ops:
        if not isinstance(op, InstanceOp):
            continue
        _, input_ports, _ = signatures[op.callee.data]
        for port_name, signal_name in decode_connections(op.input_connections):
            for port_ref, top_ref in _expand_connection_refs(
                port_name=port_name,
                signal_name=signal_name,
                port_decls=input_ports,
            ):
                top_net_loads[top_ref] += internal_input_loads[op.callee.data].get(port_ref, 0.0)

    external_loads: dict[str, dict[str, float]] = {
        name: defaultdict(float) for name in func_ops
    }
    for op in module.ops:
        if not isinstance(op, InstanceOp):
            continue
        _, _, output_ports = signatures[op.callee.data]
        for port_name, signal_name in decode_connections(op.output_connections):
            for port_ref, top_ref in _expand_connection_refs(
                port_name=port_name,
                signal_name=signal_name,
                port_decls=output_ports,
            ):
                external_loads[op.callee.data][port_ref] += top_net_loads.get(top_ref, 0.0)

    return ModuleTimingAnalysis(
        func_reports={
            name: analyze_func_timing(
                func_op,
                liberty_model,
                dict(external_loads.get(name, {})),
            )
            for name, func_op in func_ops.items()
        }
    )


def analyze_func_timing(
    func_op: FuncOp,
    liberty_model: LibertyModel,
    external_output_loads_ff: dict[str, float] | None = None,
) -> FuncTimingReport:
    func_name, input_ports, output_ports = _read_func_signature(func_op)
    gate_arcs = _iter_gate_arcs(func_op)
    external_output_loads_ff = external_output_loads_ff or {}
    input_refs = {ref for signal in input_ports for ref in _expand_signal_decl(signal)}
    output_refs = [ref for signal in output_ports for ref in _expand_signal_decl(signal)]
    net_loads = _compute_net_loads(func_op, liberty_model)
    for ref, load_ff in external_output_loads_ff.items():
        net_loads[ref] += load_ff

    arrivals: dict[str, float] = {
        ref: 0.0 for ref in input_refs
    }
    slews: dict[str, float] = {
        ref: _DEFAULT_INPUT_SLEW_NS for ref in input_refs
    }
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
            best_slew = liberty_model.transition(
                gate.cell,
                (pin_name, gate.output_pin),
                input_slew,
                load_ff,
            )
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
                delay_ns=arrivals[output_ref],
                instances=instances,
            )
        )

    return FuncTimingReport(
        func_name=func_name,
        instance_names=tuple(gate.instance_name for gate in gate_arcs),
        port_paths=port_paths,
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


def _expand_signal_decl(signal: SignalDecl) -> tuple[str, ...]:
    if signal.width == 1:
        return (signal.name,)
    return tuple(f"{signal.name}[{index}]" for index in range(signal.width))


def _expand_connection_refs(
    *,
    port_name: str,
    signal_name: str,
    port_decls: list[SignalDecl],
) -> list[tuple[str, str]]:
    decl = next((item for item in port_decls if item.name == port_name), None)
    if decl is None:
        raise AssertionError(f"Unknown port {port_name!r}")
    if decl.width == 1:
        return [(port_name, signal_name)]
    return [
        (f"{port_name}[{index}]", f"{signal_name}[{index}]")
        for index in range(decl.width)
    ]


def _iter_gate_arcs(func_op: FuncOp) -> list[GateArc]:
    arcs: list[GateArc] = []
    for op in func_op.body.block.ops:
        if isinstance(op, And2Op):
            arcs.append(
                GateArc(
                    instance_name=op.instance_name.data,
                    cell=op.cell.data,
                    output_signal=op.output.data,
                    output_pin="Y",
                    inputs=(("A", op.lhs.data), ("B", op.rhs.data)),
                )
            )
            continue
        if isinstance(op, Or2Op):
            arcs.append(
                GateArc(
                    instance_name=op.instance_name.data,
                    cell=op.cell.data,
                    output_signal=op.output.data,
                    output_pin="Y",
                    inputs=(("A", op.lhs.data), ("B", op.rhs.data)),
                )
            )
            continue
        if isinstance(op, Xor2Op):
            arcs.append(
                GateArc(
                    instance_name=op.instance_name.data,
                    cell=op.cell.data,
                    output_signal=op.output.data,
                    output_pin="Y",
                    inputs=(("A", op.lhs.data), ("B", op.rhs.data)),
                )
            )
            continue
        if isinstance(op, Ao21Op):
            arcs.append(
                GateArc(
                    instance_name=op.instance_name.data,
                    cell=op.cell.data,
                    output_signal=op.output.data,
                    output_pin="Y",
                    inputs=(
                        ("A1", op.and_lhs.data),
                        ("A2", op.and_rhs.data),
                        ("B", op.or_rhs.data),
                    ),
                )
            )
    return arcs


def _is_literal(signal: str) -> bool:
    return "'" in signal or signal.isdigit()
