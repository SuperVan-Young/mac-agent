"""Pass protocol and pipeline driver."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from .context import CompilerContext


class CompilerPass(Protocol):
    name: str

    def run(self, module: Any, context: CompilerContext) -> Any:
        """Apply the pass and return the new module object."""


@dataclass
class PassManager:
    passes: list[CompilerPass] = field(default_factory=list)

    def add_pass(self, compiler_pass: CompilerPass) -> None:
        self.passes.append(compiler_pass)

    def run(self, module: Any, context: CompilerContext) -> Any:
        current = module
        for compiler_pass in self.passes:
            context.note(f"running pass: {compiler_pass.name}")
            current = compiler_pass.run(current, context)
        return current


def build_default_pipeline() -> PassManager:
    """Return the intended first-pass pipeline ordering."""

    from .passes.annotate_timing import AnnotateTimingPass
    from .passes.bind_asap7 import BindAsap7Pass
    from .passes.build_ppg import BuildPartialProductGraphPass
    from .passes.legalize_nodes import LegalizeCompressorNodesPass
    from .passes.materialize_ct import MaterializeCompressorTreePass
    from .passes.rewrite_dadda import RewriteCtToDaddaPass

    return PassManager(
        passes=[
            BuildPartialProductGraphPass(),
            MaterializeCompressorTreePass(),
            RewriteCtToDaddaPass(),
            LegalizeCompressorNodesPass(),
            BindAsap7Pass(),
            AnnotateTimingPass(),
        ]
    )
