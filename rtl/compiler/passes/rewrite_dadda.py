"""Rewrite a compressor tree into a Dadda-style target shape."""

from __future__ import annotations

from dataclasses import dataclass

from ..context import CompilerContext
from ..dialects.arith import ArithModule


@dataclass
class RewriteCtToDaddaPass:
    name: str = "rewrite_ct_to_dadda"

    def run(self, module: ArithModule, context: CompilerContext) -> ArithModule:
        module.mac.compressor_tree.reduction_type = "dadda"
        module.mac.compressor_tree.attributes["pattern_owner"] = "arith.compressor_tree"
        context.metadata["ct_strategy"] = "dadda"
        return module
