"""Region-scoped ASAP7 cell sizing heuristics."""

from __future__ import annotations

from dataclasses import dataclass

from xdsl.context import Context
from xdsl.dialects.builtin import ArrayAttr, ModuleOp, StringAttr
from xdsl.dialects.func import FuncOp
from xdsl.passes import ModulePass

from ..analysis import (
    FUNC_TIMING_KEEP_FAST_INSTANCES_ATTR,
    FUNC_TIMING_RECLAIM_INSTANCES_ATTR,
)
from ..dialects.asap7 import Ao21Op, Xor2Op


_LOGIC_REGION_KIND_ATTR = "logic.region_kind"
_PREFIX_REGION_KIND = "arith.prefix_tree"
_COMPRESSOR_REGION_KIND = "arith.compressor_tree"


def _set_cell(op: Xor2Op | Ao21Op, cell: str) -> None:
    op.properties["cell"] = StringAttr(cell)


def _read_keep_fast_instances(func_op: FuncOp) -> set[str]:
    attr = func_op.attributes.get(FUNC_TIMING_KEEP_FAST_INSTANCES_ATTR)
    if not isinstance(attr, ArrayAttr):
        return set()
    return {
        item.data
        for item in attr
        if isinstance(item, StringAttr)
    }


def _read_reclaim_instances(func_op: FuncOp) -> set[str]:
    attr = func_op.attributes.get(FUNC_TIMING_RECLAIM_INSTANCES_ATTR)
    if not isinstance(attr, ArrayAttr):
        return set()
    return {
        item.data
        for item in attr
        if isinstance(item, StringAttr)
    }


def _size_prefix_region(
    func_op: FuncOp,
    keep_fast_instances: set[str],
    reclaim_instances: set[str],
) -> None:
    for op in func_op.body.block.ops:
        if isinstance(op, Xor2Op):
            if op.instance_name.data in keep_fast_instances:
                continue
            if reclaim_instances and op.instance_name.data not in reclaim_instances:
                continue
            _set_cell(op, "XOR2xp5_ASAP7_75t_R")
            continue
        if isinstance(op, Ao21Op):
            if op.instance_name.data in keep_fast_instances:
                continue
            if reclaim_instances and op.instance_name.data not in reclaim_instances:
                continue
            _set_cell(op, "AO21x1_ASAP7_75t_R")


def _size_compressor_region(
    func_op: FuncOp,
    keep_fast_instances: set[str],
    reclaim_instances: set[str],
) -> None:
    for op in func_op.body.block.ops:
        if not isinstance(op, Xor2Op):
            continue
        if op.instance_name.data in keep_fast_instances:
            continue
        if reclaim_instances and op.instance_name.data not in reclaim_instances:
            continue
        _set_cell(op, "XOR2xp5_ASAP7_75t_R")


@dataclass(frozen=True)
class RegionScopedCellSizingPass(ModulePass):
    name = "region-scoped-cell-sizing"

    def apply(self, ctx: Context, op: ModuleOp) -> None:
        del ctx
        for inner in op.ops:
            if not isinstance(inner, FuncOp):
                continue
            keep_fast_instances = _read_keep_fast_instances(inner)
            reclaim_instances = _read_reclaim_instances(inner)
            region_kind_attr = inner.attributes.get(_LOGIC_REGION_KIND_ATTR)
            if not isinstance(region_kind_attr, StringAttr):
                continue
            if region_kind_attr.data == _PREFIX_REGION_KIND:
                _size_prefix_region(inner, keep_fast_instances, reclaim_instances)
                continue
            if region_kind_attr.data == _COMPRESSOR_REGION_KIND:
                _size_compressor_region(inner, keep_fast_instances, reclaim_instances)
