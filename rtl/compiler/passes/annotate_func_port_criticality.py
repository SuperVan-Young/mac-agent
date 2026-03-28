"""Annotate hierarchical func regions with liberty-driven timing guidance."""

from __future__ import annotations

from dataclasses import dataclass

from xdsl.context import Context
from xdsl.dialects.builtin import ArrayAttr, ModuleOp, StringAttr
from xdsl.dialects.func import FuncOp
from xdsl.passes import ModulePass

from ..analysis import (
    FUNC_TIMING_CRITICAL_PORT_PAIRS_ATTR,
    FUNC_TIMING_KEEP_FAST_INSTANCES_ATTR,
    FUNC_TIMING_RECLAIM_INSTANCES_ATTR,
    FUNC_TIMING_MAX_DELAY_ATTR,
    analyze_module_timing,
    load_default_liberty_model,
)


def _encode_string_array(values: list[str] | tuple[str, ...]) -> ArrayAttr[StringAttr]:
    return ArrayAttr(StringAttr(value) for value in values)


@dataclass(frozen=True)
class AnnotateFuncPortCriticalityPass(ModulePass):
    name = "annotate-func-port-criticality"

    def apply(self, ctx: Context, op: ModuleOp) -> None:
        del ctx
        analysis = analyze_module_timing(op, load_default_liberty_model())
        for inner in op.ops:
            if not isinstance(inner, FuncOp):
                continue
            report = analysis.func_reports.get(inner.sym_name.data)
            if report is None:
                continue
            inner.attributes[FUNC_TIMING_CRITICAL_PORT_PAIRS_ATTR] = _encode_string_array(
                [path.encode() for path in report.critical_port_pairs]
            )
            inner.attributes[FUNC_TIMING_KEEP_FAST_INSTANCES_ATTR] = _encode_string_array(
                report.keep_fast_instances
            )
            inner.attributes[FUNC_TIMING_RECLAIM_INSTANCES_ATTR] = _encode_string_array(
                report.reclaim_instances
            )
            inner.attributes[FUNC_TIMING_MAX_DELAY_ATTR] = StringAttr(f"{report.max_delay_ns:.4f}")
