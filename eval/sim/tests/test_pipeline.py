"""Exercise real simulation scheduling and failure detection with Icarus."""
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


class PipelineSimulationTest(unittest.TestCase):
    def run_sim(self, dut, cycles, output):
        return subprocess.run(
            ["bash", str(ROOT / "eval/sim/run_rtl_sim.sh"), "-d", str(dut),
             "-p", str(cycles), "-n", "20", "-o", str(output)],
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
            self.assertIn("SIMULATION_STATUS=FAIL", result.stdout)


if __name__ == "__main__":
    unittest.main()
