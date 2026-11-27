# This file was generated with the assistance of an AI coding tool.
"""Reject stale EnergyPlus error logs; stub engine is not native validation."""
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from energyplus_design_day import run_engine


def fake_energyplus(path: Path, *, behavior: str) -> Path:
    """Create a controlled process with EnergyPlus-shaped arguments."""
    path.write_text(f"""#!{sys.executable}
import pathlib
import sys
if '--version' in sys.argv:
    print('EnergyPlus, Version 26.2.0')
    raise SystemExit(0)
out = pathlib.Path(sys.argv[sys.argv.index('--output-directory') + 1])
if {behavior!r} == 'silent':
    raise SystemExit(0)
if {behavior!r} == 'severe':
    (out / 'eplusout.err').write_text('** Severe ** Fatal input problem\\n')
else:
    (out / 'eplusout.err').write_text('EnergyPlus Completed Successfully--stub-only\\n')
    (out / 'eplusout.end').write_text('EnergyPlus Completed Successfully-- 0 Warning; 0 Severe Errors\\n')
""", encoding="utf-8")
    path.chmod(0o755)
    return path


class FreshEngineLogTests(unittest.TestCase):
    def test_reused_clean_log_cannot_turn_silent_process_green(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            out = root / 'engine'
            out.mkdir()
            old_log = out / 'eplusout.err'
            old_log.write_text('EnergyPlus Completed Successfully--stale\n')
            engine = fake_energyplus(root / 'fake-energyplus', behavior='silent')
            result = run_engine(root / 'source.idf', out, str(engine))
            self.assertEqual(result['status'], 'FAIL', result)
            self.assertFalse(result['engine_error_log_exists'])
            self.assertEqual(result['engine_exit_code'], 0)
            self.assertEqual(old_log.read_text(), 'EnergyPlus Completed Successfully--stale\n')
            self.assertNotEqual(Path(result['engine_output_directory']), out)

    def test_new_log_retained_with_hash_and_path(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            engine = fake_energyplus(root / 'fake-energyplus', behavior='success')
            result = run_engine(root / 'source.idf', root / 'engine', str(engine))
            self.assertEqual(result['status'], 'PASS', result)
            log = Path(result['engine_output_directory']) / 'eplusout.err'
            self.assertTrue(log.exists())
            self.assertEqual(len(result['engine_error_log_sha256']), 64)
            self.assertIn('stub-only', log.read_text())

    def test_new_severe_log_rejected(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            engine = fake_energyplus(root / 'fake-energyplus', behavior='severe')
            result = run_engine(root / 'source.idf', root / 'engine', str(engine))
            self.assertEqual(result['status'], 'FAIL', result)
            self.assertEqual(result['severe_or_fatal_lines'], 1)


if __name__ == '__main__':
    unittest.main()
