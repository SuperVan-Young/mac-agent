"""Helpers for the shared RTL wire type and value naming."""

from __future__ import annotations

from collections.abc import Sequence

from xdsl.dialects.builtin import DictionaryAttr, StringAttr
from xdsl.ir import Attribute, SSAValue

from ..signals import SignalDecl
from .types import WireType


RTL_NAME_ATTR = "rtl.name_hint"


def wire_type(*dims: int) -> WireType:
    return WireType(dims)


def bit_wire_type() -> WireType:
    return WireType((1,))


def get_wire_dims(attr: Attribute) -> tuple[int, ...]:
    if not isinstance(attr, WireType):
        raise AssertionError(f"Expected rtl.wire type, got {attr}")
    return tuple(dim.data for dim in attr.shape)


def expand_signal_decl_refs(signal: SignalDecl) -> list[str]:
    if signal.width == 1:
        return [signal.name]
    return [f"{signal.name}[{bit}]" for bit in range(signal.width)]


def make_name_hint_attr(name: str) -> DictionaryAttr:
    return DictionaryAttr({RTL_NAME_ATTR: StringAttr(name)})


def get_name_hint(attr: DictionaryAttr | None) -> str | None:
    if attr is None:
        return None
    value = attr.data.get(RTL_NAME_ATTR)
    if not isinstance(value, StringAttr):
        return None
    return value.data


def set_name_hint(value: SSAValue, name: str) -> None:
    value.name_hint = name
