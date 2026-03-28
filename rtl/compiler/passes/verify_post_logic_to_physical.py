"""Verification pass for the logic -> physical boundary."""

from __future__ import annotations

from dataclasses import dataclass

from xdsl.context import Context
from xdsl.dialects.builtin import ModuleOp
from xdsl.passes import ModulePass


@dataclass(frozen=True)
class PostLogicToPhysicalVerificationPass(ModulePass):
    name = "verify-post-logic-to-physical"

    def apply(self, ctx: Context, op: ModuleOp) -> None:
        del ctx
        remaining = [inner.name for inner in op.ops if inner.name.startswith("logic.")]
        if remaining:
            raise AssertionError(
                "PostLogicToPhysicalVerificationPass found remaining logic ops: "
                + ", ".join(remaining)
            )
