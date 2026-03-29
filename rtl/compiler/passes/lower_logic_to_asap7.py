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

from ..dialects.asap7 import (
    And2Op as Asap7And2Op,
    Ao21Op as Asap7Ao21Op,
    Or2Op as Asap7Or2Op,
    Xor2Op as Asap7Xor2Op,
)
from ..dialects.logic import And2Op, Ao21Op, FullAdderOp, HalfAdderOp, Or2Op, Xor2Op
from ..ir import require_wire_name


class LowerAnd2Pattern(RewritePattern):
    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: And2Op, rewriter: PatternRewriter) -> None:
        if op.region_kind.data not in {"partial_product_generator", "prefix_tree"}:
            return
        new_op = Asap7And2Op(
            instance_name=op.instance_name.data,
            output_name=require_wire_name(op.output),
            lhs=op.lhs,
            rhs=op.rhs,
            owner=op.region_kind.data,
        )
        rewriter.replace_matched_op(new_op, new_results=(new_op.output,), safe_erase=True)


class LowerOr2Pattern(RewritePattern):
    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: Or2Op, rewriter: PatternRewriter) -> None:
        if op.region_kind.data != "prefix_tree":
            return
        new_op = Asap7Or2Op(
            instance_name=op.instance_name.data,
            output_name=require_wire_name(op.output),
            lhs=op.lhs,
            rhs=op.rhs,
            owner=op.region_kind.data,
        )
        rewriter.replace_matched_op(new_op, new_results=(new_op.output,), safe_erase=True)


class LowerAo21Pattern(RewritePattern):
    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: Ao21Op, rewriter: PatternRewriter) -> None:
        if op.region_kind.data not in {"compressor_tree", "prefix_tree"}:
            return
        new_op = Asap7Ao21Op(
            instance_name=op.instance_name.data,
            output_name=require_wire_name(op.output),
            and_lhs=op.and_lhs,
            and_rhs=op.and_rhs,
            or_rhs=op.or_rhs,
            owner=op.region_kind.data,
        )
        rewriter.replace_matched_op(new_op, new_results=(new_op.output,), safe_erase=True)


class LowerXor2Pattern(RewritePattern):
    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: Xor2Op, rewriter: PatternRewriter) -> None:
        if op.region_kind.data != "prefix_tree":
            return
        new_op = Asap7Xor2Op(
            instance_name=op.instance_name.data,
            output_name=require_wire_name(op.output),
            lhs=op.lhs,
            rhs=op.rhs,
            owner=op.region_kind.data,
        )
        rewriter.replace_matched_op(new_op, new_results=(new_op.output,), safe_erase=True)


class LowerHalfAdderPattern(RewritePattern):
    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: HalfAdderOp, rewriter: PatternRewriter) -> None:
        if op.region_kind.data not in {"compressor_tree", "prefix_tree"}:
            return
        xor_op = Asap7Xor2Op(
            instance_name=f"{op.instance_name.data}_xor",
            output_name=require_wire_name(op.sum_out),
            lhs=op.lhs,
            rhs=op.rhs,
            owner=op.region_kind.data,
        )
        and_op = Asap7And2Op(
            instance_name=f"{op.instance_name.data}_and",
            output_name=require_wire_name(op.carry_out),
            lhs=op.lhs,
            rhs=op.rhs,
            owner=op.region_kind.data,
        )
        rewriter.replace_matched_op(
            [xor_op, and_op],
            new_results=(xor_op.output, and_op.output),
            safe_erase=True,
        )


class LowerFullAdderPattern(RewritePattern):
    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: FullAdderOp, rewriter: PatternRewriter) -> None:
        if op.region_kind.data not in {"compressor_tree", "prefix_tree"}:
            return
        ab_xor_name = f"{op.instance_name.data}_ab_xor"
        ab_and_name = f"{op.instance_name.data}_ab_and"
        xor_ab = Asap7Xor2Op(
            instance_name=f"{op.instance_name.data}_xor_ab",
            output_name=ab_xor_name,
            lhs=op.lhs,
            rhs=op.rhs,
            owner=op.region_kind.data,
        )
        xor_sum = Asap7Xor2Op(
            instance_name=f"{op.instance_name.data}_xor_sum",
            output_name=require_wire_name(op.sum_out),
            lhs=xor_ab.output,
            rhs=op.cin,
            owner=op.region_kind.data,
        )
        and_ab = Asap7And2Op(
            instance_name=f"{op.instance_name.data}_and_ab",
            output_name=ab_and_name,
            lhs=op.lhs,
            rhs=op.rhs,
            owner=op.region_kind.data,
        )
        ao21_carry = Asap7Ao21Op(
            instance_name=f"{op.instance_name.data}_ao21_carry",
            output_name=require_wire_name(op.carry_out),
            and_lhs=xor_ab.output,
            and_rhs=op.cin,
            or_rhs=and_ab.output,
            owner=op.region_kind.data,
        )
        rewriter.replace_matched_op(
            [xor_ab, xor_sum, and_ab, ao21_carry],
            new_results=(xor_sum.output, ao21_carry.output),
            safe_erase=True,
        )


@dataclass(frozen=True)
class LowerLogicToAsap7Pass(ModulePass):
    name = "lower-logic-to-asap7"

    def apply(self, ctx: Context, op: ModuleOp) -> None:
        del ctx
        PatternRewriteWalker(LowerAnd2Pattern(), apply_recursively=True).rewrite_module(op)
        PatternRewriteWalker(LowerOr2Pattern(), apply_recursively=True).rewrite_module(op)
        PatternRewriteWalker(LowerAo21Pattern(), apply_recursively=True).rewrite_module(op)
        PatternRewriteWalker(LowerXor2Pattern(), apply_recursively=True).rewrite_module(op)
        PatternRewriteWalker(LowerHalfAdderPattern(), apply_recursively=True).rewrite_module(op)
        PatternRewriteWalker(LowerFullAdderPattern(), apply_recursively=True).rewrite_module(op)
