"""xDSL pass that lowers arith structural regions into hierarchical logic ops."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import re

from xdsl.context import Context
from xdsl.dialects.builtin import ModuleOp, StringAttr
from xdsl.dialects.func import FuncOp, ReturnOp
from xdsl.ir import Operation, SSAValue
from xdsl.passes import ModulePass
from xdsl.pattern_rewriter import (
    PatternRewriter,
    PatternRewriteWalker,
    RewritePattern,
    op_type_rewrite_pattern,
)
from xdsl.rewriter import InsertPoint

from ..dialects.arith import (
    CompressorTreeOp,
    PartialProductGeneratorOp,
    PrefixTreeImplementation,
    PrefixTreeOp,
)
from ..dialects.logic import (
    And2Op,
    Ao21Op,
    ConstantOp,
    FullAdderOp,
    HalfAdderOp,
    InstanceOp,
    Xor2Op,
)
from ..ir import bit_wire_type, expand_signal_decl_refs, get_wire_width, require_wire_name, wire_type
from ..signals import SignalDecl
from .lower_multiplier_to_arith_parts import _plan_compressor_tree


_BIT_SELECT_RE = re.compile(r"^(?P<base>[A-Za-z_]\w*)\[(?P<index>\d+)\]$")
_PP_NAME_RE = re.compile(r"^pp_(?P<lhs>\d+)_(?P<rhs>\d+)$")
_ROW_NAME_RE = re.compile(r"^(?P<base>[A-Za-z_]\w*)\[(?P<index>\d+)\]$")
_LOGIC_REGION_KIND_ATTR = "logic.region_kind"


def _read_top_name(module: ModuleOp) -> str:
    top_func = _find_top_func(module)
    if top_func is not None:
        return top_func.sym_name.data
    func_name_attr = module.attributes.get("func_name")
    if not isinstance(func_name_attr, StringAttr):
        raise AssertionError("builtin.module is missing string attribute 'func_name'")
    return func_name_attr.data


def _find_top_func(module: ModuleOp) -> FuncOp | None:
    top_funcs = [
        op
        for op in module.ops
        if isinstance(op, FuncOp) and (op.sym_visibility is None or op.sym_visibility.data != "private")
    ]
    if not top_funcs:
        return None
    if len(top_funcs) != 1:
        raise AssertionError("Expected exactly one non-private top func.func")
    return top_funcs[0]


def _enclosing_module(op: Operation) -> ModuleOp:
    parent = op.parent_op()
    while parent is not None:
        if isinstance(parent, ModuleOp):
            return parent
        parent = parent.parent_op()
    raise AssertionError(f"Failed to find enclosing builtin.module for {op.name!r}")


def _short_region_kind(region_kind: str) -> str:
    return region_kind.rsplit(".", 1)[-1]


def _is_literal(signal: str) -> bool:
    return "'" in signal or signal.isdigit()


def _build_port_decls_from_values(values: list[SSAValue], *, kind: str) -> list[SignalDecl]:
    return [
        SignalDecl(name=require_wire_name(value), width=get_wire_width(value), kind=kind)
        for value in values
    ]


class _LogicRegionBuilder:
    def __init__(
        self,
        input_ports: list[SignalDecl],
        output_ports: list[SignalDecl],
        block_args: tuple[SSAValue, ...],
    ) -> None:
        self.input_ports = input_ports
        self.output_ports = output_ports
        self.input_refs = [ref for signal in input_ports for ref in expand_signal_decl_refs(signal)]
        self.output_refs = [ref for signal in output_ports for ref in expand_signal_decl_refs(signal)]
        self.ops: list = []
        self.values: dict[str, SSAValue] = {}
        self.constants: dict[str, SSAValue] = {}
        self._seed_inputs(block_args)

    def _seed_inputs(self, block_args: tuple[SSAValue, ...]) -> None:
        if len(block_args) != len(self.input_refs):
            raise AssertionError("Function block arguments do not match expanded input refs")
        for ref, arg in zip(self.input_refs, block_args):
            self.values[ref] = arg

    def get(self, signal: str) -> SSAValue:
        if signal in self.values:
            return self.values[signal]
        if not _is_literal(signal):
            raise AssertionError(f"Unknown logic signal reference {signal!r}")
        const = self.constants.get(signal)
        if const is not None:
            return const
        op = ConstantOp(value=signal, wire_type_=bit_wire_type())
        self.ops.append(op)
        self.constants[signal] = op.output
        return op.output

    def bind(self, signal: str, value: SSAValue) -> None:
        self.values[signal] = value

    def finish(self) -> list:
        return [*self.ops, ReturnOp(*(self.get(ref) for ref in self.output_refs))]


def _make_logic_region_func(
    *,
    func_name: str,
    region_kind: str,
    input_ports: list[SignalDecl],
    output_ports: list[SignalDecl],
 ) -> FuncOp:
    input_refs = [ref for signal in input_ports for ref in expand_signal_decl_refs(signal)]
    output_refs = [ref for signal in output_ports for ref in expand_signal_decl_refs(signal)]
    func_op = FuncOp(
        func_name,
        (
            [bit_wire_type(name=ref) for ref in input_refs],
            [bit_wire_type(name=ref) for ref in output_refs],
        ),
        visibility="private",
    )
    func_op.attributes[_LOGIC_REGION_KIND_ATTR] = StringAttr(region_kind)
    return func_op


def _make_instance_op(
    *,
    instance_name: str,
    callee: str,
    inputs: list[SSAValue],
    output_types: list,
) -> InstanceOp:
    return InstanceOp(
        instance_name=instance_name,
        callee=callee,
        inputs=inputs,
        output_types=output_types,
    )


def _group_rows(names: list[str]) -> dict[str, dict[int, str]]:
    rows: dict[str, dict[int, str]] = defaultdict(dict)
    for name in names:
        match = _ROW_NAME_RE.match(name)
        if match is None:
            rows[name][0] = name
            continue
        rows[match.group("base")][int(match.group("index"))] = name
    return rows


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
    def __init__(self, name_allocator: _NameAllocator) -> None:
        super().__init__()
        self.name_allocator = name_allocator

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: PartialProductGeneratorOp, rewriter: PatternRewriter) -> None:
        input_values = list(op.inputs)
        output_names = [require_wire_name(result) for result in op.results]
        input_names = [require_wire_name(value) for value in input_values]

        base_names = sorted({name.split("[", 1)[0] for name in input_names})
        if len(base_names) != 2:
            raise AssertionError(f"Expected two PPG input bases, got {base_names}")
        lhs_base, rhs_base = base_names

        input_ports = _build_port_decls_from_values(input_values, kind="input")
        output_ports = _build_port_decls_from_values(list(op.results), kind="output")
        func_name, instance_name = self.name_allocator.allocate(op.owner.data)
        func_op = _make_logic_region_func(
            func_name=func_name,
            region_kind=op.owner.data,
            input_ports=input_ports,
            output_ports=output_ports,
        )
        builder = _LogicRegionBuilder(input_ports, output_ports, func_op.args)
        for index, output_name in enumerate(output_names):
            match = _PP_NAME_RE.match(output_name)
            if match is None:
                raise AssertionError(f"Malformed partial product name {output_name!r}")
            lhs = builder.get(f"{lhs_base}[{int(match.group('lhs'))}]")
            rhs = builder.get(f"{rhs_base}[{int(match.group('rhs'))}]")
            and2 = And2Op(
                instance_name=f"ppg_and2_{index}",
                output_name=output_name,
                lhs=lhs,
                rhs=rhs,
            )
            builder.ops.append(and2)
            builder.bind(output_name, and2.output)

        for inner_op in builder.finish():
            func_op.body.block.add_op(inner_op)
        rewriter.insert_op(func_op, InsertPoint.at_end(_enclosing_module(op).body.block))
        instance_op = _make_instance_op(
            instance_name=instance_name,
            callee=func_name,
            inputs=input_values,
            output_types=[result.type for result in op.results],
        )
        rewriter.replace_matched_op(instance_op, new_results=tuple(instance_op.outputs), safe_erase=True)


class LowerCompressorTreeToLogicPattern(RewritePattern):
    def __init__(self, name_allocator: _NameAllocator) -> None:
        super().__init__()
        self.name_allocator = name_allocator

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: CompressorTreeOp, rewriter: PatternRewriter) -> None:
        input_values = list(op.inputs)
        output_names = [require_wire_name(result) for result in op.results]
        input_ports = _build_port_decls_from_values(input_values, kind="input")
        input_names = [ref for signal in input_ports for ref in expand_signal_decl_refs(signal)]

        columns: dict[int, list[str]] = defaultdict(list)
        for name in input_names:
            pp_match = _PP_NAME_RE.match(name)
            if pp_match is not None:
                column = int(pp_match.group("lhs")) + int(pp_match.group("rhs"))
                columns[column].append(name)
                continue
            row_match = _ROW_NAME_RE.match(name)
            if row_match is not None:
                columns[int(row_match.group("index"))].append(name)
                continue
            raise AssertionError(f"Unsupported compressor input {name!r}")

        stage_ops, lhs_row, rhs_row = _plan_compressor_tree(dict(columns))
        output_ports = _build_port_decls_from_values(list(op.results), kind="output")
        func_name, instance_name = self.name_allocator.allocate(op.owner.data)
        func_op = _make_logic_region_func(
            func_name=func_name,
            region_kind=op.owner.data,
            input_ports=input_ports,
            output_ports=output_ports,
        )
        builder = _LogicRegionBuilder(input_ports, output_ports, func_op.args)
        for kind, gate_instance_name, lhs, rhs, cin, sum_out, carry_out in stage_ops:
            if kind == "fa":
                fa = FullAdderOp(
                    instance_name=gate_instance_name,
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
                    instance_name=gate_instance_name,
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

        for signal in output_ports:
            if signal.name not in {"ct_lhs", "ct_rhs"}:
                raise AssertionError(f"Unsupported compressor output port {signal.name!r}")
            row = lhs_row if signal.name == "ct_lhs" else rhs_row
            if signal.width == 1:
                builder.bind(signal.name, builder.get(row.get(0, "1'b0")))
                continue
            for bit in range(signal.width):
                builder.bind(f"{signal.name}[{bit}]", builder.get(row.get(bit, "1'b0")))

        for inner_op in builder.finish():
            func_op.body.block.add_op(inner_op)
        rewriter.insert_op(func_op, InsertPoint.at_end(_enclosing_module(op).body.block))
        instance_op = _make_instance_op(
            instance_name=instance_name,
            callee=func_name,
            inputs=input_values,
            output_types=[result.type for result in op.results],
        )
        rewriter.replace_matched_op(instance_op, new_results=tuple(instance_op.outputs), safe_erase=True)


class LowerPrefixTreeToLogicPattern(RewritePattern):
    def __init__(self, name_allocator: _NameAllocator) -> None:
        super().__init__()
        self.name_allocator = name_allocator

    def _lower_ripple(
        self,
        output_base: str,
        lhs_row: dict[int, str],
        rhs_row: dict[int, str],
        builder: _LogicRegionBuilder,
    ) -> None:
        max_bit = max(set(lhs_row) | set(rhs_row), default=-1)
        for bit in range(max_bit + 1):
            cin_name = "1'b0" if bit == 0 else f"pt_carry_{bit}"
            carry_out = f"pt_overflow_{bit + 1}" if bit == max_bit else f"pt_carry_{bit + 1}"
            fa = FullAdderOp(
                instance_name=f"pt_b{bit}_fa",
                sum_name=f"{output_base}[{bit}]",
                carry_name=carry_out,
                lhs=builder.get(lhs_row.get(bit, "1'b0")),
                rhs=builder.get(rhs_row.get(bit, "1'b0")),
                cin=builder.get(cin_name),
            )
            builder.ops.append(fa)
            builder.bind(f"{output_base}[{bit}]", fa.sum_out)
            builder.bind(carry_out, fa.carry_out)

    def _lower_kogge_stone(
        self,
        output_base: str,
        lhs_row: dict[int, str],
        rhs_row: dict[int, str],
        builder: _LogicRegionBuilder,
    ) -> None:
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
                output_name=propagate_wire,
                lhs=lhs,
                rhs=rhs,
            )
            and_g = And2Op(
                instance_name=f"pt_b{bit}_and_g",
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
                    output_name=merged_propagate,
                    lhs=current_propagate[bit],
                    rhs=current_propagate[bit - span],
                )
                ao21_g = Ao21Op(
                    instance_name=f"pt_s{stage}_ao21_g_{bit}",
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
                output_name=f"{output_base}[{bit}]",
                lhs=propagate[bit],
                rhs=carry_in,
            )
            builder.ops.append(xor_sum)
            builder.bind(f"{output_base}[{bit}]", xor_sum.output)

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: PrefixTreeOp, rewriter: PatternRewriter) -> None:
        input_values = list(op.inputs)
        output_names = [require_wire_name(result) for result in op.results]
        input_names = [require_wire_name(value) for value in input_values]
        input_ports = _build_port_decls_from_values(input_values, kind="input")
        output_ports = _build_port_decls_from_values(list(op.results), kind="output")
        port_map = {signal.name: signal for signal in input_ports}
        lhs_decl = port_map.get("ct_lhs")
        rhs_decl = port_map.get("ct_rhs")
        if lhs_decl is None or rhs_decl is None:
            raise AssertionError(f"Expected ct_lhs/ct_rhs prefix inputs, got {input_names}")
        lhs_row = {bit: f"{lhs_decl.name}[{bit}]" for bit in range(lhs_decl.width)}
        rhs_row = {bit: f"{rhs_decl.name}[{bit}]" for bit in range(rhs_decl.width)}
        if len(output_ports) != 1:
            raise AssertionError(f"Expected one prefix output bus, got {output_names}")
        output_base = output_ports[0].name

        func_name, instance_name = self.name_allocator.allocate(op.owner.data)
        func_op = _make_logic_region_func(
            func_name=func_name,
            region_kind=op.owner.data,
            input_ports=input_ports,
            output_ports=output_ports,
        )
        builder = _LogicRegionBuilder(input_ports, output_ports, func_op.args)
        implementation = PrefixTreeImplementation(op.implementation.value.data)
        if implementation == PrefixTreeImplementation.RIPPLE:
            self._lower_ripple(output_base, lhs_row, rhs_row, builder)
        elif implementation == PrefixTreeImplementation.KOGGE_STONE:
            self._lower_kogge_stone(output_base, lhs_row, rhs_row, builder)
        else:
            raise AssertionError(f"Unsupported prefix tree implementation {op.implementation.value.data!r}")

        for inner_op in builder.finish():
            func_op.body.block.add_op(inner_op)
        rewriter.insert_op(func_op, InsertPoint.at_end(_enclosing_module(op).body.block))
        instance_op = _make_instance_op(
            instance_name=instance_name,
            callee=func_name,
            inputs=input_values,
            output_types=[result.type for result in op.results],
        )
        rewriter.replace_matched_op(instance_op, new_results=tuple(instance_op.outputs), safe_erase=True)


@dataclass(frozen=True)
class LowerArithToLogicPass(ModulePass):
    name = "lower-arith-to-logic"

    def apply(self, ctx: Context, op: ModuleOp) -> None:
        del ctx
        name_allocator = _NameAllocator(_read_top_name(op))
        PatternRewriteWalker(
            LowerPartialProductGeneratorPattern(name_allocator),
            apply_recursively=True,
        ).rewrite_module(op)
        PatternRewriteWalker(
            LowerCompressorTreeToLogicPattern(name_allocator),
            apply_recursively=True,
        ).rewrite_module(op)
        PatternRewriteWalker(
            LowerPrefixTreeToLogicPattern(name_allocator),
            apply_recursively=True,
        ).rewrite_module(op)
