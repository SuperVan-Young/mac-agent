"""Expand arith.multiplier into PPG, compressor tree, and prefix tree regions."""

from __future__ import annotations

from dataclasses import dataclass

from xdsl.context import Context
from xdsl.dialects.builtin import ArrayAttr, ModuleOp, StringAttr
from xdsl.passes import ModulePass
from xdsl.pattern_rewriter import (
    PatternRewriter,
    PatternRewriteWalker,
    RewritePattern,
    op_type_rewrite_pattern,
)

from ..dialects.arith import (
    CompressorTreeOp,
    MultiplierOp,
    PartialProductGeneratorOp,
    PrefixTreeOp,
)
from ..signals import decode_signal_decls


def _read_module_ports(module: ModuleOp) -> tuple[list, list]:
    input_ports_attr = module.attributes.get("input_ports")
    output_ports_attr = module.attributes.get("output_ports")
    if not isinstance(input_ports_attr, ArrayAttr):
        raise AssertionError("builtin.module is missing array attribute 'input_ports'")
    if not isinstance(output_ports_attr, ArrayAttr):
        raise AssertionError("builtin.module is missing array attribute 'output_ports'")
    return decode_signal_decls(input_ports_attr), decode_signal_decls(output_ports_attr)


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
    def __init__(self, module: ModuleOp) -> None:
        super().__init__()
        self.module = module

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: MultiplierOp, rewriter: PatternRewriter) -> None:
        input_ports, output_ports = _read_module_ports(self.module)
        if len(input_ports) < 3 or not output_ports:
            raise AssertionError("arith.multiplier expects inputs A/B/C and one output")

        lhs_port = input_ports[0]
        rhs_port = input_ports[1]
        addend_port = input_ports[2]
        output_port = output_ports[0]

        ppg_terms: list[tuple[str, str, str]] = []
        columns: dict[int, list[str]] = {}
        for lhs_bit in range(lhs_port.width):
            for rhs_bit in range(rhs_port.width):
                column = lhs_bit + rhs_bit
                if column >= output_port.width:
                    continue
                output_name = f"pp_{lhs_bit}_{rhs_bit}"
                ppg_terms.append(
                    (
                        output_name,
                        f"{lhs_port.name}[{lhs_bit}]",
                        f"{rhs_port.name}[{rhs_bit}]",
                    )
                )
                columns.setdefault(column, []).append(output_name)

        for bit in range(min(addend_port.width, output_port.width)):
            columns.setdefault(bit, []).append(f"{addend_port.name}[{bit}]")

        _, lhs_row, rhs_row = _plan_compressor_tree(columns)

        rewriter.replace_matched_op(
            [
                PartialProductGeneratorOp(
                    implementation="and_grid",
                    terms=ppg_terms,
                    owner="arith.partial_product_generator",
                ),
                CompressorTreeOp(
                    reduction_type="dadda",
                    columns=columns,
                    owner="arith.compressor_tree",
                ),
                PrefixTreeOp(
                    implementation="kogge_stone",
                    lhs_row=lhs_row,
                    rhs_row=rhs_row,
                    output_name=output_port.name,
                    owner="arith.prefix_tree",
                ),
            ],
            safe_erase=True,
        )


@dataclass(frozen=True)
class LowerMultiplierToArithPartsPass(ModulePass):
    name = "lower-multiplier-to-arith-parts"

    def apply(self, ctx: Context, op: ModuleOp) -> None:
        del ctx
        PatternRewriteWalker(
            LowerMultiplierToArithPartsPattern(op),
            apply_recursively=True,
        ).rewrite_module(op)
