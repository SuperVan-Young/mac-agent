"""xDSL pass that lowers logic ops into asap7 primitive cells."""

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

from ..dialects.asap7 import And2Op as Asap7And2Op, Or2Op as Asap7Or2Op, Xor2Op as Asap7Xor2Op
from ..dialects.logic import And2Op, FullAdderOp, HalfAdderOp


class LowerAnd2Pattern(RewritePattern):
    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: And2Op, rewriter: PatternRewriter) -> None:
        if op.region_kind.data != "partial_product_generator":
            return
        rewriter.replace_matched_op(
            [
                Asap7And2Op(
                    instance_name=op.instance_name.data,
                    output=op.output.data,
                    lhs=op.lhs.data,
                    rhs=op.rhs.data,
                    owner=op.region_kind.data,
                )
            ],
            safe_erase=True,
        )


class LowerHalfAdderPattern(RewritePattern):
    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: HalfAdderOp, rewriter: PatternRewriter) -> None:
        if op.region_kind.data not in {"compressor_tree", "prefix_tree"}:
            return
        rewriter.replace_matched_op(
            [
                Asap7Xor2Op(
                    instance_name=f"{op.instance_name.data}_xor",
                    output=op.sum_out.data,
                    lhs=op.lhs.data,
                    rhs=op.rhs.data,
                    owner=op.region_kind.data,
                ),
                Asap7And2Op(
                    instance_name=f"{op.instance_name.data}_and",
                    output=op.carry_out.data,
                    lhs=op.lhs.data,
                    rhs=op.rhs.data,
                    owner=op.region_kind.data,
                ),
            ],
            safe_erase=True,
        )


class LowerFullAdderPattern(RewritePattern):
    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: FullAdderOp, rewriter: PatternRewriter) -> None:
        if op.region_kind.data not in {"compressor_tree", "prefix_tree"}:
            return
        ab_xor = f"{op.instance_name.data}_ab_xor"
        ab_and = f"{op.instance_name.data}_ab_and"
        cin_and = f"{op.instance_name.data}_cin_and"
        rewriter.replace_matched_op(
            [
                Asap7Xor2Op(
                    instance_name=f"{op.instance_name.data}_xor_ab",
                    output=ab_xor,
                    lhs=op.lhs.data,
                    rhs=op.rhs.data,
                    owner=op.region_kind.data,
                ),
                Asap7Xor2Op(
                    instance_name=f"{op.instance_name.data}_xor_sum",
                    output=op.sum_out.data,
                    lhs=ab_xor,
                    rhs=op.cin.data,
                    owner=op.region_kind.data,
                ),
                Asap7And2Op(
                    instance_name=f"{op.instance_name.data}_and_ab",
                    output=ab_and,
                    lhs=op.lhs.data,
                    rhs=op.rhs.data,
                    owner=op.region_kind.data,
                ),
                Asap7And2Op(
                    instance_name=f"{op.instance_name.data}_and_cin",
                    output=cin_and,
                    lhs=ab_xor,
                    rhs=op.cin.data,
                    owner=op.region_kind.data,
                ),
                Asap7Or2Op(
                    instance_name=f"{op.instance_name.data}_or_carry",
                    output=op.carry_out.data,
                    lhs=ab_and,
                    rhs=cin_and,
                    owner=op.region_kind.data,
                ),
            ],
            safe_erase=True,
        )


@dataclass(frozen=True)
class LowerLogicToAsap7Pass(ModulePass):
    name = "lower-logic-to-asap7"

    def apply(self, ctx: Context, op: ModuleOp) -> None:
        del ctx
        PatternRewriteWalker(LowerAnd2Pattern(), apply_recursively=True).rewrite_module(op)
        PatternRewriteWalker(LowerHalfAdderPattern(), apply_recursively=True).rewrite_module(op)
        PatternRewriteWalker(LowerFullAdderPattern(), apply_recursively=True).rewrite_module(op)
