"""xDSL pass that lowers arith structural regions into hierarchical logic ops."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import re

from xdsl.context import Context
from xdsl.dialects.builtin import ModuleOp, StringAttr
from xdsl.dialects.func import FuncOp, ReturnOp
from xdsl.ir import Block, Region, SSAValue
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
    ConstantOp,
    FullAdderOp,
    HalfAdderOp,
    InputPortOp,
    InstanceOp,
    OutputPortOp,
    Xor2Op,
)
from ..ir import bit_wire_type, expand_signal_decl_refs
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


class _LogicRegionBuilder:
    def __init__(self, input_ports: list[SignalDecl], output_ports: list[SignalDecl]) -> None:
        self.input_ports = input_ports
        self.output_ports = output_ports
        self.ops: list = []
        self.values: dict[str, SSAValue] = {}
        self.constants: dict[str, SSAValue] = {}
        self._seed_inputs()

    def _seed_inputs(self) -> None:
        for signal in self.input_ports:
            for ref in expand_signal_decl_refs(signal):
                op = InputPortOp(port_name=ref, wire_type=bit_wire_type())
                self.ops.append(op)
                self.values[ref] = op.output

    def get(self, signal: str) -> SSAValue:
        if signal in self.values:
            return self.values[signal]
        if not _is_literal(signal):
            raise AssertionError(f"Unknown logic signal reference {signal!r}")
        const = self.constants.get(signal)
        if const is not None:
            return const
        op = ConstantOp(value=signal, wire_type=bit_wire_type())
        self.ops.append(op)
        self.constants[signal] = op.output
        return op.output

    def bind(self, signal: str, value: SSAValue) -> None:
        self.values[signal] = value

    def finish(self) -> list:
        for signal in self.output_ports:
            for ref in expand_signal_decl_refs(signal):
                self.ops.append(OutputPortOp(port_name=ref, value=self.get(ref)))
        return [*self.ops, ReturnOp()]


def _make_logic_region_func(
    *,
    func_name: str,
    region_kind: str,
    input_ports: list[SignalDecl],
    output_ports: list[SignalDecl],
    body_ops: list,
) -> FuncOp:
    body = Region(Block(body_ops))
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
        input_ports, output_ports = _build_partial_product_generator_ports(self.module, terms)
        builder = _LogicRegionBuilder(input_ports, output_ports)
        for index, (output, lhs, rhs) in enumerate(terms):
            and2 = And2Op(
                instance_name=f"ppg_and2_{index}",
                region_kind="partial_product_generator",
                output_name=output,
                lhs=builder.get(lhs),
                rhs=builder.get(rhs),
            )
            builder.ops.append(and2)
            builder.bind(output, and2.output)
        func_name, instance_name = self.name_allocator.allocate(op.owner.data)
        func_op = _make_logic_region_func(
            func_name=func_name,
            region_kind=op.owner.data,
            input_ports=input_ports,
            output_ports=output_ports,
            body_ops=builder.finish(),
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
        input_ports, output_ports = _build_compressor_tree_ports(self.module, columns, stage_ops)
        builder = _LogicRegionBuilder(input_ports, output_ports)
        for kind, instance_name, lhs, rhs, cin, sum_out, carry_out in stage_ops:
            if kind == "fa":
                fa = FullAdderOp(
                    instance_name=instance_name,
                    region_kind="compressor_tree",
                    sum_name=sum_out,
                    carry_name=carry_out,
                    lhs=builder.get(lhs),
                    rhs=builder.get(rhs),
                    cin=builder.get(cin),
                )
                builder.ops.append(fa)
                builder.bind(sum_out, fa.sum_out)
                builder.bind(carry_out, fa.carry_out)
                continue
            if kind == "ha":
                ha = HalfAdderOp(
                    instance_name=instance_name,
                    region_kind="compressor_tree",
                    sum_name=sum_out,
                    carry_name=carry_out,
                    lhs=builder.get(lhs),
                    rhs=builder.get(rhs),
                )
                builder.ops.append(ha)
                builder.bind(sum_out, ha.sum_out)
                builder.bind(carry_out, ha.carry_out)
                continue
            raise AssertionError(f"Unsupported compressor op kind {kind!r}")
        func_name, instance_name = self.name_allocator.allocate(op.owner.data)
        func_op = _make_logic_region_func(
            func_name=func_name,
            region_kind=op.owner.data,
            input_ports=input_ports,
            output_ports=output_ports,
            body_ops=builder.finish(),
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

    def _lower_ripple(self, op: PrefixTreeOp, builder: _LogicRegionBuilder) -> None:
        lhs_row = decode_bit_map(op.lhs_row)
        rhs_row = decode_bit_map(op.rhs_row)
        max_bit = max(set(lhs_row) | set(rhs_row), default=-1)
        for bit in range(max_bit + 1):
            cin_name = "1'b0" if bit == 0 else f"pt_carry_{bit}"
            carry_out = f"pt_overflow_{bit + 1}" if bit == max_bit else f"pt_carry_{bit + 1}"
            fa = FullAdderOp(
                instance_name=f"pt_b{bit}_fa",
                region_kind="prefix_tree",
                sum_name=f"{op.output_name.data}[{bit}]",
                carry_name=carry_out,
                lhs=builder.get(lhs_row.get(bit, "1'b0")),
                rhs=builder.get(rhs_row.get(bit, "1'b0")),
                cin=builder.get(cin_name),
            )
            builder.ops.append(fa)
            builder.bind(f"{op.output_name.data}[{bit}]", fa.sum_out)
            builder.bind(carry_out, fa.carry_out)

    def _lower_kogge_stone(self, op: PrefixTreeOp, builder: _LogicRegionBuilder) -> None:
        lhs_row = decode_bit_map(op.lhs_row)
        rhs_row = decode_bit_map(op.rhs_row)
        max_bit = max(set(lhs_row) | set(rhs_row), default=-1)
        if max_bit < 0:
            return

        propagate: dict[int, SSAValue] = {}
        current_generate: dict[int, SSAValue] = {}
        current_propagate: dict[int, SSAValue] = {}

        for bit in range(max_bit + 1):
            lhs = builder.get(lhs_row.get(bit, "1'b0"))
            rhs = builder.get(rhs_row.get(bit, "1'b0"))
            propagate_wire = f"pt_p_{bit}"
            generate_wire = f"pt_g_{bit}"
            xor_p = Xor2Op(
                instance_name=f"pt_b{bit}_xor_p",
                region_kind="prefix_tree",
                output_name=propagate_wire,
                lhs=lhs,
                rhs=rhs,
            )
            and_g = And2Op(
                instance_name=f"pt_b{bit}_and_g",
                region_kind="prefix_tree",
                output_name=generate_wire,
                lhs=lhs,
                rhs=rhs,
            )
            builder.ops.extend([xor_p, and_g])
            propagate[bit] = xor_p.output
            current_propagate[bit] = xor_p.output
            current_generate[bit] = and_g.output
            builder.bind(propagate_wire, xor_p.output)
            builder.bind(generate_wire, and_g.output)

        span = 1
        stage = 0
        while span <= max_bit:
            next_propagate = dict(current_propagate)
            next_generate = dict(current_generate)
            for bit in range(span, max_bit + 1):
                merged_propagate = f"pt_s{stage}_p_{bit}"
                merged_generate = f"pt_s{stage}_g_{bit}"
                and_p = And2Op(
                    instance_name=f"pt_s{stage}_and_p_{bit}",
                    region_kind="prefix_tree",
                    output_name=merged_propagate,
                    lhs=current_propagate[bit],
                    rhs=current_propagate[bit - span],
                )
                ao21_g = Ao21Op(
                    instance_name=f"pt_s{stage}_ao21_g_{bit}",
                    region_kind="prefix_tree",
                    output_name=merged_generate,
                    and_lhs=current_propagate[bit],
                    and_rhs=current_generate[bit - span],
                    or_rhs=current_generate[bit],
                )
                builder.ops.extend([and_p, ao21_g])
                next_propagate[bit] = and_p.output
                next_generate[bit] = ao21_g.output
                builder.bind(merged_propagate, and_p.output)
                builder.bind(merged_generate, ao21_g.output)
            current_propagate = next_propagate
            current_generate = next_generate
            span <<= 1
            stage += 1

        for bit in range(max_bit + 1):
            carry_in = builder.get("1'b0") if bit == 0 else current_generate[bit - 1]
            xor_sum = Xor2Op(
                instance_name=f"pt_b{bit}_xor_sum",
                region_kind="prefix_tree",
                output_name=f"{op.output_name.data}[{bit}]",
                lhs=propagate[bit],
                rhs=carry_in,
            )
            builder.ops.append(xor_sum)
            builder.bind(f"{op.output_name.data}[{bit}]", xor_sum.output)

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: PrefixTreeOp, rewriter: PatternRewriter) -> None:
        lhs_row = decode_bit_map(op.lhs_row)
        rhs_row = decode_bit_map(op.rhs_row)
        input_ports, output_ports = _build_prefix_tree_ports(
            self.module,
            lhs_row,
            rhs_row,
            op.output_name.data,
        )
        builder = _LogicRegionBuilder(input_ports, output_ports)
        if op.implementation.data == "ripple":
            self._lower_ripple(op, builder)
        elif op.implementation.data == "kogge_stone":
            self._lower_kogge_stone(op, builder)
        else:
            raise AssertionError(f"Unsupported prefix tree implementation {op.implementation.data!r}")
        func_name, instance_name = self.name_allocator.allocate(op.owner.data)
        func_op = _make_logic_region_func(
            func_name=func_name,
            region_kind=op.owner.data,
            input_ports=input_ports,
            output_ports=output_ports,
            body_ops=builder.finish(),
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
