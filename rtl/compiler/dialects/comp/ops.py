"""xDSL definitions for the comp dialect."""

from __future__ import annotations

from xdsl.dialects.builtin import StringAttr
from xdsl.irdl import IRDLOperation, prop_def, irdl_op_definition
from xdsl.ir import Dialect


@irdl_op_definition
class FullAdderOp(IRDLOperation):
    name = "comp.fa"

    instance_name = prop_def(StringAttr)
    sum_out = prop_def(StringAttr)
    carry_out = prop_def(StringAttr)
    lhs = prop_def(StringAttr)
    rhs = prop_def(StringAttr)
    cin = prop_def(StringAttr)
    owner = prop_def(StringAttr)

    def __init__(
        self,
        *,
        instance_name: str,
        sum_out: str,
        carry_out: str,
        lhs: str,
        rhs: str,
        cin: str,
        owner: str,
    ) -> None:
        super().__init__(
            properties={
                "instance_name": StringAttr(instance_name),
                "sum_out": StringAttr(sum_out),
                "carry_out": StringAttr(carry_out),
                "lhs": StringAttr(lhs),
                "rhs": StringAttr(rhs),
                "cin": StringAttr(cin),
                "owner": StringAttr(owner),
            }
        )


@irdl_op_definition
class HalfAdderOp(IRDLOperation):
    name = "comp.ha"

    instance_name = prop_def(StringAttr)
    sum_out = prop_def(StringAttr)
    carry_out = prop_def(StringAttr)
    lhs = prop_def(StringAttr)
    rhs = prop_def(StringAttr)
    owner = prop_def(StringAttr)

    def __init__(
        self,
        *,
        instance_name: str,
        sum_out: str,
        carry_out: str,
        lhs: str,
        rhs: str,
        owner: str,
    ) -> None:
        super().__init__(
            properties={
                "instance_name": StringAttr(instance_name),
                "sum_out": StringAttr(sum_out),
                "carry_out": StringAttr(carry_out),
                "lhs": StringAttr(lhs),
                "rhs": StringAttr(rhs),
                "owner": StringAttr(owner),
            }
        )


COMP_DIALECT = Dialect("comp", [FullAdderOp, HalfAdderOp], [])
