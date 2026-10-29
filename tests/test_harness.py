"""Real-tool acceptance, rejection and fixed-revision isolation regressions."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "eval"))
from common import EvaluationError, execute, load_config
from check.run import check_netlist

HEADER = 'module mac16x16p32(input [15:0] A, input [15:0] B, input [31:0] C, output [31:0] D);\n'


class HarnessTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.config = load_config()

    def check(self, source, name):
        dut = self.root / f'{name}.v'
        dut.write_text(source)
        return check_netlist(dut, self.root / name, self.config)

    def run_eval(self, candidate, output, *options, root=ROOT):
        return subprocess.run([sys.executable, str(root / 'eval/run.py'), str(candidate),
                               '--output', str(output), *options], capture_output=True, text=True, timeout=120)

    def test_nested_mapped_baseline(self):
        baseline = (ROOT / 'rtl/baseline/baseline.synth.v').read_text().replace(
            'module mac16x16p32(', 'module mapped_mac(', 1)
        source = HEADER + 'mapped_mac u(A,B,C,D);\nendmodule\n' + baseline
        mapped = self.check(source, 'nested')
        self.assertTrue(mapped.is_file())

    def test_unmapped_and_invalid_structures(self):
        cases = {
            'arithmetic': HEADER + 'assign D=A*B+C; endmodule',
            'nested_behavior': HEADER + 'hidden u(A,B,C,D); endmodule\n' +
                HEADER.replace('mac16x16p32', 'hidden') + 'assign D=A*B+C; endmodule',
            'process': HEADER + 'reg [31:0] r; always @* r = C; assign D=r; endmodule',
            'spoof': HEADER + 'INVx1_ASAP7_75t_R u(.A(A[0]),.Y(D[0])); assign D[31:1]=0; endmodule\n' +
                'module INVx1_ASAP7_75t_R(input A,output Y); assign Y=A; endmodule',
            'unknown': HEADER + 'fake u(.A(A),.Y(D)); endmodule',
            'loop': HEADER + 'wire n; INVx1_ASAP7_75t_R u(.A(n),.Y(n)); assign D={32{n}}; endmodule',
            'undriven': HEADER + 'wire n; INVx1_ASAP7_75t_R u(.A(n),.Y(D[0])); assign D[31:1]=0; endmodule',
            'multi_driver': HEADER + 'INVx1_ASAP7_75t_R u(.A(A[0]),.Y(D[0])); '
                'INVx1_ASAP7_75t_R v(.A(B[0]),.Y(D[0])); assign D[31:1]=0; endmodule',
            'external': '`include "other.v"\n' + HEADER + 'assign D=C; endmodule',
        }
        for name, source in cases.items():
            with self.subTest(name=name), self.assertRaises(EvaluationError):
                self.check(source, name)

    def test_wrong_function_and_stale_output(self):
        candidate = self.root / 'wrong.v'
        candidate.write_text(HEADER + 'assign D=C; endmodule')
        out = self.root / 'run'
        result = self.run_eval(candidate, out, '--dev')
        self.assertEqual(result.returncode, 1, result.stderr)
        summary = json.loads((out / 'summary.json').read_text())
        self.assertEqual(summary['failed_stage'], 'sim')
        self.assertEqual(summary['validity'], 'invalid')
        self.assertIsNone(summary['metrics'])
        original = (out / 'summary.json').read_bytes()
        again = self.run_eval(ROOT / 'rtl/baseline/baseline.synth.v', out, '--dev')
        self.assertEqual(again.returncode, 2)
        self.assertEqual(original, (out / 'summary.json').read_bytes())

    def test_timeout(self):
        with self.assertRaises(EvaluationError) as context:
            execute([sys.executable, '-c', 'import time; time.sleep(30)'],
                    self.root / 'timeout.log', 0.05)
        self.assertEqual(context.exception.status, 'timeout')

    def test_missing_candidate_has_result(self):
        out = self.root / 'missing'
        result = self.run_eval(self.root / 'absent.v', out, '--dev')
        self.assertEqual(result.returncode, 2)
        summary = json.loads((out / 'summary.json').read_text())
        self.assertEqual(summary['execution_status'], 'error')
        self.assertFalse(summary['pass'])

    def test_stage_timeout_is_not_a_pass(self):
        config = self.config
        config['timeouts_sec']['check'] = 0.00001
        path = self.root / 'timeout-config.json'
        path.write_text(json.dumps(config))
        out = self.root / 'timeout-run'
        result = self.run_eval(ROOT / 'rtl/baseline/baseline.synth.v', out, '--dev', '--config', str(path))
        self.assertEqual(result.returncode, 3, result.stderr)
        summary = json.loads((out / 'summary.json').read_text())
        self.assertEqual(summary['execution_status'], 'timeout')
        self.assertEqual(summary['failed_stage'], 'check')
        self.assertFalse(summary['pass'])
        self.assertIsNone(summary['metrics'])

    def test_constraints_are_separate_from_validity(self):
        config = self.config
        config['limits']['min_wns_ns'] = 2.0
        path = self.root / 'constraint-config.json'
        path.write_text(json.dumps(config))
        out = self.root / 'constraint-run'
        result = self.run_eval(ROOT / 'rtl/baseline/baseline.synth.v', out, '--dev', '--config', str(path))
        self.assertEqual(result.returncode, 1, result.stderr)
        summary = json.loads((out / 'summary.json').read_text())
        self.assertEqual(summary['validity'], 'valid')
        self.assertEqual(summary['constraints']['timing'], 'fail')
        self.assertFalse(summary['pass'])
        self.assertIsNotNone(summary['metrics'])

    def test_missing_timing_report_is_tool_error(self):
        bindir = self.root / 'tools' / 'bin'
        bindir.mkdir(parents=True)
        prefix = Path(self.config['tool_prefix']) / 'bin'
        for name in ('yosys', 'openroad'):
            (bindir / name).symlink_to(prefix / name)
        sta = bindir / 'sta'
        sta.write_text('#!/bin/sh\nexit 0\n')
        sta.chmod(0o755)
        self.config['tool_prefix'] = str(bindir.parent)
        path = self.root / 'missing-report-config.json'
        path.write_text(json.dumps(self.config))
        out = self.root / 'missing-report'
        result = self.run_eval(ROOT / 'rtl/baseline/baseline.synth.v', out, '--dev', '--config', str(path))
        self.assertEqual(result.returncode, 2)
        summary = json.loads((out / 'summary.json').read_text())
        self.assertEqual(summary['failed_stage'], 'timing')
        self.assertEqual(summary['execution_status'], 'error')
        self.assertFalse(summary['pass'])
        self.assertIsNone(summary['metrics'])

    def test_official_uses_committed_harness(self):
        repo = self.root / 'repo'
        repo.mkdir()
        for folder in ('eval', 'tech'):
            shutil.copytree(ROOT / folder, repo / folder, ignore=shutil.ignore_patterns('__pycache__'))
        subprocess.run(['git', 'init', '-q', str(repo)], check=True)
        subprocess.run(['git', '-C', str(repo), 'add', '.'], check=True)
        subprocess.run(['git', '-C', str(repo), '-c', 'user.name=Harness Test',
                        '-c', 'user.email=harness@example.invalid', 'commit', '-qm', 'test fixture'], check=True)
        revision = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
        # An uncommitted broken tool path must not affect official evaluation.
        config = json.loads((repo / 'eval/config.json').read_text())
        config['top'] = 'wrong_working_tree_top'
        (repo / 'eval/config.json').write_text(json.dumps(config))
        (repo / 'eval/check/run.py').write_text('this is deliberately invalid Python!')
        out = self.root / 'official'
        result = self.run_eval(ROOT / 'rtl/baseline/baseline.synth.v', out, root=repo)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        summary = json.loads((out / 'summary.json').read_text())
        self.assertEqual(summary['harness_commit'], revision)
        self.assertEqual(summary['mode'], 'official')
        self.assertTrue(summary['pass'])
        self.assertEqual(summary['constraints']['area'], 'not_set')
        self.assertAlmostEqual(summary['metrics']['area_um2'], 153.0)
        self.assertTrue((out / 'manifest.json').is_file())


if __name__ == '__main__':
    unittest.main()
