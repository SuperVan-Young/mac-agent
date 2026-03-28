"""Compatibility helpers for optional xDSL integration."""

from __future__ import annotations

from dataclasses import dataclass


try:
    import xdsl  # type: ignore  # noqa: F401

    XDSL_AVAILABLE = True
except ImportError:
    XDSL_AVAILABLE = False


@dataclass(frozen=True)
class XdslRequirement:
    """Represents an optional dependency gate for xDSL-backed features."""

    feature: str

    def ensure(self) -> None:
        if XDSL_AVAILABLE:
            return
        raise RuntimeError(
            f"{self.feature} requires the optional dependency 'xdsl'. "
            "Install it with `pip install -e .[compiler]`."
        )
