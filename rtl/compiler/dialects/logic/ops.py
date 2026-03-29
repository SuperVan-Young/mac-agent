"""xDSL definitions for the logic dialect."""

from __future__ import annotations

from xdsl.dialects.builtin import ArrayAttr, StringAttr
from xdsl.ir import Dialect, SSAValue
from xdsl.irdl import (
    IRDLOperation,
    operand_def,
    prop_def,
    irdl_op_definition,
    result_def,
)

from ...ir import WireType, bit_wire_type


def _encode_connections(connections: list[tuple[str, str]]) -> ArrayAttr[StringAttr]:
    return ArrayAttr(StringAttr(f"{port}={signal}") for port, signal in connections)


def decode_connections(attr: ArrayAttr[StringAttr]) -> list[tuple[str, str]]:
    connections: list[tuple[str, str]] = []
    for item in attr:
        port, _, signal = item.data.partition("=")
        connections.append((port, signal))
    return connections


@irdl_op_definition
class InputPortOp(IRDLOperation):
    name = "logic.input"

    port_name = prop_def(StringAttr)
    output = result_def(WireType)

    def __init__(self, *, port_name: str, wire_type: WireType | None = None) -> None:
        super().__init__(
            properties={"port_name": StringAttr(port_name)},
            result_types=(wire_type or bit_wire_type(),),
        )


@irdl_op_definition
class OutputPortOp(IRDLOperation):
    name = "logic.output"

    port_name = prop_def(StringAttr)
    value = operand_def(WireType)

    def __init__(self, *, port_name: str, value: SSAValue) -> None:
        super().__init__(
            operands=(value,),
            properties={"port_name": StringAttr(port_name)},
        )


@irdl_op_definition
class ConstantOp(IRDLOperation):
    name = "logic.constant"

    value = prop_def(StringAttr)
    output = result_def(WireType)

    def __init__(self, *, value: str, wire_type: WireType | None = None) -> None:
        super().__init__(
            properties={"value": StringAttr(value)},
            result_types=(wire_type or bit_wire_type(),),
        )


@irdl_op_definition
class And2Op(IRDLOperation):
    name = "logic.and2"

    lhs = operand_def(WireType)
    rhs = operand_def(WireType)
    instance_name = prop_def(StringAttr)
    region_kind = prop_def(StringAttr)
    output_name = prop_def(StringAttr)
    output = result_def(WireType)

    def __init__(
        self,
        *,
        instance_name: str,
        region_kind: str,
        output_name: str,
        lhs: SSAValue,
        rhs: SSAValue,
        wire_type: WireType | None = None,
    ) -> None:
        super().__init__(
            operands=(lhs, rhs),
            properties={
                "instance_name": StringAttr(instance_name),
                "region_kind": StringAttr(region_kind),
                "output_name": StringAttr(output_name),
            },
            result_types=(wire_type or bit_wire_type(),),
        )


@irdl_op_definition
class Or2Op(IRDLOperation):
    name = "logic.or2"

    lhs = operand_def(WireType)
    rhs = operand_def(WireType)
    instance_name = prop_def(StringAttr)
    region_kind = prop_def(StringAttr)
    output_name = prop_def(StringAttr)
    output = result_def(WireType)

    def __init__(
        self,
        *,
        instance_name: str,
        region_kind: str,
        output_name: str,
        lhs: SSAValue,
        rhs: SSAValue,
        wire_type: WireType | None = None,
    ) -> None:
        super().__init__(
            operands=(lhs, rhs),
            properties={
                "instance_name": StringAttr(instance_name),
                "region_kind": StringAttr(region_kind),
                "output_name": StringAttr(output_name),
            },
            result_types=(wire_type or bit_wire_type(),),
        )


@irdl_op_definition
class Xor2Op(IRDLOperation):
    name = "logic.xor2"

    lhs = operand_def(WireType)
    rhs = operand_def(WireType)
    instance_name = prop_def(StringAttr)
    region_kind = prop_def(StringAttr)
    output_name = prop_def(StringAttr)
    output = result_def(WireType)

    def __init__(
        self,
        *,
        instance_name: str,
        region_kind: str,
        output_name: str,
        lhs: SSAValue,
        rhs: SSAValue,
        wire_type: WireType | None = None,
    ) -> None:
        super().__init__(
            operands=(lhs, rhs),
            properties={
                "instance_name": StringAttr(instance_name),
                "region_kind": StringAttr(region_kind),
                "output_name": StringAttr(output_name),
            },
            result_types=(wire_type or bit_wire_type(),),
        )


