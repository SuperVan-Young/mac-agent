"""xDSL pass that lowers logic ops into asap7 ops."""

from __future__ import annotations

from dataclasses import dataclass

from xdsl.context import Context
from xdsl.dialects.builtin import ModuleOp
from xdsl.passes import ModulePass
from xdsl.pattern_rewriter import (
    PatternRewriter,
    PatternRewriteWalker,
    RewritePattern,
    op_type_rewrite_pattern,
)

from ..dialects.asap7 import FullAdderOp as Asap7FullAdderOp, HalfAdderOp as Asap7HalfAdderOp
from ..dialects.logic import FullAdderOp, HalfAdderOp


class LowerHalfAdderPattern(RewritePattern):
    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: HalfAdderOp, rewriter: PatternRewriter) -> None:
        if op.region_kind.data != "compressor_tree":
            return
        rewriter.replace_matched_op(
            [
                Asap7HalfAdderOp(
                    instance_name=op.instance_name.data,
                    impl_type="xor_and",
                    region_kind=op.region_kind.data,
                    sum_out=op.sum_out.data,
                    carry_out=op.carry_out.data,
                    lhs=op.lhs.data,
                    rhs=op.rhs.data,
                )
            ],
            safe_erase=True,
        )


class LowerFullAdderPattern(RewritePattern):
    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: FullAdderOp, rewriter: PatternRewriter) -> None:
        if op.region_kind.data != "compressor_tree":
            return
        rewriter.replace_matched_op(
            [
                Asap7FullAdderOp(
                    instance_name=op.instance_name.data,
                    impl_type="xor3_and2",
                    region_kind=op.region_kind.data,
                    sum_out=op.sum_out.data,
                    carry_out=op.carry_out.data,
                    lhs=op.lhs.data,
                    rhs=op.rhs.data,
                    cin=op.cin.data,
                )
            ],
            safe_erase=True,
        )


@dataclass(frozen=True)
class LowerLogicToAsap7Pass(ModulePass):
    name = "lower-logic-to-asap7"

    def apply(self, ctx: Context, op: ModuleOp) -> None:
        del ctx
        PatternRewriteWalker(LowerHalfAdderPattern(), apply_recursively=True).rewrite_module(op)
        PatternRewriteWalker(LowerFullAdderPattern(), apply_recursively=True).rewrite_module(op)
