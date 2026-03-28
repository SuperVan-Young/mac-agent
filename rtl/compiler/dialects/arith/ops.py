"""xDSL definitions for the arith dialect."""

from __future__ import annotations

from xdsl.dialects.builtin import ArrayAttr, StringAttr
from xdsl.irdl import IRDLOperation, prop_def, irdl_op_definition
from xdsl.ir import Dialect


def _encode_columns(columns: dict[int, list[str]]) -> ArrayAttr[StringAttr]:
    return ArrayAttr(
        StringAttr(f"c{column}=" + ",".join(signals))
        for column, signals in sorted(columns.items())
    )


def decode_columns(attr: ArrayAttr[StringAttr]) -> dict[int, list[str]]:
    columns: dict[int, list[str]] = {}
    for item in attr:
        raw = item.data
        column_tag, _, payload = raw.partition("=")
        column = int(column_tag[1:])
        columns[column] = [signal for signal in payload.split(",") if signal]
    return columns


def _encode_bit_map(bits: dict[int, str]) -> ArrayAttr[StringAttr]:
    return ArrayAttr(StringAttr(f"b{bit}={signal}") for bit, signal in sorted(bits.items()))


def decode_bit_map(attr: ArrayAttr[StringAttr]) -> dict[int, str]:
    bits: dict[int, str] = {}
    for item in attr:
        raw = item.data
        bit_tag, _, signal = raw.partition("=")
        bits[int(bit_tag[1:])] = signal
    return bits


def _encode_terms(terms: list[tuple[str, str, str]]) -> ArrayAttr[StringAttr]:
    return ArrayAttr(StringAttr(f"{output}={lhs},{rhs}") for output, lhs, rhs in terms)


def decode_terms(attr: ArrayAttr[StringAttr]) -> list[tuple[str, str, str]]:
    terms: list[tuple[str, str, str]] = []
    for item in attr:
        output, _, payload = item.data.partition("=")
        lhs, rhs = payload.split(",", 1)
        terms.append((output, lhs, rhs))
    return terms


def _encode_compressor_ops(
    ops: list[tuple[str, str, str, str, str, str, str]],
) -> ArrayAttr[StringAttr]:
    return ArrayAttr(StringAttr(":".join(op)) for op in ops)


def decode_compressor_ops(
    attr: ArrayAttr[StringAttr],
) -> list[tuple[str, str, str, str, str, str, str]]:
    ops: list[tuple[str, str, str, str, str, str, str]] = []
    for item in attr:
        fields = item.data.split(":")
        if len(fields) != 7:
            raise AssertionError(f"Malformed compressor op encoding: {item.data!r}")
        ops.append(tuple(fields))  # type: ignore[arg-type]
    return ops


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
    terms = prop_def(ArrayAttr[StringAttr])
    owner = prop_def(StringAttr)

    def __init__(
        self,
        *,
        implementation: str = "and_grid",
        terms: list[tuple[str, str, str]] | None = None,
        owner: str = "arith.partial_product_generator",
    ) -> None:
        super().__init__(
            properties={
                "implementation": StringAttr(implementation),
                "terms": _encode_terms(terms or []),
                "owner": StringAttr(owner),
            }
        )


@irdl_op_definition
class CompressorTreeOp(IRDLOperation):
    """High-level compressor-tree op before binding to a concrete cell graph."""

    name = "arith.compressor_tree"

    reduction_type = prop_def(StringAttr)
    columns = prop_def(ArrayAttr[StringAttr])
    stages = prop_def(ArrayAttr[StringAttr])
    owner = prop_def(StringAttr)

    def __init__(
        self,
        *,
        reduction_type: str,
        columns: dict[int, list[str]],
        stages: list[tuple[str, str, str, str, str, str, str]] | None = None,
        owner: str = "arith.compressor_tree",
    ) -> None:
        super().__init__(
            properties={
                "reduction_type": StringAttr(reduction_type),
                "columns": _encode_columns(columns),
                "stages": _encode_compressor_ops(stages or []),
                "owner": StringAttr(owner),
            }
        )


@irdl_op_definition
class PrefixTreeOp(IRDLOperation):
    name = "arith.prefix_tree"

    implementation = prop_def(StringAttr)
    lhs_row = prop_def(ArrayAttr[StringAttr])
    rhs_row = prop_def(ArrayAttr[StringAttr])
    output_name = prop_def(StringAttr)
    owner = prop_def(StringAttr)

    def __init__(
        self,
        *,
        implementation: str = "ripple",
        lhs_row: dict[int, str] | None = None,
        rhs_row: dict[int, str] | None = None,
        output_name: str = "D",
        owner: str = "arith.prefix_tree",
    ) -> None:
        super().__init__(
            properties={
                "implementation": StringAttr(implementation),
                "lhs_row": _encode_bit_map(lhs_row or {}),
                "rhs_row": _encode_bit_map(rhs_row or {}),
                "output_name": StringAttr(output_name),
                "owner": StringAttr(owner),
            }
        )


ARITH_DIALECT = Dialect(
    "arith",
    [MultiplierOp, PartialProductGeneratorOp, CompressorTreeOp, PrefixTreeOp],
    [],
)
