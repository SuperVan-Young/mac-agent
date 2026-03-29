"""Shared IR types and helpers for the RTL compiler."""

from .types import RTL_IR_DIALECT, WireType
from .type_utils import (
    RTL_NAME_ATTR,
    bit_wire_type,
    expand_signal_decl_refs,
    get_name_hint,
    get_wire_dims,
    make_name_hint_attr,
    set_name_hint,
    wire_type,
)

__all__ = [
    "RTL_IR_DIALECT",
    "RTL_NAME_ATTR",
    "WireType",
    "bit_wire_type",
    "expand_signal_decl_refs",
    "get_name_hint",
    "get_wire_dims",
    "make_name_hint_attr",
    "set_name_hint",
    "wire_type",
]
