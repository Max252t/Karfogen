import os
import tempfile
import unittest
from unittest import mock

import support
from AIAssistant.tools import slice_tools


class AtomicExportTest(unittest.TestCase):
    def test_replace_failure_preserves_previous_export(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "result.gcode")
            slice_tools._atomic_write(path, b"previous")
            with mock.patch.object(slice_tools.os, "replace", side_effect=OSError("disk error")):
                with self.assertRaises(OSError):
                    slice_tools._atomic_write(path, b"replacement")
            with open(path, "rb") as handle:
                self.assertEqual(handle.read(), b"previous")
            self.assertEqual(os.listdir(folder), ["result.gcode"])

    def test_success_replaces_export(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "project.3mf")
            slice_tools._atomic_write(path, b"old")
            slice_tools._atomic_write(path, b"new")
            with open(path, "rb") as handle:
                self.assertEqual(handle.read(), b"new")
