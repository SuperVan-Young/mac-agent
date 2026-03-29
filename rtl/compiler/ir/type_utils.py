"""Helpers for the shared RTL wire type."""

from __future__ import annotations

from math import prod

from xdsl.ir import Attribute, SSAValue

from ..signals import SignalDecl
from .types import WireType


def wire_type(*dims: int, name: str = "") -> WireType:
    return WireType(dims, wire_name=name)


def bit_wire_type(name: str = "") -> WireType:
    return WireType((1,), wire_name=name)


def get_wire_dims(attr: Attribute | SSAValue) -> tuple[int, ...]:
    wire = attr.type if isinstance(attr, SSAValue) else attr
    if not isinstance(wire, WireType):
        raise AssertionError(f"Expected rtl.wire type, got {wire}")
    return tuple(dim.data for dim in wire.shape)


def get_wire_width(attr: Attribute | SSAValue) -> int:
    return prod(get_wire_dims(attr))


def get_wire_name(attr: Attribute | SSAValue) -> str | None:
    wire = attr.type if isinstance(attr, SSAValue) else attr
    if not isinstance(wire, WireType):
        raise AssertionError(f"Expected rtl.wire type, got {wire}")
    if not wire.wire_name.data:
        return None
    return wire.wire_name.data


def require_wire_name(attr: Attribute | SSAValue) -> str:
    name = get_wire_name(attr)
    if name is None:
        raise AssertionError(f"Expected named rtl.wire, got {attr.type if isinstance(attr, SSAValue) else attr}")
    return name


def expand_signal_decl_refs(signal: SignalDecl) -> list[str]:
    if signal.width == 1:
        return [signal.name]
    return [f"{signal.name}[{bit}]" for bit in range(signal.width)]
