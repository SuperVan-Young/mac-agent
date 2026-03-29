"""xDSL definitions for the arith dialect."""

from __future__ import annotations

from enum import auto
from typing import ClassVar

from xdsl.dialects.builtin import StringAttr
from xdsl.ir import Attribute, Dialect, ParametrizedAttribute, SSAValue
from xdsl.irdl import (
    IRDLOperation,
    irdl_attr_definition,
    prop_def,
    irdl_op_definition,
    var_operand_def,
    var_result_def,
)
from xdsl.parser import AttrParser
from xdsl.printer import Printer
from xdsl.utils.exceptions import VerifyException
from xdsl.utils.str_enum import StrEnum

from ...ir import WireType, bit_wire_type


class MultiplierImplementation(StrEnum):
    ARRAY = auto()


class PartialProductGeneratorImplementation(StrEnum):
    AND_GRID = auto()


class CompressorTreeImplementation(StrEnum):
    DADDA = auto()
    WALLACE = auto()


class PrefixTreeImplementation(StrEnum):
    RIPPLE = auto()
    KOGGE_STONE = auto()


class _ImplementationAttr(ParametrizedAttribute):
    value: StringAttr
    ALLOWED_VALUES: ClassVar[tuple[str, ...]] = ()

    def __init__(self, value: str | StringAttr) -> None:
        if not isinstance(value, StringAttr):
            value = StringAttr(value)
        super().__init__(value)

    @classmethod
    def parse_parameters(cls, parser: AttrParser) -> list[Attribute]:
        with parser.in_angle_brackets():
            return [StringAttr(parser.parse_identifier())]

    def print_parameters(self, printer: Printer) -> None:
        with printer.in_angle_brackets():
            printer.print_string(self.value.data)

    def verify(self) -> None:
        if self.value.data not in self.ALLOWED_VALUES:
            allowed = ", ".join(repr(value) for value in self.ALLOWED_VALUES)
            raise VerifyException(f"{self.name} expects one of {allowed}, got {self.value.data!r}")


@irdl_attr_definition
class MultiplierImplementationAttr(_ImplementationAttr):
    name = "arith.multiplier_impl"
    ALLOWED_VALUES = tuple(value.value for value in MultiplierImplementation)


@irdl_attr_definition
class PartialProductGeneratorImplementationAttr(_ImplementationAttr):
    name = "arith.ppg_impl"
    ALLOWED_VALUES = tuple(value.value for value in PartialProductGeneratorImplementation)


@irdl_attr_definition
class CompressorTreeImplementationAttr(_ImplementationAttr):
    name = "arith.compressor_impl"
    ALLOWED_VALUES = tuple(value.value for value in CompressorTreeImplementation)


@irdl_attr_definition
class PrefixTreeImplementationAttr(_ImplementationAttr):
    name = "arith.prefix_impl"
    ALLOWED_VALUES = tuple(value.value for value in PrefixTreeImplementation)


@irdl_op_definition
class MultiplierOp(IRDLOperation):
    """High-level multiplier op that can be decomposed structurally later."""

    name = "arith.multiplier"

    inputs = var_operand_def(WireType)
    implementation = prop_def(MultiplierImplementationAttr)
    outputs = var_result_def(WireType)

    def __init__(
        self,
        *,
        inputs: list[SSAValue],
        output_names: list[str],
        output_types: list[WireType] | None = None,
        implementation: MultiplierImplementation | MultiplierImplementationAttr | str = MultiplierImplementation.ARRAY,
    ) -> None:
        if isinstance(implementation, str):
            implementation = MultiplierImplementation(implementation)
        if not isinstance(implementation, MultiplierImplementationAttr):
            implementation = MultiplierImplementationAttr(implementation)
        super().__init__(
            operands=[inputs],
            properties={"implementation": implementation},
            result_types=[[*(output_types or [bit_wire_type(name) for name in output_names])]],
        )


@irdl_op_definition
class PartialProductGeneratorOp(IRDLOperation):
    name = "arith.partial_product_generator"

    inputs = var_operand_def(WireType)
    implementation = prop_def(PartialProductGeneratorImplementationAttr)
    owner = prop_def(StringAttr)
    outputs = var_result_def(WireType)

    def __init__(
        self,
        *,
        implementation: (
            PartialProductGeneratorImplementation
            | PartialProductGeneratorImplementationAttr
            | str
        ) = PartialProductGeneratorImplementation.AND_GRID,
        inputs: list[SSAValue],
        output_names: list[str],
        output_types: list[WireType] | None = None,
        owner: str = "arith.partial_product_generator",
    ) -> None:
        if isinstance(implementation, str):
            implementation = PartialProductGeneratorImplementation(implementation)
        if not isinstance(implementation, PartialProductGeneratorImplementationAttr):
            implementation = PartialProductGeneratorImplementationAttr(implementation)
        super().__init__(
            operands=[inputs],
            properties={
                "implementation": implementation,
                "owner": StringAttr(owner),
            },
            result_types=[[*(output_types or [bit_wire_type(name) for name in output_names])]],
        )


@irdl_op_definition
class CompressorTreeOp(IRDLOperation):
    """High-level compressor-tree op before binding to a concrete cell graph."""

    name = "arith.compressor_tree"

    inputs = var_operand_def(WireType)
    implementation = prop_def(CompressorTreeImplementationAttr)
    owner = prop_def(StringAttr)
    outputs = var_result_def(WireType)

    def __init__(
        self,
        *,
        implementation: CompressorTreeImplementation | CompressorTreeImplementationAttr | str,
        inputs: list[SSAValue],
        output_names: list[str],
        output_types: list[WireType] | None = None,
        owner: str = "arith.compressor_tree",
    ) -> None:
        if isinstance(implementation, str):
            implementation = CompressorTreeImplementation(implementation)
        if not isinstance(implementation, CompressorTreeImplementationAttr):
            implementation = CompressorTreeImplementationAttr(implementation)
        super().__init__(
            operands=[inputs],
            properties={
                "implementation": implementation,
                "owner": StringAttr(owner),
            },
            result_types=[[*(output_types or [bit_wire_type(name) for name in output_names])]],
        )


@irdl_op_definition
class PrefixTreeOp(IRDLOperation):
    name = "arith.prefix_tree"

    inputs = var_operand_def(WireType)
    implementation = prop_def(PrefixTreeImplementationAttr)
    owner = prop_def(StringAttr)
    outputs = var_result_def(WireType)

    def __init__(
        self,
        *,
        implementation: PrefixTreeImplementation | PrefixTreeImplementationAttr | str = PrefixTreeImplementation.RIPPLE,
        inputs: list[SSAValue],
        output_names: list[str],
        output_types: list[WireType] | None = None,
        owner: str = "arith.prefix_tree",
    ) -> None:
        if isinstance(implementation, str):
            implementation = PrefixTreeImplementation(implementation)
        if not isinstance(implementation, PrefixTreeImplementationAttr):
            implementation = PrefixTreeImplementationAttr(implementation)
        super().__init__(
            operands=[inputs],
            properties={
                "implementation": implementation,
                "owner": StringAttr(owner),
            },
            result_types=[[*(output_types or [bit_wire_type(name) for name in output_names])]],
        )


ARITH_DIALECT = Dialect(
    "arith",
    [MultiplierOp, PartialProductGeneratorOp, CompressorTreeOp, PrefixTreeOp],
    [
        MultiplierImplementationAttr,
        PartialProductGeneratorImplementationAttr,
        CompressorTreeImplementationAttr,
        PrefixTreeImplementationAttr,
    ],
)
