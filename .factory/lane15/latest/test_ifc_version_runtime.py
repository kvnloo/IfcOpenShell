# This file was generated with the assistance of an AI coding tool.
"""Reject the wrong IfcOpenShell runtime before calling native authoring APIs."""
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from ifc_author import Dimensions, run


class NativeVersionIsolationTests(TestCase):
    def test_wrong_runtime_version_cannot_author_ifc(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.dict('sys.modules', {'ifcopenshell': SimpleNamespace(version='0.8.5')}):
                report = run(root, Dimensions(), length_unit='mm')
            self.assertEqual(report['status'], 'blocked')
            self.assertEqual(report['runtime_checks']['ifc_roundtrip'], 'NOT_RUN')
            self.assertIn('0.9.0', report['blocker'])
            self.assertFalse((root / 'single_zone.ifc').exists())
