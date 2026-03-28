"""xDSL pass that lowers arith.compressor_tree ops into comp ops."""

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

from ..dialects.arith import CompressorTreeOp, decode_columns
from ..dialects.comp import FullAdderOp, HalfAdderOp


class LowerCompressorTreeToCompPattern(RewritePattern):
    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: CompressorTreeOp, rewriter: PatternRewriter) -> None:
        columns = decode_columns(op.columns)
        owner = op.owner.data
        new_ops: list[FullAdderOp | HalfAdderOp] = []
        for column, signals in sorted(columns.items()):
            if len(signals) >= 3:
                new_ops.append(
                    FullAdderOp(
                        instance_name=f"ct_c{column}_fa",
                        sum_out=f"ct_c{column}_sum",
                        carry_out=f"ct_c{column + 1}_carry",
                        lhs=signals[0],
                        rhs=signals[1],
                        cin=signals[2],
                        owner=owner,
                    )
                )
            elif len(signals) == 2:
                new_ops.append(
                    HalfAdderOp(
                        instance_name=f"ct_c{column}_ha",
                        sum_out=f"ct_c{column}_sum",
                        carry_out=f"ct_c{column + 1}_carry",
                        lhs=signals[0],
                        rhs=signals[1],
                        owner=owner,
                    )
                )
        rewriter.replace_matched_op(new_ops, safe_erase=True)


@dataclass(frozen=True)
class LowerArithCompressorTreeToCompPass(ModulePass):
    name = "lower-arith-ct-to-comp"

    def apply(self, ctx: Context, op: ModuleOp) -> None:
        del ctx
        PatternRewriteWalker(
            LowerCompressorTreeToCompPattern(),
            apply_recursively=True,
        ).rewrite_module(op)
