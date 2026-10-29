"""Exercise real simulation scheduling and failure detection with Icarus."""
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class PipelineSimulationTest(unittest.TestCase):
    def run_sim(self, dut, cycles, output):
        return subprocess.run(
            [sys.executable, str(ROOT / "eval/sim/run.py"), str(dut),
             "--cycles", str(cycles), "--random-count", "20", "--output", str(output)],
            text=True, capture_output=True,
        )

    def test_baseline_pipeline_and_wrong_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            baseline = ROOT / "rtl/baseline/baseline.v"
            for cycles in (1, 2, 3, 5):
                with self.subTest(cycles=cycles):
                    result = self.run_sim(baseline, cycles, tmp / str(cycles))
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertIn("SIMULATION_STATUS=PASS", result.stdout)
            wrong = tmp / "wrong.v"
            wrong.write_text(baseline.read_text().replace(
                "assign sum_out = mult_out + C;", "assign sum_out = mult_out + C + 1'b1;"
            ))
            result = self.run_sim(wrong, 2, tmp / "wrong")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("SIMULATION_STATUS=FAIL", result.stderr)

    def test_conflicting_verdict_is_rejected(self):
        sys.path.insert(0, str(ROOT / 'eval'))
        from common import EvaluationError, load_config, tool
        from sim.run import simulate
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            fake = tmp / 'vvp'
            fake.write_text('#!/bin/sh\nprintf "RESULT: PASS\\nRESULT: FAIL\\nDUT=baseline.v VECTORS=5010\\n"\n')
            fake.chmod(0o755)
            with patch('sim.run.tool', side_effect=lambda name, cfg: str(fake) if name == 'vvp' else tool(name, cfg)):
                with self.assertRaises(EvaluationError):
                    simulate(ROOT / 'rtl/baseline/baseline.v', tmp / 'run', load_config())


if __name__ == "__main__":
    unittest.main()
