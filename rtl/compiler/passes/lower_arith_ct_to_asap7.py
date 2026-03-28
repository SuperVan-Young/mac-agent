"""Deprecated direct xDSL pass from arith.compressor_tree to asap7 ops."""

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

from ..dialects.arith.xdsl import CompressorTreeOp, decode_columns
from ..dialects.asap7.xdsl import And2Op, Xor2Op


class LowerCompressorTreePattern(RewritePattern):
    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: CompressorTreeOp, rewriter: PatternRewriter) -> None:
        columns = decode_columns(op.columns)
        owner = op.owner.data
        new_ops: list[Xor2Op | And2Op] = []
        for column, signals in sorted(columns.items()):
            if len(signals) < 2:
                continue
            lhs = signals[0]
            rhs = signals[1]
            new_ops.append(
                Xor2Op(
                    instance_name=f"ct_c{column}_sum",
                    output=f"ct_c{column}_sum",
                    lhs=lhs,
                    rhs=rhs,
                    owner=owner,
                )
            )
            new_ops.append(
                And2Op(
                    instance_name=f"ct_c{column}_carry",
                    output=f"ct_c{column + 1}_carry",
                    lhs=lhs,
                    rhs=rhs,
                    owner=owner,
                )
            )
        rewriter.replace_matched_op(new_ops, safe_erase=True)


@dataclass(frozen=True)
class LowerArithCompressorTreeToAsap7Pass(ModulePass):
    name = "lower-arith-ct-to-asap7"

    def apply(self, ctx: Context, op: ModuleOp) -> None:
        del ctx
        PatternRewriteWalker(
            LowerCompressorTreePattern(),
            apply_recursively=True,
        ).rewrite_module(op)
