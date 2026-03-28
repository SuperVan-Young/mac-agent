"""xDSL pass that lowers arith structural regions into logic ops."""

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
from ..dialects.logic import FullAdderOp, HalfAdderOp


class LowerCompressorTreeToLogicPattern(RewritePattern):
    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: CompressorTreeOp, rewriter: PatternRewriter) -> None:
        columns = decode_columns(op.columns)
        region_kind = "compressor_tree"
        new_ops: list[FullAdderOp | HalfAdderOp] = []
        for column, signals in sorted(columns.items()):
            if len(signals) >= 3:
                new_ops.append(
                    FullAdderOp(
                        instance_name=f"ct_c{column}_fa",
                        region_kind=region_kind,
                        sum_out=f"ct_c{column}_sum",
                        carry_out=f"ct_c{column + 1}_carry",
                        lhs=signals[0],
                        rhs=signals[1],
                        cin=signals[2],
                    )
                )
            elif len(signals) == 2:
                new_ops.append(
                    HalfAdderOp(
                        instance_name=f"ct_c{column}_ha",
                        region_kind=region_kind,
                        sum_out=f"ct_c{column}_sum",
                        carry_out=f"ct_c{column + 1}_carry",
                        lhs=signals[0],
                        rhs=signals[1],
                    )
                )
        rewriter.replace_matched_op(new_ops, safe_erase=True)


@dataclass(frozen=True)
class LowerArithToLogicPass(ModulePass):
    name = "lower-arith-to-logic"

    def apply(self, ctx: Context, op: ModuleOp) -> None:
        del ctx
        PatternRewriteWalker(
            LowerCompressorTreeToLogicPattern(),
            apply_recursively=True,
        ).rewrite_module(op)
