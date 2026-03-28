"""Logic dialect entry points."""

from .ops import (
    And2Op,
    Ao21Op,
    FullAdderOp,
    HalfAdderOp,
    InstanceOp,
    LOGIC_DIALECT,
    Or2Op,
    Xor2Op,
    decode_connections,
)

__all__ = [
    "And2Op",
    "Ao21Op",
    "FullAdderOp",
    "HalfAdderOp",
    "InstanceOp",
    "LOGIC_DIALECT",
    "Or2Op",
    "Xor2Op",
    "decode_connections",
]
