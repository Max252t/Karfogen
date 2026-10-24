import unittest

import support
from AIAssistant.ui.view_state import ChatViewState


class SliceInvalidationTest(unittest.TestCase):
    def test_scene_invalidation_clears_previous_slice_metrics(self):
        state = ChatViewState()
        state.apply({"type": "slice_result", "data": {"time": "2 h", "weight": "40 g"}})
        state.apply({"type": "status", "data": {"text": "slice_state", "state": "not_started"}})
        self.assertEqual(state.slice["state"], "idle")
        self.assertEqual(state.slice["time"], "")
        self.assertEqual(state.slice["progress"], 0)

    def test_backend_failure_is_visible_without_agent_tool_result(self):
        state = ChatViewState()
        state.apply({"type": "status", "data": {"text": "slice_state", "state": "error"}})
        self.assertEqual(state.slice["state"], "error")
