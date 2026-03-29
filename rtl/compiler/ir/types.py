"""Shared RTL SSA types."""

from __future__ import annotations

from collections.abc import Sequence

from xdsl.dialects.builtin import ArrayAttr, IntAttr, StringAttr
from xdsl.ir import Attribute, Dialect, ParametrizedAttribute, TypeAttribute
from xdsl.irdl import irdl_attr_definition
from xdsl.parser import AttrParser
from xdsl.printer import Printer
from xdsl.utils.exceptions import VerifyException


@irdl_attr_definition
class WireType(ParametrizedAttribute, TypeAttribute):
    """A named wire with an arbitrary packed shape."""

    name = "rtl.wire"

    wire_name: StringAttr
    shape: ArrayAttr[IntAttr]

    def __init__(
        self,
        shape: Sequence[int] | ArrayAttr[IntAttr],
        wire_name: str | StringAttr = "",
    ) -> None:
        if not isinstance(shape, ArrayAttr):
            shape = ArrayAttr(IntAttr(dim) for dim in shape)
        if not isinstance(wire_name, StringAttr):
            wire_name = StringAttr(wire_name)
        super().__init__(wire_name, shape)

    @classmethod
    def parse_parameters(cls, parser: AttrParser) -> list[Attribute]:
        dims: list[int] = []
        with parser.in_angle_brackets():
            wire_name = ""
            maybe_name = parser.parse_optional_str_literal()
            if maybe_name is not None:
                wire_name = maybe_name
                parser.parse_characters(":")
            dims.append(parser.parse_integer(allow_boolean=False))
            while parser.parse_optional_characters("x") is not None:
                dims.append(parser.parse_integer(allow_boolean=False))
        return [StringAttr(wire_name), ArrayAttr(IntAttr(dim) for dim in dims)]

    def print_parameters(self, printer: Printer) -> None:
        with printer.in_angle_brackets():
            if self.wire_name.data:
                printer.print_attribute(self.wire_name)
                printer.print_string(":")
            printer.print_string("x".join(str(dim.data) for dim in self.shape))

    def verify(self) -> None:
        dims = tuple(dim.data for dim in self.shape)
        if not dims:
            raise VerifyException("rtl.wire requires at least one dimension")
        if any(dim <= 0 for dim in dims):
            raise VerifyException(f"rtl.wire dimensions must be positive, got {dims}")


RTL_IR_DIALECT = Dialect("rtl", [], [WireType])
