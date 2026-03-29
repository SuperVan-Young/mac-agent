"""xDSL definitions for the arith dialect."""

from __future__ import annotations

from xdsl.dialects.builtin import StringAttr
from xdsl.ir import Dialect, SSAValue
from xdsl.irdl import (
    IRDLOperation,
    prop_def,
    irdl_op_definition,
    result_def,
    var_operand_def,
    var_result_def,
)

from ...ir import WireType, bit_wire_type


@irdl_op_definition
class MultiplierOp(IRDLOperation):
    """High-level multiplier op that can be decomposed structurally later."""

    name = "arith.multiplier"

    implementation = prop_def(StringAttr)

    def __init__(self, *, implementation: str = "array") -> None:
        super().__init__(properties={"implementation": StringAttr(implementation)})


@irdl_op_definition
class PartialProductGeneratorOp(IRDLOperation):
    name = "arith.partial_product_generator"

    inputs = var_operand_def(WireType)
    implementation = prop_def(StringAttr)
    owner = prop_def(StringAttr)
    outputs = var_result_def(WireType)

    def __init__(
        self,
        *,
        implementation: str = "and_grid",
        inputs: list[SSAValue],
        output_names: list[str],
        output_types: list[WireType] | None = None,
        owner: str = "arith.partial_product_generator",
    ) -> None:
        super().__init__(
            operands=[inputs],
            properties={
                "implementation": StringAttr(implementation),
                "owner": StringAttr(owner),
            },
            result_types=[[*(output_types or [bit_wire_type(name) for name in output_names])]],
        )


@irdl_op_definition
class CompressorTreeOp(IRDLOperation):
    """High-level compressor-tree op before binding to a concrete cell graph."""

    name = "arith.compressor_tree"

    inputs = var_operand_def(WireType)
    implementation = prop_def(StringAttr)
    owner = prop_def(StringAttr)
    outputs = var_result_def(WireType)

    def __init__(
        self,
        *,
        implementation: str,
        inputs: list[SSAValue],
        output_names: list[str],
        output_types: list[WireType] | None = None,
        owner: str = "arith.compressor_tree",
    ) -> None:
        super().__init__(
            operands=[inputs],
            properties={
                "implementation": StringAttr(implementation),
                "owner": StringAttr(owner),
            },
            result_types=[[*(output_types or [bit_wire_type(name) for name in output_names])]],
        )


@irdl_op_definition
class PrefixTreeOp(IRDLOperation):
    name = "arith.prefix_tree"

    inputs = var_operand_def(WireType)
    implementation = prop_def(StringAttr)
    owner = prop_def(StringAttr)
    outputs = var_result_def(WireType)

    def __init__(
        self,
        *,
        implementation: str = "ripple",
        inputs: list[SSAValue],
        output_names: list[str],
        output_types: list[WireType] | None = None,
        owner: str = "arith.prefix_tree",
    ) -> None:
        super().__init__(
            operands=[inputs],
            properties={
                "implementation": StringAttr(implementation),
                "owner": StringAttr(owner),
            },
            result_types=[[*(output_types or [bit_wire_type(name) for name in output_names])]],
        )


ARITH_DIALECT = Dialect(
    "arith",
    [MultiplierOp, PartialProductGeneratorOp, CompressorTreeOp, PrefixTreeOp],
    [],
)
