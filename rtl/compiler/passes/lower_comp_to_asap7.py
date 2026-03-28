"""xDSL pass that lowers comp ops into asap7 ops."""

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

from ..dialects.asap7.xdsl import And2Op, Xor2Op
from ..dialects.comp.xdsl import FullAdderOp, HalfAdderOp


class LowerHalfAdderPattern(RewritePattern):
    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: HalfAdderOp, rewriter: PatternRewriter) -> None:
        rewriter.replace_matched_op(
            [
                Xor2Op(
                    instance_name=f"{op.instance_name.data}_sum",
                    output=op.sum_out.data,
                    lhs=op.lhs.data,
                    rhs=op.rhs.data,
                    owner=op.owner.data,
                ),
                And2Op(
                    instance_name=f"{op.instance_name.data}_carry",
                    output=op.carry_out.data,
                    lhs=op.lhs.data,
                    rhs=op.rhs.data,
                    owner=op.owner.data,
                ),
            ],
            safe_erase=True,
        )


class LowerFullAdderPattern(RewritePattern):
    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: FullAdderOp, rewriter: PatternRewriter) -> None:
        # Minimal structural lowering: use two XOR2s to form parity and one AND2 as carry placeholder.
        # This is enough to exercise the comp -> asap7 rewrite boundary without flattening earlier IR.
        rewriter.replace_matched_op(
            [
                Xor2Op(
                    instance_name=f"{op.instance_name.data}_xor0",
                    output=f"{op.instance_name.data}_parity",
                    lhs=op.lhs.data,
                    rhs=op.rhs.data,
                    owner=op.owner.data,
                ),
                Xor2Op(
                    instance_name=f"{op.instance_name.data}_xor1",
                    output=op.sum_out.data,
                    lhs=f"{op.instance_name.data}_parity",
                    rhs=op.cin.data,
                    owner=op.owner.data,
                ),
                And2Op(
                    instance_name=f"{op.instance_name.data}_carry",
                    output=op.carry_out.data,
                    lhs=op.lhs.data,
                    rhs=op.rhs.data,
                    owner=op.owner.data,
                ),
            ],
            safe_erase=True,
        )


@dataclass(frozen=True)
class LowerCompToAsap7Pass(ModulePass):
    name = "lower-comp-to-asap7"

    def apply(self, ctx: Context, op: ModuleOp) -> None:
        del ctx
        PatternRewriteWalker(LowerHalfAdderPattern(), apply_recursively=True).rewrite_module(op)
        PatternRewriteWalker(LowerFullAdderPattern(), apply_recursively=True).rewrite_module(op)
