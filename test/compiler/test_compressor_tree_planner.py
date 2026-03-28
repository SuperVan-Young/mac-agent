from __future__ import annotations

from rtl.compiler.passes.lower_multiplier_to_arith_parts import _plan_compressor_tree


def test_plan_compressor_tree_uses_latest_selected_input_as_cin() -> None:
    stages, _, _ = _plan_compressor_tree(
        {
            2: [
                "pp_0_2",
                "pp_1_1",
                "pp_2_0",
                "C[2]",
                "C[3]",
            ]
        }
    )

    kind, _, lhs, rhs, cin, _, _ = stages[0]
    assert kind == "fa"
    assert (lhs, rhs) == ("C[2]", "C[3]")
    assert cin == "pp_0_2"
