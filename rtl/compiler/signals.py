"""Basic signal declarations used by the compiler and Verilog emitter."""

from __future__ import annotations

from dataclasses import dataclass

from xdsl.dialects.builtin import ArrayAttr, StringAttr


@dataclass(frozen=True)
class SignalDecl:
    name: str
    width: int
    kind: str


def encode_signal_decl(signal: SignalDecl) -> StringAttr:
    return StringAttr(f"{signal.kind}:{signal.name}:{signal.width}")


def decode_signal_decl(attr: StringAttr) -> SignalDecl:
    kind, name, width = attr.data.split(":", 2)
    return SignalDecl(name=name, width=int(width), kind=kind)


def encode_signal_decls(signals: list[SignalDecl]) -> ArrayAttr[StringAttr]:
    return ArrayAttr(encode_signal_decl(signal) for signal in signals)


def decode_signal_decls(attr: ArrayAttr[StringAttr]) -> list[SignalDecl]:
    return [decode_signal_decl(item) for item in attr]
