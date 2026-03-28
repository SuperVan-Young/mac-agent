"""Region-scoped ASAP7 cell sizing heuristics."""

from __future__ import annotations

from dataclasses import dataclass
import re

from xdsl.context import Context
from xdsl.dialects.builtin import ModuleOp, StringAttr
from xdsl.dialects.func import FuncOp
from xdsl.passes import ModulePass

from ..dialects.asap7 import Ao21Op, Xor2Op


_LOGIC_REGION_KIND_ATTR = "logic.region_kind"
_PREFIX_REGION_KIND = "arith.prefix_tree"
_COMPRESSOR_REGION_KIND = "arith.compressor_tree"

_PREFIX_KEEP_MIN = 17
_PREFIX_KEEP_MAX = 21
_COMPRESSOR_KEEP_MIN = 13
_COMPRESSOR_KEEP_MAX = 22

_PREFIX_XOR_RE = re.compile(r"^pt_b(?P<bit>\d+)_xor_(?:p|sum)$")
_PREFIX_AO21_RE = re.compile(r"^pt_s\d+_ao21_g_(?P<bit>\d+)$")
_COMPRESSOR_COLUMN_RE = re.compile(r"_c(?P<column>\d+)_")


def _set_cell(op: Xor2Op | Ao21Op, cell: str) -> None:
    op.properties["cell"] = StringAttr(cell)


def _size_prefix_region(func_op: FuncOp) -> None:
    for op in func_op.body.block.ops:
        if isinstance(op, Xor2Op):
            match = _PREFIX_XOR_RE.match(op.instance_name.data)
            if match is None:
                continue
            bit = int(match.group("bit"))
            if _PREFIX_KEEP_MIN <= bit <= _PREFIX_KEEP_MAX:
                continue
            _set_cell(op, "XOR2xp5_ASAP7_75t_R")
            continue
        if isinstance(op, Ao21Op):
            match = _PREFIX_AO21_RE.match(op.instance_name.data)
            if match is None:
                continue
            bit = int(match.group("bit"))
            if _PREFIX_KEEP_MIN <= bit <= _PREFIX_KEEP_MAX:
                continue
            _set_cell(op, "AO21x1_ASAP7_75t_R")


def _size_compressor_region(func_op: FuncOp) -> None:
    for op in func_op.body.block.ops:
        if not isinstance(op, Xor2Op):
            continue
        match = _COMPRESSOR_COLUMN_RE.search(op.instance_name.data)
        if match is None:
            continue
        column = int(match.group("column"))
        if _COMPRESSOR_KEEP_MIN <= column <= _COMPRESSOR_KEEP_MAX:
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
            region_kind_attr = inner.attributes.get(_LOGIC_REGION_KIND_ATTR)
            if not isinstance(region_kind_attr, StringAttr):
                continue
            if region_kind_attr.data == _PREFIX_REGION_KIND:
                _size_prefix_region(inner)
                continue
            if region_kind_attr.data == _COMPRESSOR_REGION_KIND:
                _size_compressor_region(inner)
