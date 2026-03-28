"""xDSL definitions for the arith dialect."""

from __future__ import annotations

from xdsl.dialects.builtin import ArrayAttr, StringAttr
from xdsl.irdl import IRDLOperation, prop_def, irdl_op_definition
from xdsl.ir import Dialect


def _encode_columns(columns: dict[int, list[str]]) -> ArrayAttr[StringAttr]:
    encoded = []
    for column, signals in sorted(columns.items()):
        encoded.append(StringAttr(f"c{column}=" + ",".join(signals)))
    return ArrayAttr(encoded)


def decode_columns(attr: ArrayAttr[StringAttr]) -> dict[int, list[str]]:
    columns: dict[int, list[str]] = {}
    for item in attr:
        raw = item.data
        column_tag, _, payload = raw.partition("=")
        column = int(column_tag[1:])
        columns[column] = [signal for signal in payload.split(",") if signal]
    return columns


@irdl_op_definition
class MultiplierOp(IRDLOperation):
    """High-level multiplier op that can be decomposed structurally later."""

    name = "arith.multiplier"

    implementation = prop_def(StringAttr)

    def __init__(self, *, implementation: str = "array") -> None:
        super().__init__(properties={"implementation": StringAttr(implementation)})


@irdl_op_definition
class PartialProductGeneratorOp(IRDLOperation):
    name = "arith.partial_product_generator"

    implementation = prop_def(StringAttr)

    def __init__(self, *, implementation: str = "and_grid") -> None:
        super().__init__(properties={"implementation": StringAttr(implementation)})


@irdl_op_definition
class CompressorTreeOp(IRDLOperation):
    """High-level compressor-tree op before binding to a concrete cell graph."""

    name = "arith.compressor_tree"

    reduction_type = prop_def(StringAttr)
    columns = prop_def(ArrayAttr[StringAttr])
    owner = prop_def(StringAttr)

    def __init__(
        self,
        *,
        reduction_type: str,
        columns: dict[int, list[str]],
        owner: str = "arith.compressor_tree",
    ) -> None:
        super().__init__(
            properties={
                "reduction_type": StringAttr(reduction_type),
                "columns": _encode_columns(columns),
                "owner": StringAttr(owner),
            }
        )


@irdl_op_definition
class PrefixTreeOp(IRDLOperation):
    name = "arith.prefix_tree"

    implementation = prop_def(StringAttr)

    def __init__(self, *, implementation: str = "kogge_stone") -> None:
        super().__init__(properties={"implementation": StringAttr(implementation)})


ARITH_DIALECT = Dialect(
    "arith",
    [MultiplierOp, PartialProductGeneratorOp, CompressorTreeOp, PrefixTreeOp],
    [],
)
