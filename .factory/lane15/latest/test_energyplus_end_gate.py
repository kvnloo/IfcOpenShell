# This file was generated with the assistance of an AI coding tool.
"""The EnergyPlus 26.2 .end receipt is the native completion authority."""
from pathlib import Path
from tempfile import TemporaryDirectory
import sys
import unittest

from energyplus_design_day import run_engine


def stub(root: Path, *, end_line: str | None, err_line: str = 'Program Version,EnergyPlus, 26.2.0,IDD_Version 26.2.0\n') -> Path:
    executable = root / 'energyplus-stub'
    executable.write_text(
        f'#!{sys.executable}\n'
        'from pathlib import Path\n'
        'import sys\n'
        'if "--version" in sys.argv:\n'
        '    print("EnergyPlus, Version 26.2.0")\n'
        '    raise SystemExit(0)\n'
        'out = Path(sys.argv[sys.argv.index("--output-directory") + 1])\n'
        f'(out / "eplusout.err").write_text({err_line!r})\n'
        + (f'(out / "eplusout.end").write_text({end_line!r})\n' if end_line is not None else '')
    )
    executable.chmod(0o755)
    return executable


class EndReceiptTests(unittest.TestCase):
    def test_zero_exit_with_error_log_but_no_end_is_not_pass(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            outcome = run_engine(root / 'model.idf', root / 'output', str(stub(root, end_line=None)))
            self.assertEqual(outcome['status'], 'FAIL', outcome)
            self.assertFalse(outcome.get('engine_end_file_exists', False))

    def test_terminated_end_is_not_pass(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            outcome = run_engine(root / 'model.idf', root / 'output',
                                 str(stub(root, end_line='EnergyPlus Terminated--Fatal Error Detected\n')))
            self.assertEqual(outcome['status'], 'FAIL', outcome)

    def test_end_declares_nonzero_severe_errors_is_not_pass(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            outcome = run_engine(root / 'model.idf', root / 'output',
                                 str(stub(root, end_line='EnergyPlus Completed Successfully-- 0 Warning; 1 Severe Errors\n')))
            self.assertEqual(outcome['status'], 'FAIL', outcome)

    def test_end_success_and_clean_error_log_allow_pass(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            outcome = run_engine(root / 'model.idf', root / 'output',
                                 str(stub(root, end_line='EnergyPlus Completed Successfully-- 2 Warning; 0 Severe Errors; Elapsed Time=00hr 00min 1.0sec\n')))
            self.assertEqual(outcome['status'], 'PASS', outcome)
            self.assertTrue(outcome['engine_end_file_exists'])
            self.assertEqual(len(outcome['engine_end_file_sha256']), 64)

    def test_error_log_severe_overrides_successful_end(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            outcome = run_engine(root / 'model.idf', root / 'output', str(stub(
                root, end_line='EnergyPlus Completed Successfully-- 0 Warning; 0 Severe Errors\n',
                err_line='Program Version,EnergyPlus, 26.2.0\n** Severe ** input broken\n')))
            self.assertEqual(outcome['status'], 'FAIL', outcome)


if __name__ == '__main__':
    unittest.main()
