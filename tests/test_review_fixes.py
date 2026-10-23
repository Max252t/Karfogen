import base64
import os
import tempfile
import unittest

import support
from AIAssistant import config
from AIAssistant.agent.agent import compact_history, MAX_HISTORY_CHARS, OLD_TOOL_RESULT_CHARS
from AIAssistant.server import uploads
from AIAssistant.tools import advisor_tools
from AIAssistant.tools.slice_tools import SliceMonitor


class SliceMonitorTest(unittest.TestCase):
    def setUp(self):
        self.monitor = SliceMonitor()
        self.monitor.reset()

    def test_error_survives_following_not_started(self):
        self.monitor.on_state(4)
        self.monitor.on_state(1)
        self.assertTrue(self.monitor.finished.is_set())
        self.assertEqual(self.monitor.result, 4)

    def test_done_is_recorded(self):
        self.monitor.on_state(2)
        self.monitor.on_state(3)
        self.assertEqual(self.monitor.result, 3)

    def test_invalidation_after_done(self):
        self.monitor.on_state(3)
        self.monitor.on_state(1)
        self.assertIsNone(self.monitor.result)

    def test_new_processing_after_done_restarts(self):
        self.monitor.on_state(3)
        self.monitor.on_state(2)
        self.assertFalse(self.monitor.finished.is_set())
        self.assertIsNone(self.monitor.result)

    def test_reset_clears_result(self):
        self.monitor.on_state(4)
        self.monitor.reset()
        self.assertIsNone(self.monitor.result)
        self.assertFalse(self.monitor.finished.is_set())


class UploadsTest(unittest.TestCase):
    def setUp(self):
        config.set_value("results_dir", tempfile.mkdtemp())

    def test_ids_are_unique_and_folders_reusable(self):
        data = base64.b64encode(b"solid x").decode("ascii")
        os.makedirs(os.path.join(config.get_uploads_dir(), "f1"))
        first = uploads.save_upload("part.stl", data)
        second = uploads.save_upload("part.stl", data)
        self.assertNotEqual(first["id"], second["id"])
        self.assertNotEqual(first["path"], second["path"])
        self.assertTrue(os.path.isfile(second["path"]))


class PickQualityTest(unittest.TestCase):
    PROFILES = [
        {"quality_type": "high", "available": True, "layer_height": 0.06},
        {"quality_type": "normal", "available": True, "layer_height": None},
        {"quality_type": "fast", "available": True, "layer_height": 0.15},
        {"quality_type": "draft", "available": True, "layer_height": "=layer_height"},
        {"quality_type": "coarse", "available": False, "layer_height": 0.4},
    ]

    def test_exact_match_without_layer_height(self):
        self.assertEqual(advisor_tools._pick_quality("normal", self.PROFILES), "normal")

    def test_nearest_ignores_non_numeric(self):
        profiles = [p for p in self.PROFILES if p["quality_type"] != "fast"]
        self.assertEqual(advisor_tools._pick_quality("verydraft", profiles), "high")

    def test_unavailable_not_chosen(self):
        self.assertEqual(advisor_tools._pick_quality("coarse", self.PROFILES), "fast")


class CompactHistoryTest(unittest.TestCase):
    def test_old_tool_results_shortened_current_kept(self):
        history = [
            {"role": "user", "content": [{"type": "text", "text": "old"}, {"type": "image_url", "image_url": {"url": "data:x"}}]},
            {"role": "assistant", "content": "", "tool_calls": [{"id": "1", "function": {"name": "a", "arguments": "{}"}}]},
            {"role": "tool", "tool_call_id": "1", "content": "x" * 5000},
            {"role": "assistant", "content": "done"},
            {"role": "user", "content": "new"},
            {"role": "assistant", "content": "", "tool_calls": [{"id": "2", "function": {"name": "a", "arguments": "{}"}}]},
            {"role": "tool", "tool_call_id": "2", "content": "y" * 5000},
        ]
        result = compact_history(history)
        self.assertEqual(len(result), len(history))
        self.assertIsInstance(result[0]["content"], str)
        self.assertLessEqual(len(result[2]["content"]), OLD_TOOL_RESULT_CHARS + 20)
        self.assertEqual(len(result[6]["content"]), 5000)
        self.assertEqual(len(history[2]["content"]), 5000)

    def test_oldest_turns_dropped_when_too_large(self):
        history = []
        for i in range(400):
            history.append({"role": "user", "content": "q%d " % i + "z" * 1000})
            history.append({"role": "assistant", "content": "a"})
        result = compact_history(history)
        self.assertEqual(result[-2]["content"], history[-2]["content"])
        self.assertEqual(result[0]["role"], "user")
        self.assertLess(sum(len(m["content"]) for m in result), MAX_HISTORY_CHARS + 2000)


if __name__ == "__main__":
    unittest.main()
