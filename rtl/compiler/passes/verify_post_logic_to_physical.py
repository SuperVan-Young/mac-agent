"""Verification pass for the logic -> physical boundary."""

from __future__ import annotations

from dataclasses import dataclass

from xdsl.context import Context
from xdsl.dialects.builtin import ModuleOp
from xdsl.ir import Operation
from xdsl.passes import ModulePass


def _walk_ops(op: Operation):
    yield op
    for region in op.regions:
        for block in region.blocks:
            for inner in block.ops:
                yield from _walk_ops(inner)


@dataclass(frozen=True)
class PostLogicToPhysicalVerificationPass(ModulePass):
    name = "verify-post-logic-to-physical"

    def apply(self, ctx: Context, op: ModuleOp) -> None:
        del ctx
        remaining = [
            inner.name
            for inner in _walk_ops(op)
            if inner.name.startswith("logic.") and inner.name != "logic.instance"
        ]
        if remaining:
            raise AssertionError(
                "PostLogicToPhysicalVerificationPass found remaining logic ops: "
                + ", ".join(remaining)
            )
