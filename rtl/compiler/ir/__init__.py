"""Shared IR types and helpers for the RTL compiler."""

from .types import RTL_IR_DIALECT, WireType
from .type_utils import (
    PortDecl,
    bit_wire_type,
    expand_signal_decl_refs,
    get_wire_dims,
    get_wire_name,
    get_wire_width,
    require_wire_name,
    signal_decls_from_wires,
    wire_type,
)

__all__ = [
    "RTL_IR_DIALECT",
    "WireType",
    "PortDecl",
    "bit_wire_type",
    "expand_signal_decl_refs",
    "get_wire_dims",
    "get_wire_name",
    "get_wire_width",
    "require_wire_name",
    "signal_decls_from_wires",
    "wire_type",
]
