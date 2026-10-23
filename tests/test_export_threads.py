import unittest

import support
from AIAssistant.mcp.registry import ToolError
from AIAssistant.tools import slice_tools


class ExportThreadTest(unittest.TestCase):
    def test_writers_refuse_to_run_on_main_thread(self):
        with self.assertRaises(ToolError):
            slice_tools._write_gcode("result.gcode")
        with self.assertRaises(ToolError):
            slice_tools._write_project("project.3mf")


if __name__ == "__main__":
    unittest.main()
