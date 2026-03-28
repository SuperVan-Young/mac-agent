"""xDSL definitions for the asap7 dialect."""

from __future__ import annotations

from xdsl.dialects.builtin import StringAttr
from xdsl.irdl import IRDLOperation, prop_def, irdl_op_definition
from xdsl.ir import Dialect


@irdl_op_definition
class Xor2Op(IRDLOperation):
    name = "asap7.xor2"

    instance_name = prop_def(StringAttr)
    output = prop_def(StringAttr)
    lhs = prop_def(StringAttr)
    rhs = prop_def(StringAttr)
    owner = prop_def(StringAttr)

    def __init__(self, *, instance_name: str, output: str, lhs: str, rhs: str, owner: str) -> None:
        super().__init__(
            properties={
                "instance_name": StringAttr(instance_name),
                "output": StringAttr(output),
                "lhs": StringAttr(lhs),
                "rhs": StringAttr(rhs),
                "owner": StringAttr(owner),
            }
        )


@irdl_op_definition
class Or2Op(IRDLOperation):
    name = "asap7.or2"

    instance_name = prop_def(StringAttr)
    output = prop_def(StringAttr)
    lhs = prop_def(StringAttr)
    rhs = prop_def(StringAttr)
    owner = prop_def(StringAttr)

    def __init__(self, *, instance_name: str, output: str, lhs: str, rhs: str, owner: str) -> None:
        super().__init__(
            properties={
                "instance_name": StringAttr(instance_name),
                "output": StringAttr(output),
                "lhs": StringAttr(lhs),
                "rhs": StringAttr(rhs),
                "owner": StringAttr(owner),
            }
        )


@irdl_op_definition
class And2Op(IRDLOperation):
    name = "asap7.and2"

    instance_name = prop_def(StringAttr)
    output = prop_def(StringAttr)
    lhs = prop_def(StringAttr)
    rhs = prop_def(StringAttr)
    owner = prop_def(StringAttr)

    def __init__(self, *, instance_name: str, output: str, lhs: str, rhs: str, owner: str) -> None:
        super().__init__(
            properties={
                "instance_name": StringAttr(instance_name),
                "output": StringAttr(output),
                "lhs": StringAttr(lhs),
                "rhs": StringAttr(rhs),
                "owner": StringAttr(owner),
            }
        )


@irdl_op_definition
class FullAdderOp(IRDLOperation):
    name = "asap7.full_adder"

    instance_name = prop_def(StringAttr)
    impl_type = prop_def(StringAttr)
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
        impl_type: str,
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
                "impl_type": StringAttr(impl_type),
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
    name = "asap7.half_adder"

    instance_name = prop_def(StringAttr)
    impl_type = prop_def(StringAttr)
    region_kind = prop_def(StringAttr)
    sum_out = prop_def(StringAttr)
    carry_out = prop_def(StringAttr)
    lhs = prop_def(StringAttr)
    rhs = prop_def(StringAttr)

    def __init__(
        self,
        *,
        instance_name: str,
        impl_type: str,
        region_kind: str,
        sum_out: str,
        carry_out: str,
        lhs: str,
        rhs: str,
    ) -> None:
        super().__init__(
            properties={
                "instance_name": StringAttr(instance_name),
                "impl_type": StringAttr(impl_type),
                "region_kind": StringAttr(region_kind),
                "sum_out": StringAttr(sum_out),
                "carry_out": StringAttr(carry_out),
                "lhs": StringAttr(lhs),
                "rhs": StringAttr(rhs),
            }
        )

ASAP7_DIALECT = Dialect("asap7", [Xor2Op, Or2Op, And2Op, FullAdderOp, HalfAdderOp], [])
