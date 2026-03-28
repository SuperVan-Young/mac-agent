"""xDSL definitions for the logic dialect."""

from __future__ import annotations

from xdsl.dialects.builtin import ArrayAttr, StringAttr
from xdsl.irdl import IRDLOperation, prop_def, irdl_op_definition
from xdsl.ir import Dialect


def _encode_connections(connections: list[tuple[str, str]]) -> ArrayAttr[StringAttr]:
    return ArrayAttr(StringAttr(f"{port}={signal}") for port, signal in connections)


def decode_connections(attr: ArrayAttr[StringAttr]) -> list[tuple[str, str]]:
    connections: list[tuple[str, str]] = []
    for item in attr:
        port, _, signal = item.data.partition("=")
        connections.append((port, signal))
    return connections


@irdl_op_definition
class And2Op(IRDLOperation):
    name = "logic.and2"

    instance_name = prop_def(StringAttr)
    region_kind = prop_def(StringAttr)
    output = prop_def(StringAttr)
    lhs = prop_def(StringAttr)
    rhs = prop_def(StringAttr)

    def __init__(
        self,
        *,
        instance_name: str,
        region_kind: str,
        output: str,
        lhs: str,
        rhs: str,
    ) -> None:
        super().__init__(
            properties={
                "instance_name": StringAttr(instance_name),
                "region_kind": StringAttr(region_kind),
                "output": StringAttr(output),
                "lhs": StringAttr(lhs),
                "rhs": StringAttr(rhs),
            }
        )


@irdl_op_definition
class Or2Op(IRDLOperation):
    name = "logic.or2"

    instance_name = prop_def(StringAttr)
    region_kind = prop_def(StringAttr)
    output = prop_def(StringAttr)
    lhs = prop_def(StringAttr)
    rhs = prop_def(StringAttr)

    def __init__(
        self,
        *,
        instance_name: str,
        region_kind: str,
        output: str,
        lhs: str,
        rhs: str,
    ) -> None:
        super().__init__(
            properties={
                "instance_name": StringAttr(instance_name),
                "region_kind": StringAttr(region_kind),
                "output": StringAttr(output),
                "lhs": StringAttr(lhs),
                "rhs": StringAttr(rhs),
            }
        )


@irdl_op_definition
class Xor2Op(IRDLOperation):
    name = "logic.xor2"

    instance_name = prop_def(StringAttr)
    region_kind = prop_def(StringAttr)
    output = prop_def(StringAttr)
    lhs = prop_def(StringAttr)
    rhs = prop_def(StringAttr)

    def __init__(
        self,
        *,
        instance_name: str,
        region_kind: str,
        output: str,
        lhs: str,
        rhs: str,
    ) -> None:
        super().__init__(
            properties={
                "instance_name": StringAttr(instance_name),
                "region_kind": StringAttr(region_kind),
                "output": StringAttr(output),
                "lhs": StringAttr(lhs),
                "rhs": StringAttr(rhs),
            }
        )


@irdl_op_definition
class Ao21Op(IRDLOperation):
    name = "logic.ao21"

    instance_name = prop_def(StringAttr)
    region_kind = prop_def(StringAttr)
    output = prop_def(StringAttr)
    and_lhs = prop_def(StringAttr)
    and_rhs = prop_def(StringAttr)
    or_rhs = prop_def(StringAttr)

    def __init__(
        self,
        *,
        instance_name: str,
        region_kind: str,
        output: str,
        and_lhs: str,
        and_rhs: str,
        or_rhs: str,
    ) -> None:
        super().__init__(
            properties={
                "instance_name": StringAttr(instance_name),
                "region_kind": StringAttr(region_kind),
                "output": StringAttr(output),
                "and_lhs": StringAttr(and_lhs),
                "and_rhs": StringAttr(and_rhs),
                "or_rhs": StringAttr(or_rhs),
            }
        )


@irdl_op_definition
class FullAdderOp(IRDLOperation):
    name = "logic.full_adder"

    instance_name = prop_def(StringAttr)
    region_kind = prop_def(StringAttr)
    sum_out = prop_def(StringAttr)
    carry_out = prop_def(StringAttr)
    lhs = prop_def(StringAttr)
    rhs = prop_def(StringAttr)
    cin = prop_def(StringAttr)

    def __init__(
        self,
        *,
        instance_name: str,
        region_kind: str,
        sum_out: str,
        carry_out: str,
        lhs: str,
        rhs: str,
        cin: str,
    ) -> None:
        super().__init__(
            properties={
                "instance_name": StringAttr(instance_name),
                "region_kind": StringAttr(region_kind),
                "sum_out": StringAttr(sum_out),
                "carry_out": StringAttr(carry_out),
                "lhs": StringAttr(lhs),
                "rhs": StringAttr(rhs),
                "cin": StringAttr(cin),
            }
        )


@irdl_op_definition
class HalfAdderOp(IRDLOperation):
    name = "logic.half_adder"

    instance_name = prop_def(StringAttr)
    region_kind = prop_def(StringAttr)
    sum_out = prop_def(StringAttr)
    carry_out = prop_def(StringAttr)
    lhs = prop_def(StringAttr)
    rhs = prop_def(StringAttr)

    def __init__(
        self,
        *,
        instance_name: str,
        region_kind: str,
        sum_out: str,
        carry_out: str,
        lhs: str,
        rhs: str,
    ) -> None:
        super().__init__(
            properties={
                "instance_name": StringAttr(instance_name),
                "region_kind": StringAttr(region_kind),
                "sum_out": StringAttr(sum_out),
                "carry_out": StringAttr(carry_out),
                "lhs": StringAttr(lhs),
                "rhs": StringAttr(rhs),
            }
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
    [And2Op, Or2Op, Xor2Op, Ao21Op, FullAdderOp, HalfAdderOp, InstanceOp],
    [],
)
