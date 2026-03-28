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

from ..dialects.arith import (
    CompressorTreeOp,
    PartialProductGeneratorOp,
    PrefixTreeOp,
    decode_bit_map,
    decode_compressor_ops,
    decode_columns,
    decode_terms,
)
from ..dialects.logic import And2Op, FullAdderOp, HalfAdderOp, Or2Op, Xor2Op
from .lower_multiplier_to_arith_parts import _plan_compressor_tree


class LowerPartialProductGeneratorPattern(RewritePattern):
    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: PartialProductGeneratorOp, rewriter: PatternRewriter) -> None:
        new_ops = [
            And2Op(
                instance_name=f"ppg_and2_{index}",
                region_kind="partial_product_generator",
                output=output,
                lhs=lhs,
                rhs=rhs,
            )
            for index, (output, lhs, rhs) in enumerate(decode_terms(op.terms))
        ]
        rewriter.replace_matched_op(new_ops, safe_erase=True)


class LowerCompressorTreeToLogicPattern(RewritePattern):
    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: CompressorTreeOp, rewriter: PatternRewriter) -> None:
        new_ops: list[FullAdderOp | HalfAdderOp] = []
        if "stages" in op.properties:
            stage_ops = decode_compressor_ops(op.stages)
        else:
            stage_ops, _, _ = _plan_compressor_tree(decode_columns(op.columns))
        for kind, instance_name, lhs, rhs, cin, sum_out, carry_out in stage_ops:
            if kind == "fa":
                new_ops.append(
                    FullAdderOp(
                        instance_name=instance_name,
                        region_kind="compressor_tree",
                        sum_out=sum_out,
                        carry_out=carry_out,
                        lhs=lhs,
                        rhs=rhs,
                        cin=cin,
                    )
                )
                continue
            if kind == "ha":
                new_ops.append(
                    HalfAdderOp(
                        instance_name=instance_name,
                        region_kind="compressor_tree",
                        sum_out=sum_out,
                        carry_out=carry_out,
                        lhs=lhs,
                        rhs=rhs,
                    )
                )
                continue
            raise AssertionError(f"Unsupported compressor op kind {kind!r}")
        rewriter.replace_matched_op(new_ops, safe_erase=True)


class LowerPrefixTreeToLogicPattern(RewritePattern):
    def _lower_ripple(self, op: PrefixTreeOp) -> list[FullAdderOp]:
        lhs_row = decode_bit_map(op.lhs_row)
        rhs_row = decode_bit_map(op.rhs_row)
        max_bit = max(set(lhs_row) | set(rhs_row), default=-1)
        new_ops: list[FullAdderOp] = []
        for bit in range(max_bit + 1):
            cin = "1'b0" if bit == 0 else f"pt_carry_{bit}"
            carry_out = f"pt_overflow_{bit + 1}" if bit == max_bit else f"pt_carry_{bit + 1}"
            new_ops.append(
                FullAdderOp(
                    instance_name=f"pt_b{bit}_fa",
                    region_kind="prefix_tree",
                    sum_out=f"{op.output_name.data}[{bit}]",
                    carry_out=carry_out,
                    lhs=lhs_row.get(bit, "1'b0"),
                    rhs=rhs_row.get(bit, "1'b0"),
                    cin=cin,
                )
            )
        return new_ops

    def _lower_kogge_stone(
        self, op: PrefixTreeOp
    ) -> list[And2Op | Or2Op | Xor2Op]:
        lhs_row = decode_bit_map(op.lhs_row)
        rhs_row = decode_bit_map(op.rhs_row)
        max_bit = max(set(lhs_row) | set(rhs_row), default=-1)
        if max_bit < 0:
            return []

        new_ops: list[And2Op | Or2Op | Xor2Op] = []
        propagate: dict[int, str] = {}
        current_generate: dict[int, str] = {}
        current_propagate: dict[int, str] = {}

        for bit in range(max_bit + 1):
            lhs = lhs_row.get(bit, "1'b0")
            rhs = rhs_row.get(bit, "1'b0")
            propagate_wire = f"pt_p_{bit}"
            generate_wire = f"pt_g_{bit}"
            new_ops.append(
                Xor2Op(
                    instance_name=f"pt_b{bit}_xor_p",
                    region_kind="prefix_tree",
                    output=propagate_wire,
                    lhs=lhs,
                    rhs=rhs,
                )
            )
            new_ops.append(
                And2Op(
                    instance_name=f"pt_b{bit}_and_g",
                    region_kind="prefix_tree",
                    output=generate_wire,
                    lhs=lhs,
                    rhs=rhs,
                )
            )
            propagate[bit] = propagate_wire
            current_propagate[bit] = propagate_wire
            current_generate[bit] = generate_wire

        span = 1
        stage = 0
        while span <= max_bit:
            next_propagate = dict(current_propagate)
            next_generate = dict(current_generate)
            for bit in range(span, max_bit + 1):
                merged_propagate = f"pt_s{stage}_p_{bit}"
                merged_generate_and = f"pt_s{stage}_gand_{bit}"
                merged_generate = f"pt_s{stage}_g_{bit}"
                new_ops.append(
                    And2Op(
                        instance_name=f"pt_s{stage}_and_p_{bit}",
                        region_kind="prefix_tree",
                        output=merged_propagate,
                        lhs=current_propagate[bit],
                        rhs=current_propagate[bit - span],
                    )
                )
                new_ops.append(
                    And2Op(
                        instance_name=f"pt_s{stage}_and_g_{bit}",
                        region_kind="prefix_tree",
                        output=merged_generate_and,
                        lhs=current_propagate[bit],
                        rhs=current_generate[bit - span],
                    )
                )
                new_ops.append(
                    Or2Op(
                        instance_name=f"pt_s{stage}_or_g_{bit}",
                        region_kind="prefix_tree",
                        output=merged_generate,
                        lhs=current_generate[bit],
                        rhs=merged_generate_and,
                    )
                )
                next_propagate[bit] = merged_propagate
                next_generate[bit] = merged_generate
            current_propagate = next_propagate
            current_generate = next_generate
            span <<= 1
            stage += 1

        for bit in range(max_bit + 1):
            carry_in = "1'b0" if bit == 0 else current_generate[bit - 1]
            new_ops.append(
                Xor2Op(
                    instance_name=f"pt_b{bit}_xor_sum",
                    region_kind="prefix_tree",
                    output=f"{op.output_name.data}[{bit}]",
                    lhs=propagate[bit],
                    rhs=carry_in,
                )
            )
        return new_ops

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: PrefixTreeOp, rewriter: PatternRewriter) -> None:
        if op.implementation.data == "ripple":
            new_ops = self._lower_ripple(op)
        elif op.implementation.data == "kogge_stone":
            new_ops = self._lower_kogge_stone(op)
        else:
            raise AssertionError(f"Unsupported prefix tree implementation {op.implementation.data!r}")
        rewriter.replace_matched_op(new_ops, safe_erase=True)


@dataclass(frozen=True)
class LowerArithToLogicPass(ModulePass):
    name = "lower-arith-to-logic"

    def apply(self, ctx: Context, op: ModuleOp) -> None:
        del ctx
        PatternRewriteWalker(
            LowerPartialProductGeneratorPattern(),
            apply_recursively=True,
        ).rewrite_module(op)
        PatternRewriteWalker(
            LowerCompressorTreeToLogicPattern(),
            apply_recursively=True,
        ).rewrite_module(op)
        PatternRewriteWalker(
            LowerPrefixTreeToLogicPattern(),
            apply_recursively=True,
        ).rewrite_module(op)
