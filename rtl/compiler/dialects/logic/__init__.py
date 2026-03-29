"""Logic dialect entry points."""

from .ops import (
    And2Op,
    Ao21Op,
    ConstantOp,
    decode_port_names,
    FullAdderOp,
    HalfAdderOp,
    InputPortOp,
    InstanceOp,
    LOGIC_DIALECT,
    OutputPortOp,
    Or2Op,
    Xor2Op,
)

__all__ = [
    "And2Op",
    "Ao21Op",
    "ConstantOp",
    "decode_port_names",
    "FullAdderOp",
    "HalfAdderOp",
    "InputPortOp",
    "InstanceOp",
    "LOGIC_DIALECT",
    "OutputPortOp",
    "Or2Op",
    "Xor2Op",
]
