"""Expand arith.multiplier into SSA-connected PPG, compressor tree, and prefix tree ops."""

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
    CompressorTreeImplementation,
    MultiplierOp,
    PartialProductGeneratorOp,
    PartialProductGeneratorImplementation,
    PrefixTreeOp,
    PrefixTreeImplementation,
)
from ..ir import get_wire_width, require_wire_name, wire_type


def _build_dadda_targets(max_height: int) -> list[int]:
    targets = [2]
    while targets[-1] < max_height:
        targets.append((targets[-1] * 3) // 2)
    if targets[-1] >= max_height:
        targets.pop()
    return list(reversed(targets))


def _initial_arrival(signal: str) -> float:
    if signal.startswith("C["):
        return 0.0
    if signal.startswith("pp_"):
        return 1.0
    return 0.0


def _signal_sort_key(arrival: dict[str, float], signal: str) -> tuple[float, str]:
    return arrival.get(signal, 0.0), signal


def _estimate_half_adder_arrival(lhs_arrival: float, rhs_arrival: float) -> tuple[float, float]:
    base = max(lhs_arrival, rhs_arrival)
    return base + 2.0, base + 1.0


def _estimate_full_adder_arrival(
    lhs_arrival: float, rhs_arrival: float, cin_arrival: float
) -> tuple[float, float]:
    sum_arrival = max(lhs_arrival + 2.0, rhs_arrival + 2.0, cin_arrival + 1.0)
    carry_arrival = max(lhs_arrival + 1.5, rhs_arrival + 1.5, cin_arrival + 1.0)
    return sum_arrival, carry_arrival


def _plan_compressor_tree(
    columns: dict[int, list[str]],
) -> tuple[list[tuple[str, str, str, str, str, str, str]], dict[int, str], dict[int, str]]:
    planned_columns = {column: list(signals) for column, signals in columns.items()}
    max_height = max((len(signals) for signals in planned_columns.values()), default=0)
    stages: list[tuple[str, str, str, str, str, str, str]] = []
    arrival = {
        signal: _initial_arrival(signal)
        for signals in planned_columns.values()
        for signal in signals
    }

    for stage_index, target in enumerate(_build_dadda_targets(max_height)):
        for column in range(max(planned_columns) + 2):
            signals = planned_columns.setdefault(column, [])
            signals.sort(key=lambda signal: _signal_sort_key(arrival, signal))
            while len(signals) > target:
                excess = len(signals) - target
                if excess == 1:
                    lhs = signals.pop(0)
                    rhs = signals.pop(0)
                    sum_out = f"ct_s{stage_index}_c{column}_sum{len(stages)}"
                    carry_out = f"ct_s{stage_index}_c{column + 1}_carry{len(stages)}"
                    sum_arrival, carry_arrival = _estimate_half_adder_arrival(
                        arrival[lhs], arrival[rhs]
                    )
                    arrival[sum_out] = sum_arrival
                    arrival[carry_out] = carry_arrival
                    stages.append(
                        (
                            "ha",
                            f"ct_s{stage_index}_c{column}_ha{len(stages)}",
                            lhs,
                            rhs,
                            "",
                            sum_out,
                            carry_out,
                        )
                    )
                    signals.append(sum_out)
                    planned_columns.setdefault(column + 1, []).append(carry_out)
                    signals.sort(key=lambda signal: _signal_sort_key(arrival, signal))
                    continue

                chosen = [signals.pop(0), signals.pop(0), signals.pop(0)]
                chosen.sort(key=lambda signal: _signal_sort_key(arrival, signal))
                lhs, rhs, cin = chosen
                sum_out = f"ct_s{stage_index}_c{column}_sum{len(stages)}"
                carry_out = f"ct_s{stage_index}_c{column + 1}_carry{len(stages)}"
                sum_arrival, carry_arrival = _estimate_full_adder_arrival(
                    arrival[lhs], arrival[rhs], arrival[cin]
                )
                arrival[sum_out] = sum_arrival
                arrival[carry_out] = carry_arrival
                stages.append(
                    (
                        "fa",
                        f"ct_s{stage_index}_c{column}_fa{len(stages)}",
                        lhs,
                        rhs,
                        cin,
                        sum_out,
                        carry_out,
                    )
                )
                signals.append(sum_out)
                planned_columns.setdefault(column + 1, []).append(carry_out)
                signals.sort(key=lambda signal: _signal_sort_key(arrival, signal))

    lhs_row: dict[int, str] = {}
    rhs_row: dict[int, str] = {}
    for column, signals in sorted(planned_columns.items()):
        signals.sort(key=lambda signal: _signal_sort_key(arrival, signal))
        if len(signals) > 2:
            raise AssertionError(f"Compressor tree did not converge at column {column}: {signals}")
        if signals:
            lhs_row[column] = signals[0]
        if len(signals) == 2:
            rhs_row[column] = signals[1]
    return stages, lhs_row, rhs_row


class LowerMultiplierToArithPartsPattern(RewritePattern):
    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: MultiplierOp, rewriter: PatternRewriter) -> None:
        if len(op.inputs) != 3 or len(op.results) != 1:
            raise AssertionError("arith.multiplier expects three bus operands and one bus result")

        lhs_value, rhs_value, addend_value = op.inputs
        lhs_port = require_wire_name(lhs_value)
        rhs_port = require_wire_name(rhs_value)
        addend_port = require_wire_name(addend_value)
        if len(op.results) != 1:
            raise AssertionError("arith.multiplier currently expects a single bus result")
        output_port = require_wire_name(op.results[0]).split("[", 1)[0]
        output_width = get_wire_width(op.results[0])
        lhs_width = get_wire_width(lhs_value)
        rhs_width = get_wire_width(rhs_value)
        addend_width = get_wire_width(addend_value)

        columns: dict[int, list[str]] = {}
        ppg_output_names: list[str] = []
        for lhs_bit in range(lhs_width):
            for rhs_bit in range(rhs_width):
                column = lhs_bit + rhs_bit
                if column >= output_width:
                    continue
                pp_name = f"pp_{lhs_bit}_{rhs_bit}"
                ppg_output_names.append(pp_name)
                columns.setdefault(column, []).append(pp_name)

        for bit in range(min(addend_width, output_width)):
            columns.setdefault(bit, []).append(f"{addend_port}[{bit}]")

        compressor_output_names = ["ct_lhs", "ct_rhs"]
        prefix_output_names = [output_port]

        ppg = PartialProductGeneratorOp(
            implementation=PartialProductGeneratorImplementation.AND_GRID,
            inputs=[lhs_value, rhs_value],
            output_names=ppg_output_names,
            owner="arith.partial_product_generator",
        )
        compressor = CompressorTreeOp(
            implementation=CompressorTreeImplementation.DADDA,
            inputs=[*ppg.results, addend_value],
            output_names=compressor_output_names,
            output_types=[wire_type(output_width, name="ct_lhs"), wire_type(output_width, name="ct_rhs")],
            owner="arith.compressor_tree",
        )
        prefix = PrefixTreeOp(
            implementation=PrefixTreeImplementation.KOGGE_STONE,
            inputs=list(compressor.results),
            output_names=prefix_output_names,
            output_types=[wire_type(output_width, name=output_port)],
            owner="arith.prefix_tree",
        )

        if get_wire_width(prefix.results[0]) != output_width:
            raise AssertionError("arith.prefix_tree output width must match arith.multiplier results")
        rewriter.replace_matched_op(
            [ppg, compressor, prefix],
            new_results=tuple(prefix.results),
            safe_erase=True,
        )


@dataclass(frozen=True)
class LowerMultiplierToArithPartsPass(ModulePass):
    name = "lower-multiplier-to-arith-parts"

    def apply(self, ctx: Context, op: ModuleOp) -> None:
        del ctx
        PatternRewriteWalker(
            LowerMultiplierToArithPartsPattern(),
            apply_recursively=True,
        ).rewrite_module(op)
