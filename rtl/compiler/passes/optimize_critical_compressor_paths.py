"""Timing-guided local rewrites for ASAP7-lowered compressor trees."""

from __future__ import annotations

from dataclasses import dataclass
import os

from xdsl.context import Context
from xdsl.dialects.builtin import ModuleOp, StringAttr
from xdsl.dialects.func import FuncOp
from xdsl.passes import ModulePass

from ..analysis import analyze_module_timing, load_default_liberty_model
from ..dialects.asap7 import And2Op, Ao21Op, Xor2Op


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

    @property
    def lhs(self) -> str:
        return self.xor_ab.lhs.data

    @property
    def rhs(self) -> str:
        return self.xor_ab.rhs.data

    @property
    def cin(self) -> str:
        return self.xor_sum.rhs.data

    @property
    def sum_out(self) -> str:
        return self.xor_sum.output.data

    @property
    def carry_out(self) -> str:
        return self.ao21_carry.output.data


def _collect_full_adder_cones(func_op: FuncOp) -> list[_FullAdderCone]:
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
            )
        )
    return cones


def _signal_score(report, signal: str) -> float:
    return report.signal_scores_ns.get(signal, 0.0)


def _signal_arrival(report, signal: str) -> float:
    return report.signal_arrivals_ns.get(signal, 0.0)


def _rewrite_cone_inputs(cone: _FullAdderCone, lhs: str, rhs: str, cin: str) -> None:
    cone.xor_ab.properties["lhs"] = StringAttr(lhs)
    cone.xor_ab.properties["rhs"] = StringAttr(rhs)
    cone.and_ab.properties["lhs"] = StringAttr(lhs)
    cone.and_ab.properties["rhs"] = StringAttr(rhs)
    cone.xor_sum.properties["rhs"] = StringAttr(cin)
    cone.ao21_carry.properties["and_rhs"] = StringAttr(cin)


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
    candidates: list[tuple[float, float, str, _FullAdderCone, list[str], str]] = []
    for cone in cones:
        cone_score = max(
            _signal_score(report, cone.sum_out),
            _signal_score(report, cone.carry_out),
        )
        if cone_score + 1e-12 < max_delay - _NEAR_CRITICAL_MARGIN_NS:
            continue

        signals = [cone.lhs, cone.rhs, cone.cin]
        latest_signal = max(signals, key=lambda signal: (_signal_arrival(report, signal), signal))
        if latest_signal == cone.cin:
            continue

        remaining = [signal for signal in signals if signal != latest_signal]
        if len(remaining) != 2:
            continue
        arrival_spread = _signal_arrival(report, latest_signal) - max(
            _signal_arrival(report, remaining[0]),
            _signal_arrival(report, remaining[1]),
        )
        candidates.append(
            (cone_score, arrival_spread, cone.stem, cone, remaining, latest_signal)
        )
    if not candidates:
        return None
    candidates.sort(reverse=True, key=lambda item: (item[0], item[1], item[2]))
    _, _, _, cone, remaining, latest_signal = candidates[0]
    remaining.sort(key=lambda signal: (_signal_arrival(report, signal), signal))
    return cone, remaining[0], remaining[1], latest_signal


def _optimize_module_once(module: ModuleOp, analysis) -> bool:
    candidates: list[tuple[float, float, str, FuncOp, _FullAdderCone, str, str, str]] = []
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
        arrival_spread = _signal_arrival(report, cin) - max(
            _signal_arrival(report, lhs),
            _signal_arrival(report, rhs),
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
