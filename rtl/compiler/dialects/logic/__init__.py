"""Logic dialect entry points."""

from .ops import (
    And2Op,
    Ao21Op,
    ConstantOp,
    FullAdderOp,
    HalfAdderOp,
    InputPortOp,
    InstanceOp,
    LOGIC_DIALECT,
    OutputPortOp,
    Or2Op,
    Xor2Op,
    decode_connections,
)

__all__ = [
    "And2Op",
    "Ao21Op",
    "ConstantOp",
    "FullAdderOp",
    "HalfAdderOp",
    "InputPortOp",
    "InstanceOp",
    "LOGIC_DIALECT",
    "OutputPortOp",
    "Or2Op",
    "Xor2Op",
    "decode_connections",
]
