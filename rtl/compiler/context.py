"""Shared compiler configuration and execution context."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class CompilerConfig:
    top_name: str = "mac16x16p32"
    a_width: int = 16
    b_width: int = 16
    acc_width: int = 32
    output_path: Path = Path("mac16x16p32.v")
    use_xdsl_pipeline: bool = False
    emit_debug_artifacts: bool = False
    pdk: str = "asap7"
    reduction_type: str = "dadda"


@dataclass
class CompilerContext:
    config: CompilerConfig = field(default_factory=CompilerConfig)
    metadata: dict[str, object] = field(default_factory=dict)
    diagnostics: list[str] = field(default_factory=list)

    def note(self, message: str) -> None:
        self.diagnostics.append(message)
