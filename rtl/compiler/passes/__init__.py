"""Compiler passes."""

from .annotate_func_port_criticality import AnnotateFuncPortCriticalityPass
from .emit_verilog import emit_verilog
from .lower_arith_to_logic import LowerArithToLogicPass
from .lower_logic_to_asap7 import LowerLogicToAsap7Pass
from .lower_multiplier_to_arith_parts import LowerMultiplierToArithPartsPass
from .region_scoped_cell_sizing import RegionScopedCellSizingPass
from .verify_post_arith_to_logic import PostArithToLogicVerificationPass
from .verify_post_logic_to_physical import PostLogicToPhysicalVerificationPass

__all__ = [
    "AnnotateFuncPortCriticalityPass",
    "LowerArithToLogicPass",
    "LowerLogicToAsap7Pass",
    "LowerMultiplierToArithPartsPass",
    "RegionScopedCellSizingPass",
    "PostArithToLogicVerificationPass",
    "PostLogicToPhysicalVerificationPass",
    "emit_verilog",
]
