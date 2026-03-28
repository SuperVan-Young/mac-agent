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


ASAP7_DIALECT = Dialect("asap7", [Xor2Op, And2Op], [])
