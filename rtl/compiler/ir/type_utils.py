"""Helpers for the shared RTL wire type."""

from __future__ import annotations

from dataclasses import dataclass
import re
from math import prod
from typing import Iterable

from xdsl.ir import Attribute, SSAValue

from .types import WireType


_BIT_SELECT_RE = re.compile(r"^(?P<base>[A-Za-z_]\w*)\[(?P<index>\d+)\]$")


@dataclass(frozen=True)
class PortDecl:
    name: str
    width: int


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


def signal_decls_from_wires(wires: Iterable[Attribute | SSAValue]) -> list[PortDecl]:
    order: list[str] = []
    widths: dict[str, int] = {}
    for wire in wires:
        name = require_wire_name(wire)
        width = get_wire_width(wire)
        match = _BIT_SELECT_RE.match(name)
        if match is not None and width == 1:
            base = match.group("base")
            width = int(match.group("index")) + 1
        else:
            base = name
        if base not in widths:
            order.append(base)
            widths[base] = width
            continue
        widths[base] = max(widths[base], width)
    return [PortDecl(name=name, width=widths[name]) for name in order]


def expand_signal_decl_refs(signal: PortDecl) -> list[str]:
    if signal.width == 1:
        return [signal.name]
    return [f"{signal.name}[{bit}]" for bit in range(signal.width)]