@irdl_op_definition
class Ao21Op(IRDLOperation):
    name = "logic.ao21"

    and_lhs = operand_def(WireType)
    and_rhs = operand_def(WireType)
    or_rhs = operand_def(WireType)
    instance_name = prop_def(StringAttr)
    region_kind = prop_def(StringAttr)
    output_name = prop_def(StringAttr)
    output = result_def(WireType)

    def __init__(
        self,
        *,
        instance_name: str,
        region_kind: str,
        output_name: str,
        and_lhs: SSAValue,
        and_rhs: SSAValue,
        or_rhs: SSAValue,
        wire_type: WireType | None = None,
    ) -> None:
        super().__init__(
            operands=(and_lhs, and_rhs, or_rhs),
            properties={
                "instance_name": StringAttr(instance_name),
                "region_kind": StringAttr(region_kind),
                "output_name": StringAttr(output_name),
            },
            result_types=(wire_type or bit_wire_type(),),
        )


@irdl_op_definition
class FullAdderOp(IRDLOperation):
    name = "logic.full_adder"

    lhs = operand_def(WireType)
    rhs = operand_def(WireType)
    cin = operand_def(WireType)
    instance_name = prop_def(StringAttr)
    region_kind = prop_def(StringAttr)
    sum_name = prop_def(StringAttr)
    carry_name = prop_def(StringAttr)
    sum_out = result_def(WireType)
    carry_out = result_def(WireType)

    def __init__(
        self,
        *,
        instance_name: str,
        region_kind: str,
        sum_name: str,
        carry_name: str,
        lhs: SSAValue,
        rhs: SSAValue,
        cin: SSAValue,
        wire_type: WireType | None = None,
    ) -> None:
        result_wire_type = wire_type or bit_wire_type()
        super().__init__(
            operands=(lhs, rhs, cin),
            properties={
                "instance_name": StringAttr(instance_name),
                "region_kind": StringAttr(region_kind),
                "sum_name": StringAttr(sum_name),
                "carry_name": StringAttr(carry_name),
            },
            result_types=(result_wire_type, result_wire_type),
        )


@irdl_op_definition
class HalfAdderOp(IRDLOperation):
    name = "logic.half_adder"

    lhs = operand_def(WireType)
    rhs = operand_def(WireType)
    instance_name = prop_def(StringAttr)
    region_kind = prop_def(StringAttr)
    sum_name = prop_def(StringAttr)
    carry_name = prop_def(StringAttr)
    sum_out = result_def(WireType)
    carry_out = result_def(WireType)

    def __init__(
        self,
        *,
        instance_name: str,
        region_kind: str,
        sum_name: str,
        carry_name: str,
        lhs: SSAValue,
        rhs: SSAValue,
        wire_type: WireType | None = None,
    ) -> None:
        result_wire_type = wire_type or bit_wire_type()
        super().__init__(
            operands=(lhs, rhs),
            properties={
                "instance_name": StringAttr(instance_name),
                "region_kind": StringAttr(region_kind),
                "sum_name": StringAttr(sum_name),
                "carry_name": StringAttr(carry_name),
            },
            result_types=(result_wire_type, result_wire_type),
        )


@irdl_op_definition
class InstanceOp(IRDLOperation):
    name = "logic.instance"

    instance_name = prop_def(StringAttr)
    callee = prop_def(StringAttr)
    region_kind = prop_def(StringAttr)
    input_connections = prop_def(ArrayAttr[StringAttr])
    output_connections = prop_def(ArrayAttr[StringAttr])

    def __init__(
        self,
        *,
        instance_name: str,
        callee: str,
        region_kind: str,
        input_connections: list[tuple[str, str]],
        output_connections: list[tuple[str, str]],
    ) -> None:
        super().__init__(
            properties={
                "instance_name": StringAttr(instance_name),
                "callee": StringAttr(callee),
                "region_kind": StringAttr(region_kind),
                "input_connections": _encode_connections(input_connections),
                "output_connections": _encode_connections(output_connections),
            }
        )


LOGIC_DIALECT = Dialect(
    "logic",
    [
        InputPortOp,
        OutputPortOp,
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
