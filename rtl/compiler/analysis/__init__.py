"""Analysis helpers for the compiler."""

from .func_timing import (
    FUNC_TIMING_CRITICAL_PORT_PAIRS_ATTR,
    FUNC_TIMING_KEEP_FAST_INSTANCES_ATTR,
    FUNC_TIMING_RECLAIM_INSTANCES_ATTR,
    FUNC_TIMING_MAX_DELAY_ATTR,
    analyze_func_timing,
    analyze_module_timing,
)
from .liberty_model import LibertyModel, load_default_liberty_model

__all__ = [
    "FUNC_TIMING_CRITICAL_PORT_PAIRS_ATTR",
    "FUNC_TIMING_KEEP_FAST_INSTANCES_ATTR",
    "FUNC_TIMING_RECLAIM_INSTANCES_ATTR",
    "FUNC_TIMING_MAX_DELAY_ATTR",
    "LibertyModel",
    "analyze_func_timing",
    "analyze_module_timing",
    "load_default_liberty_model",
]
