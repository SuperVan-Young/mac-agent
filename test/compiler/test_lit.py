from __future__ import annotations

from pathlib import Path

import pytest

from .lit_runner import discover_mlir_tests, run_mlir_test


TEST_ROOT = Path(__file__).resolve().parent


@pytest.mark.parametrize("path", discover_mlir_tests(TEST_ROOT), ids=lambda path: str(path.relative_to(TEST_ROOT)))
def test_mlir_file(path: Path) -> None:
    run_mlir_test(path)
