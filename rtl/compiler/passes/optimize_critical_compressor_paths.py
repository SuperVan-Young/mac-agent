"""Timing-guided local rewrites for ASAP7-lowered compressor trees."""

from __future__ import annotations

from dataclasses import dataclass
import os

from xdsl.context import Context
from xdsl.dialects.builtin import ArrayAttr, ModuleOp, StringAttr
from xdsl.dialects.func import FuncOp
from xdsl.passes import ModulePass

from ..analysis import analyze_module_timing, load_default_liberty_model
from ..dialects.asap7 import And2Op, Ao21Op, Xor2Op
from ..dialects.logic import ConstantOp, InputPortOp
from ..ir import expand_signal_decl_refs, require_wire_name, signal_decls_from_wires
from ..signals import decode_signal_decls


_LOGIC_REGION_KIND_ATTR = "logic.region_kind"
_COMPRESSOR_REGION_KIND = "arith.compressor_tree"
_NEAR_CRITICAL_MARGIN_NS = 0.01
_DEFAULT_MAX_ITERATIONS = 3
_MAX_ITERATIONS_ENV = "MAC_AGENT_COMPRESSOR_OPT_MAX_ITERATIONS"


@dataclass
class _FullAdderCone:
    stem: str
    xor_ab: Xor2Op
    xor_sum: Xor2Op
    and_ab: And2Op
    ao21_carry: Ao21Op
    value_names: dict

    @property
    def lhs(self) -> str:
        return self.value_names[self.xor_ab.lhs]

    @property
    def rhs(self) -> str:
        return self.value_names[self.xor_ab.rhs]

    @property
    def cin(self) -> str:
        return self.value_names[self.xor_sum.rhs]

    @property
    def sum_out(self) -> str:
        return require_wire_name(self.xor_sum.output)

    @property
    def carry_out(self) -> str:
        return require_wire_name(self.ao21_carry.output)


def _build_value_names(func_op: FuncOp) -> dict:
    value_names = {}
    input_ports = signal_decls_from_wires(func_op.args, kind="input")
    if not input_ports:
        input_ports_attr = func_op.attributes.get("logic.input_ports")
        if not isinstance(input_ports_attr, ArrayAttr):
            raise AssertionError(f"{func_op.sym_name.data} is missing logic.input_ports")
        input_ports = decode_signal_decls(input_ports_attr)
    input_refs = [ref for signal in input_ports for ref in expand_signal_decl_refs(signal)]
    for arg, ref in zip(func_op.args, input_refs):
        value_names[arg] = ref
    for op in func_op.body.block.ops:
        if isinstance(op, InputPortOp):
            value_names[op.output] = require_wire_name(op.output)
            continue
        if isinstance(op, ConstantOp):
            value_names[op.output] = op.value.data
            continue
        if isinstance(op, Xor2Op | And2Op | Ao21Op):
            value_names[op.output] = require_wire_name(op.output)
    return value_names


def _collect_full_adder_cones(func_op: FuncOp) -> list[_FullAdderCone]:
    value_names = _build_value_names(func_op)
    xor_by_name: dict[str, Xor2Op] = {}
    and_by_name: dict[str, And2Op] = {}
    ao21_by_name: dict[str, Ao21Op] = {}
    for op in func_op.body.block.ops:
        if isinstance(op, Xor2Op):
            xor_by_name[op.instance_name.data] = op
            continue
        if isinstance(op, And2Op):
            and_by_name[op.instance_name.data] = op
            continue
        if isinstance(op, Ao21Op):
            ao21_by_name[op.instance_name.data] = op

    cones: list[_FullAdderCone] = []
    for xor_name, xor_ab in xor_by_name.items():
        if not xor_name.endswith("_xor_ab"):
            continue
        stem = xor_name[: -len("_xor_ab")]
        xor_sum = xor_by_name.get(f"{stem}_xor_sum")
        and_ab = and_by_name.get(f"{stem}_and_ab")
        ao21_carry = ao21_by_name.get(f"{stem}_ao21_carry")
        if xor_sum is None or and_ab is None or ao21_carry is None:
            continue
        if xor_ab.owner.data != "compressor_tree":
            continue
        cones.append(
            _FullAdderCone(
                stem=stem,
                xor_ab=xor_ab,
                xor_sum=xor_sum,
                and_ab=and_ab,
                ao21_carry=ao21_carry,
                value_names=value_names,
            )
        )
    return cones


def _signal_score(report, signal: str) -> float:
    return report.signal_scores_ns.get(signal, 0.0)


def _signal_arrival(report, signal: str) -> float:
    return report.signal_arrivals_ns.get(signal, 0.0)


