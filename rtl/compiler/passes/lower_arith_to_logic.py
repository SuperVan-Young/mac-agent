"""xDSL pass that lowers arith structural regions into hierarchical logic ops."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import re

from xdsl.context import Context
from xdsl.dialects.builtin import ModuleOp, StringAttr
from xdsl.dialects.func import FuncOp, ReturnOp
from xdsl.ir import Block, Region
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
    decode_columns,
    decode_compressor_ops,
    decode_terms,
)
from ..dialects.logic import (
    And2Op,
    Ao21Op,
    FullAdderOp,
    HalfAdderOp,
    InstanceOp,
    Xor2Op,
)
from ..signals import SignalDecl, encode_signal_decls
from .lower_multiplier_to_arith_parts import _plan_compressor_tree, _read_module_ports


_BIT_SELECT_RE = re.compile(r"^(?P<base>[A-Za-z_]\w*)\[(?P<index>\d+)\]$")
_LOGIC_REGION_KIND_ATTR = "logic.region_kind"
_LOGIC_INPUT_PORTS_ATTR = "logic.input_ports"
_LOGIC_OUTPUT_PORTS_ATTR = "logic.output_ports"


def _read_top_name(module: ModuleOp) -> str:
    func_name_attr = module.attributes.get("func_name")
    if not isinstance(func_name_attr, StringAttr):
        raise AssertionError("builtin.module is missing string attribute 'func_name'")
    return func_name_attr.data


def _short_region_kind(region_kind: str) -> str:
    return region_kind.rsplit(".", 1)[-1]


def _is_literal(signal: str) -> bool:
    return "'" in signal or signal.isdigit()


def _build_known_widths(module: ModuleOp) -> dict[str, int]:
    input_ports, output_ports = _read_module_ports(module)
    return {signal.name: signal.width for signal in input_ports + output_ports}


def _build_port_decls(
    signals: list[str],
    *,
    kind: str,
    known_widths: dict[str, int],
) -> list[SignalDecl]:
    order: list[str] = []
    widths: dict[str, int] = {}
    for signal in signals:
        if _is_literal(signal):
            continue
        match = _BIT_SELECT_RE.match(signal)
        if match is not None:
            base = match.group("base")
            width = known_widths.get(base, int(match.group("index")) + 1)
        else:
            base = signal
            width = known_widths.get(base, 1)
        if base not in widths:
            order.append(base)
            widths[base] = width
            continue
        widths[base] = max(widths[base], width)
    return [SignalDecl(name=name, width=widths[name], kind=kind) for name in order]


def _make_logic_region_func(
    *,
    func_name: str,
    region_kind: str,
    input_ports: list[SignalDecl],
    output_ports: list[SignalDecl],
    body_ops: list,
) -> FuncOp:
    body = Region(Block([*body_ops, ReturnOp()]))
    func_op = FuncOp(func_name, ((), ()), region=body, visibility="private")
    func_op.attributes[_LOGIC_REGION_KIND_ATTR] = StringAttr(region_kind)
    func_op.attributes[_LOGIC_INPUT_PORTS_ATTR] = encode_signal_decls(input_ports)
    func_op.attributes[_LOGIC_OUTPUT_PORTS_ATTR] = encode_signal_decls(output_ports)
    return func_op


def _make_instance_op(
    *,
    instance_name: str,
    callee: str,
    region_kind: str,
    input_ports: list[SignalDecl],
    output_ports: list[SignalDecl],
) -> InstanceOp:
    return InstanceOp(
        instance_name=instance_name,
        callee=callee,
        region_kind=region_kind,
        input_connections=[(port.name, port.name) for port in input_ports],
        output_connections=[(port.name, port.name) for port in output_ports],
    )


def _build_partial_product_generator_ports(
    module: ModuleOp, terms: list[tuple[str, str, str]]
) -> tuple[list[SignalDecl], list[SignalDecl]]:
    known_widths = _build_known_widths(module)
    input_refs = [ref for _, lhs, rhs in terms for ref in (lhs, rhs)]
    output_refs = [output for output, _, _ in terms]
    return (
        _build_port_decls(input_refs, kind="input", known_widths=known_widths),
        _build_port_decls(output_refs, kind="output", known_widths=known_widths),
    )


def _build_compressor_tree_ports(
    module: ModuleOp,
    columns: dict[int, list[str]],
    stage_ops: list[tuple[str, str, str, str, str, str, str]],
) -> tuple[list[SignalDecl], list[SignalDecl]]:
    known_widths = _build_known_widths(module)
    input_refs = [signal for _, signals in sorted(columns.items()) for signal in signals]
    output_refs = [wire for _, _, _, _, _, sum_out, carry_out in stage_ops for wire in (sum_out, carry_out)]
    return (
        _build_port_decls(input_refs, kind="input", known_widths=known_widths),
        _build_port_decls(output_refs, kind="output", known_widths=known_widths),
    )


def _build_prefix_tree_ports(
    module: ModuleOp, lhs_row: dict[int, str], rhs_row: dict[int, str], output_name: str
) -> tuple[list[SignalDecl], list[SignalDecl]]:
    known_widths = _build_known_widths(module)
    input_refs = [signal for _, signal in sorted(lhs_row.items())] + [
        signal for _, signal in sorted(rhs_row.items())
    ]
    max_bit = max(set(lhs_row) | set(rhs_row), default=known_widths.get(output_name, 1) - 1)
    output_refs = [f"{output_name}[{bit}]" for bit in range(max_bit + 1)]
    return (
        _build_port_decls(input_refs, kind="input", known_widths=known_widths),
        _build_port_decls(output_refs, kind="output", known_widths=known_widths),
    )


class _NameAllocator:
    def __init__(self, top_name: str) -> None:
        self.top_name = top_name
        self.counters: dict[str, int] = defaultdict(int)

    def allocate(self, region_kind: str) -> tuple[str, str]:
        short_kind = _short_region_kind(region_kind)
        index = self.counters[short_kind]
        self.counters[short_kind] += 1
        return (
            f"{self.top_name}__{short_kind}_{index}",
            f"{short_kind}_{index}_inst",
        )


class LowerPartialProductGeneratorPattern(RewritePattern):
    def __init__(self, module: ModuleOp, name_allocator: _NameAllocator) -> None:
        super().__init__()
        self.module = module
        self.name_allocator = name_allocator

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: PartialProductGeneratorOp, rewriter: PatternRewriter) -> None:
        terms = decode_terms(op.terms)
        body_ops = [
            And2Op(
                instance_name=f"ppg_and2_{index}",
                region_kind="partial_product_generator",
                output=output,
                lhs=lhs,
                rhs=rhs,
            )
            for index, (output, lhs, rhs) in enumerate(terms)
        ]
        input_ports, output_ports = _build_partial_product_generator_ports(self.module, terms)
        func_name, instance_name = self.name_allocator.allocate(op.owner.data)
        func_op = _make_logic_region_func(
            func_name=func_name,
            region_kind=op.owner.data,
            input_ports=input_ports,
            output_ports=output_ports,
            body_ops=body_ops,
        )
        instance_op = _make_instance_op(
            instance_name=instance_name,
            callee=func_name,
            region_kind=op.owner.data,
            input_ports=input_ports,
            output_ports=output_ports,
        )
        rewriter.replace_matched_op([instance_op, func_op], safe_erase=True)


class LowerCompressorTreeToLogicPattern(RewritePattern):
    def __init__(self, module: ModuleOp, name_allocator: _NameAllocator) -> None:
        super().__init__()
        self.module = module
        self.name_allocator = name_allocator

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: CompressorTreeOp, rewriter: PatternRewriter) -> None:
        columns = decode_columns(op.columns)
        stage_ops = decode_compressor_ops(op.stages)
        if not stage_ops:
            stage_ops, _, _ = _plan_compressor_tree(columns)
        body_ops: list[FullAdderOp | HalfAdderOp] = []
        for kind, instance_name, lhs, rhs, cin, sum_out, carry_out in stage_ops:
            if kind == "fa":
                body_ops.append(
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
                body_ops.append(
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
        input_ports, output_ports = _build_compressor_tree_ports(self.module, columns, stage_ops)
        func_name, instance_name = self.name_allocator.allocate(op.owner.data)
        func_op = _make_logic_region_func(
            func_name=func_name,
            region_kind=op.owner.data,
            input_ports=input_ports,
            output_ports=output_ports,
            body_ops=body_ops,
        )
        instance_op = _make_instance_op(
            instance_name=instance_name,
            callee=func_name,
            region_kind=op.owner.data,
            input_ports=input_ports,
            output_ports=output_ports,
        )
        rewriter.replace_matched_op([instance_op, func_op], safe_erase=True)


class LowerPrefixTreeToLogicPattern(RewritePattern):
    def __init__(self, module: ModuleOp, name_allocator: _NameAllocator) -> None:
        super().__init__()
        self.module = module
        self.name_allocator = name_allocator

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

    def _lower_kogge_stone(self, op: PrefixTreeOp) -> list[And2Op | Ao21Op | Xor2Op]:
        lhs_row = decode_bit_map(op.lhs_row)
        rhs_row = decode_bit_map(op.rhs_row)
        max_bit = max(set(lhs_row) | set(rhs_row), default=-1)
        if max_bit < 0:
            return []

        new_ops: list[And2Op | Ao21Op | Xor2Op] = []
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
                    Ao21Op(
                        instance_name=f"pt_s{stage}_ao21_g_{bit}",
                        region_kind="prefix_tree",
                        output=merged_generate,
                        and_lhs=current_propagate[bit],
                        and_rhs=current_generate[bit - span],
                        or_rhs=current_generate[bit],
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
        lhs_row = decode_bit_map(op.lhs_row)
        rhs_row = decode_bit_map(op.rhs_row)
        if op.implementation.data == "ripple":
            body_ops = self._lower_ripple(op)
        elif op.implementation.data == "kogge_stone":
            body_ops = self._lower_kogge_stone(op)
        else:
            raise AssertionError(f"Unsupported prefix tree implementation {op.implementation.data!r}")
        input_ports, output_ports = _build_prefix_tree_ports(
            self.module,
            lhs_row,
            rhs_row,
            op.output_name.data,
        )
        func_name, instance_name = self.name_allocator.allocate(op.owner.data)
        func_op = _make_logic_region_func(
            func_name=func_name,
            region_kind=op.owner.data,
            input_ports=input_ports,
            output_ports=output_ports,
            body_ops=body_ops,
        )
        instance_op = _make_instance_op(
            instance_name=instance_name,
            callee=func_name,
            region_kind=op.owner.data,
            input_ports=input_ports,
            output_ports=output_ports,
        )
        rewriter.replace_matched_op([instance_op, func_op], safe_erase=True)


@dataclass(frozen=True)
class LowerArithToLogicPass(ModulePass):
    name = "lower-arith-to-logic"

    def apply(self, ctx: Context, op: ModuleOp) -> None:
        del ctx
        name_allocator = _NameAllocator(_read_top_name(op))
        PatternRewriteWalker(
            LowerPartialProductGeneratorPattern(op, name_allocator),
            apply_recursively=True,
        ).rewrite_module(op)
        PatternRewriteWalker(
            LowerCompressorTreeToLogicPattern(op, name_allocator),
            apply_recursively=True,
        ).rewrite_module(op)
        PatternRewriteWalker(
            LowerPrefixTreeToLogicPattern(op, name_allocator),
            apply_recursively=True,
        ).rewrite_module(op)
