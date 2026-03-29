"""xDSL definitions for the asap7 dialect."""

from __future__ import annotations

from xdsl.dialects.builtin import StringAttr
from xdsl.ir import Dialect, SSAValue
from xdsl.irdl import IRDLOperation, operand_def, prop_def, irdl_op_definition, result_def

from ...ir import WireType, bit_wire_type, wire_type


def _named_result_types(
    result_type: WireType | None,
    *names: str,
) -> tuple[WireType, ...]:
    dims = (1,) if result_type is None else tuple(dim.data for dim in result_type.shape)
    return tuple(wire_type(*dims, name=name) for name in names)


@irdl_op_definition
class Xor2Op(IRDLOperation):
    name = "asap7.xor2"

    lhs = operand_def(WireType)
    rhs = operand_def(WireType)
    instance_name = prop_def(StringAttr)
    cell = prop_def(StringAttr)
    owner = prop_def(StringAttr)
    output = result_def(WireType)

    def __init__(
        self,
        *,
        instance_name: str,
        lhs: SSAValue,
        rhs: SSAValue,
        output_name: str,
        owner: str,
        cell: str = "XOR2x2_ASAP7_75t_R",
        wire_type_: WireType | None = None,
    ) -> None:
        super().__init__(
            operands=(lhs, rhs),
            properties={
                "instance_name": StringAttr(instance_name),
                "cell": StringAttr(cell),
                "owner": StringAttr(owner),
            },
            result_types=(_named_result_types(wire_type_, output_name)[0],),
        )


@irdl_op_definition
class Or2Op(IRDLOperation):
    name = "asap7.or2"

    lhs = operand_def(WireType)
    rhs = operand_def(WireType)
    instance_name = prop_def(StringAttr)
    cell = prop_def(StringAttr)
    owner = prop_def(StringAttr)
    output = result_def(WireType)

    def __init__(
        self,
        *,
        instance_name: str,
        lhs: SSAValue,
        rhs: SSAValue,
        output_name: str,
        owner: str,
        cell: str = "OR2x2_ASAP7_75t_R",
        wire_type_: WireType | None = None,
    ) -> None:
        super().__init__(
            operands=(lhs, rhs),
            properties={
                "instance_name": StringAttr(instance_name),
                "cell": StringAttr(cell),
                "owner": StringAttr(owner),
            },
            result_types=(_named_result_types(wire_type_, output_name)[0],),
        )


@irdl_op_definition
class And2Op(IRDLOperation):
    name = "asap7.and2"

    lhs = operand_def(WireType)
    rhs = operand_def(WireType)
    instance_name = prop_def(StringAttr)
    cell = prop_def(StringAttr)
    owner = prop_def(StringAttr)
    output = result_def(WireType)

    def __init__(
        self,
        *,
        instance_name: str,
        lhs: SSAValue,
        rhs: SSAValue,
        output_name: str,
        owner: str,
        cell: str = "AND2x2_ASAP7_75t_R",
        wire_type_: WireType | None = None,
    ) -> None:
        super().__init__(
            operands=(lhs, rhs),
            properties={
                "instance_name": StringAttr(instance_name),
                "cell": StringAttr(cell),
                "owner": StringAttr(owner),
            },
            result_types=(_named_result_types(wire_type_, output_name)[0],),
        )


@irdl_op_definition
class Ao21Op(IRDLOperation):
    name = "asap7.ao21"

    and_lhs = operand_def(WireType)
    and_rhs = operand_def(WireType)
    or_rhs = operand_def(WireType)
    instance_name = prop_def(StringAttr)
    cell = prop_def(StringAttr)
    owner = prop_def(StringAttr)
    output = result_def(WireType)

    def __init__(
        self,
        *,
        instance_name: str,
        and_lhs: SSAValue,
        and_rhs: SSAValue,
        or_rhs: SSAValue,
        output_name: str,
        owner: str,
        cell: str = "AO21x2_ASAP7_75t_R",
        wire_type_: WireType | None = None,
    ) -> None:
        super().__init__(
            operands=(and_lhs, and_rhs, or_rhs),
            properties={
                "instance_name": StringAttr(instance_name),
                "cell": StringAttr(cell),
                "owner": StringAttr(owner),
            },
            result_types=(_named_result_types(wire_type_, output_name)[0],),
        )


@irdl_op_definition
class FullAdderOp(IRDLOperation):
    name = "asap7.full_adder"

    lhs = operand_def(WireType)
    rhs = operand_def(WireType)
    cin = operand_def(WireType)
    instance_name = prop_def(StringAttr)
    impl_type = prop_def(StringAttr)
    region_kind = prop_def(StringAttr)
    sum_out = result_def(WireType)
    carry_out = result_def(WireType)

    def __init__(
        self,
        *,
        instance_name: str,
        impl_type: str,
        region_kind: str,
        sum_name: str,
        carry_name: str,
        lhs: SSAValue,
        rhs: SSAValue,
        cin: SSAValue,
        wire_type_: WireType | None = None,
    ) -> None:
        super().__init__(
            operands=(lhs, rhs, cin),
            properties={
                "instance_name": StringAttr(instance_name),
                "impl_type": StringAttr(impl_type),
                "region_kind": StringAttr(region_kind),
            },
            result_types=_named_result_types(wire_type_, sum_name, carry_name),
        )


@irdl_op_definition
class HalfAdderOp(IRDLOperation):
    name = "asap7.half_adder"

    lhs = operand_def(WireType)
    rhs = operand_def(WireType)
    instance_name = prop_def(StringAttr)
    impl_type = prop_def(StringAttr)
    region_kind = prop_def(StringAttr)
    sum_out = result_def(WireType)
    carry_out = result_def(WireType)

    def __init__(
        self,
        *,
        instance_name: str,
        impl_type: str,
        region_kind: str,
        sum_name: str,
        carry_name: str,
        lhs: SSAValue,
        rhs: SSAValue,
        wire_type_: WireType | None = None,
    ) -> None:
        super().__init__(
            operands=(lhs, rhs),
            properties={
                "instance_name": StringAttr(instance_name),
                "impl_type": StringAttr(impl_type),
                "region_kind": StringAttr(region_kind),
            },
            result_types=_named_result_types(wire_type_, sum_name, carry_name),
        )


ASAP7_DIALECT = Dialect(
    "asap7",
    [Xor2Op, Or2Op, And2Op, Ao21Op, FullAdderOp, HalfAdderOp],
    [],
)
