"""Verification pass for the arith -> logic boundary."""

from __future__ import annotations

from dataclasses import dataclass

from xdsl.context import Context
from xdsl.dialects.builtin import ModuleOp
from xdsl.passes import ModulePass


@dataclass(frozen=True)
class PostArithToLogicVerificationPass(ModulePass):
    name = "verify-post-arith-to-logic"

    def apply(self, ctx: Context, op: ModuleOp) -> None:
        del ctx
        remaining = [inner.name for inner in op.ops if inner.name.startswith("arith.")]
        if remaining:
            raise AssertionError(
                "PostArithToLogicVerificationPass found remaining arith ops: "
                + ", ".join(remaining)
            )