def _rewrite_cone_inputs(cone: _FullAdderCone, lhs, rhs, cin) -> None:
    cone.xor_ab.operands[0] = lhs
    cone.xor_ab.operands[1] = rhs
    cone.and_ab.operands[0] = lhs
    cone.and_ab.operands[1] = rhs
    cone.xor_sum.operands[1] = cin
    cone.ao21_carry.operands[1] = cin


def _read_max_iterations() -> int:
    raw = os.environ.get(_MAX_ITERATIONS_ENV)
    if raw is None:
        return _DEFAULT_MAX_ITERATIONS
    try:
        value = int(raw)
    except ValueError as exc:
        raise AssertionError(
            f"{_MAX_ITERATIONS_ENV} must be an integer, got {raw!r}"
        ) from exc
    if value < 0:
        raise AssertionError(f"{_MAX_ITERATIONS_ENV} must be non-negative, got {value}")
    return value


def _choose_rewrite(cones: list[_FullAdderCone], report):
    max_delay = report.max_delay_ns
    candidates: list[tuple[float, float, str, _FullAdderCone, list, object]] = []
    for cone in cones:
        cone_score = max(
            _signal_score(report, cone.sum_out),
            _signal_score(report, cone.carry_out),
        )
        if cone_score + 1e-12 < max_delay - _NEAR_CRITICAL_MARGIN_NS:
            continue

        signal_values = [
            (cone.lhs, cone.xor_ab.lhs),
            (cone.rhs, cone.xor_ab.rhs),
            (cone.cin, cone.xor_sum.rhs),
        ]
        signals = [name for name, _ in signal_values]
        latest_signal = max(signals, key=lambda signal: (_signal_arrival(report, signal), signal))
        if latest_signal == cone.cin:
            continue

        remaining = [(name, value) for name, value in signal_values if name != latest_signal]
        if len(remaining) != 2:
            continue
        arrival_spread = _signal_arrival(report, latest_signal) - max(
            _signal_arrival(report, remaining[0][0]),
            _signal_arrival(report, remaining[1][0]),
        )
        candidates.append(
            (
                cone_score,
                arrival_spread,
                cone.stem,
                cone,
                remaining,
                next(value for name, value in signal_values if name == latest_signal),
            )
        )
    if not candidates:
        return None
    candidates.sort(reverse=True, key=lambda item: (item[0], item[1], item[2]))
    _, _, _, cone, remaining, latest_value = candidates[0]
    remaining.sort(key=lambda item: (_signal_arrival(report, item[0]), item[0]))
    return cone, remaining[0][1], remaining[1][1], latest_value


def _optimize_module_once(module: ModuleOp, analysis) -> bool:
    candidates: list[tuple[float, float, str, FuncOp, _FullAdderCone, object, object, object]] = []
    for inner in module.ops:
        if not isinstance(inner, FuncOp):
            continue
        region_kind_attr = inner.attributes.get(_LOGIC_REGION_KIND_ATTR)
        if not isinstance(region_kind_attr, StringAttr):
            continue
        if region_kind_attr.data != _COMPRESSOR_REGION_KIND:
            continue
        report = analysis.func_reports.get(inner.sym_name.data)
        if report is None:
            continue
        rewrite = _choose_rewrite(_collect_full_adder_cones(inner), report)
        if rewrite is None:
            continue
        cone, lhs, rhs, cin = rewrite
        cone_score = max(
            _signal_score(report, cone.sum_out),
            _signal_score(report, cone.carry_out),
        )
        arrival_spread = _signal_arrival(report, cone.value_names[cin]) - max(
            _signal_arrival(report, cone.value_names[lhs]),
            _signal_arrival(report, cone.value_names[rhs]),
        )
        candidates.append(
            (cone_score, arrival_spread, inner.sym_name.data, inner, cone, lhs, rhs, cin)
        )
    if not candidates:
        return False
    candidates.sort(reverse=True, key=lambda item: (item[0], item[1], item[2]))
    _, _, _, _, cone, lhs, rhs, cin = candidates[0]
    _rewrite_cone_inputs(cone, lhs, rhs, cin)
    return True


@dataclass(frozen=True)
class OptimizeCriticalCompressorPathsPass(ModulePass):
    name = "optimize-critical-compressor-paths"

    def apply(self, ctx: Context, op: ModuleOp) -> None:
        del ctx
        max_iterations = _read_max_iterations()
        if max_iterations == 0:
            return
        liberty_model = load_default_liberty_model()
        for _ in range(max_iterations):
            analysis = analyze_module_timing(op, liberty_model)
            if not _optimize_module_once(op, analysis):
                break
