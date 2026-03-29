"""xDSL definitions for the logic dialect."""

from __future__ import annotations

from xdsl.dialects.builtin import IntAttr, StringAttr
from xdsl.ir import Dialect, SSAValue
from xdsl.irdl import (
    IRDLOperation,
    operand_def,
    prop_def,
    irdl_op_definition,
    result_def,
    var_operand_def,
    var_result_def,
)

from ...ir import WireType, bit_wire_type, wire_type


def _named_result_types(
    result_type: WireType | None,
    *names: str,
) -> tuple[WireType, ...]:
    dims = (1,) if result_type is None else tuple(dim.data for dim in result_type.shape)
    return tuple(wire_type(*dims, name=name) for name in names)


@irdl_op_definition
class ConstantOp(IRDLOperation):
    name = "logic.constant"

    value = prop_def(StringAttr)
    output = result_def(WireType)

    def __init__(self, *, value: str, wire_type_: WireType | None = None) -> None:
        super().__init__(
            properties={"value": StringAttr(value)},
            result_types=((wire_type_ or bit_wire_type()),),
        )


@irdl_op_definition
class And2Op(IRDLOperation):
    name = "logic.and2"

    lhs = operand_def(WireType)
    rhs = operand_def(WireType)
    instance_name = prop_def(StringAttr)
    output = result_def(WireType)

    def __init__(
        self,
        *,
        instance_name: str,
        output_name: str,
        lhs: SSAValue,
        rhs: SSAValue,
        wire_type_: WireType | None = None,
    ) -> None:
        super().__init__(
            operands=(lhs, rhs),
            properties={
                "instance_name": StringAttr(instance_name),
            },
            result_types=(_named_result_types(wire_type_, output_name)[0],),
        )


@irdl_op_definition
class Or2Op(IRDLOperation):
    name = "logic.or2"

    lhs = operand_def(WireType)
    rhs = operand_def(WireType)
    instance_name = prop_def(StringAttr)
    output = result_def(WireType)

    def __init__(
        self,
        *,
        instance_name: str,
        output_name: str,
        lhs: SSAValue,
        rhs: SSAValue,
        wire_type_: WireType | None = None,
    ) -> None:
        super().__init__(
            operands=(lhs, rhs),
            properties={
                "instance_name": StringAttr(instance_name),
            },
            result_types=(_named_result_types(wire_type_, output_name)[0],),
        )


@irdl_op_definition
class Xor2Op(IRDLOperation):
    name = "logic.xor2"

    lhs = operand_def(WireType)
    rhs = operand_def(WireType)
    instance_name = prop_def(StringAttr)
    output = result_def(WireType)

    def __init__(
        self,
        *,
        instance_name: str,
        output_name: str,
        lhs: SSAValue,
        rhs: SSAValue,
        wire_type_: WireType | None = None,
    ) -> None:
        super().__init__(
            operands=(lhs, rhs),
            properties={
                "instance_name": StringAttr(instance_name),
            },
            result_types=(_named_result_types(wire_type_, output_name)[0],),
        )


@irdl_op_definition
class Ao21Op(IRDLOperation):
    name = "logic.ao21"

    and_lhs = operand_def(WireType)
    and_rhs = operand_def(WireType)
    or_rhs = operand_def(WireType)
    instance_name = prop_def(StringAttr)
    output = result_def(WireType)

    def __init__(
        self,
        *,
        instance_name: str,
        output_name: str,
        and_lhs: SSAValue,
        and_rhs: SSAValue,
        or_rhs: SSAValue,
        wire_type_: WireType | None = None,
    ) -> None:
        super().__init__(
            operands=(and_lhs, and_rhs, or_rhs),
            properties={
                "instance_name": StringAttr(instance_name),
            },
            result_types=(_named_result_types(wire_type_, output_name)[0],),
        )


@irdl_op_definition
class FullAdderOp(IRDLOperation):
    name = "logic.full_adder"

    lhs = operand_def(WireType)
    rhs = operand_def(WireType)
    cin = operand_def(WireType)
    instance_name = prop_def(StringAttr)
    sum_out = result_def(WireType)
    carry_out = result_def(WireType)

    def __init__(
        self,
        *,
        instance_name: str,
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
            },
            result_types=_named_result_types(wire_type_, sum_name, carry_name),
        )


@irdl_op_definition
class HalfAdderOp(IRDLOperation):
    name = "logic.half_adder"

    lhs = operand_def(WireType)
    rhs = operand_def(WireType)
    instance_name = prop_def(StringAttr)
    sum_out = result_def(WireType)
    carry_out = result_def(WireType)

    def __init__(
        self,
        *,
        instance_name: str,
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
            },
            result_types=_named_result_types(wire_type_, sum_name, carry_name),
        )


@irdl_op_definition
class InstanceOp(IRDLOperation):
    name = "logic.instance"

    inputs = var_operand_def(WireType)
    instance_name = prop_def(StringAttr)
    callee = prop_def(StringAttr)
    outputs = var_result_def(WireType)

    def __init__(
        self,
        *,
        instance_name: str,
        callee: str,
        inputs: list[SSAValue],
        output_types: list[WireType],
    ) -> None:
        super().__init__(
            operands=[inputs],
            properties={
                "instance_name": StringAttr(instance_name),
                "callee": StringAttr(callee),
            },
            result_types=[output_types],
        )


LOGIC_DIALECT = Dialect(
    "logic",
    [
        ConstantOp,
        And2Op,
        Or2Op,
        Xor2Op,
        Ao21Op,
        FullAdderOp,
        HalfAdderOp,
        InstanceOp,
    ],
    [],
)
