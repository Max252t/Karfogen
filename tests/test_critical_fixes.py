import threading
import unittest
from unittest import mock

import support
from AIAssistant.agent.agent import Agent
from AIAssistant.mcp.registry import ToolError
from AIAssistant.server.events import EventBus
from AIAssistant.tools import settings_tools


class ProtectedSettingsTest(unittest.TestCase):
    def test_machine_and_gcode_keys_rejected(self):
        for key in ("machine_start_gcode", "machine_end_gcode", "machine_width", "Machine_Name", "layer_start_gcode"):
            with self.assertRaises(ToolError):
                settings_tools.check_key_allowed(key)

    def test_regular_keys_allowed(self):
        for key in ("wall_line_count", "infill_sparse_density", "support_enable"):
            settings_tools.check_key_allowed(key)

    def test_apply_rejects_before_touching_stack(self):
        with self.assertRaises(ToolError):
            settings_tools._apply_setting("machine_start_gcode", "M104 S300", None)


class _Registry(object):
    def list_openai(self):
        return []


class _Llm(object):
    def __init__(self, agent):
        self.agent = agent
        self.calls = 0

    def chat(self, messages, tools):
        self.calls += 1
        self.agent.cancel()
        return {"content": "x", "tool_calls": [{"id": "1", "function": {"name": "noop", "arguments": "{}"}}]}


class CancelTest(unittest.TestCase):
    def test_cancel_on_last_iteration_does_not_report_step_limit(self):
        bus = EventBus()
        agent = Agent(registry=_Registry(), bus=bus)
        agent._llm = _Llm(agent)
        with mock.patch("AIAssistant.agent.agent.config.get", return_value=1):
            agent.submit("hello")
            agent._thread.join(5)
        self.assertFalse(any(e["type"] == "error" for e in bus.snapshot()))
        self.assertTrue(any(e["data"].get("code") == "cancelled" for e in bus.snapshot()))

    def test_cancel_when_idle_returns_false(self):
        agent = Agent(registry=_Registry(), bus=EventBus(), llm=object())
        self.assertFalse(agent.cancel())

    def test_cancel_stops_loop_and_frees_agent(self):
        bus = EventBus()
        agent = Agent(registry=_Registry(), bus=bus, llm=None)
        agent._llm = _Llm(agent)
        ok, _ = agent.submit("hello")
        self.assertTrue(ok)
        agent._thread.join(5)
        self.assertFalse(agent.is_running())
        self.assertEqual(agent._llm.calls, 1)
        tool_messages = [m for m in agent.get_history() if m.get("role") == "tool"]
        self.assertEqual(len(tool_messages), 1)
        self.assertIn("Отменено", tool_messages[0]["content"])
        texts = [e["data"].get("text", "") for e in bus.snapshot() if e["type"] == "assistant_message"]
        self.assertTrue(any("Остановлено" in t for t in texts))

    def test_new_submit_clears_cancel_flag(self):
        agent = Agent(registry=_Registry(), bus=EventBus(), llm=None)
        agent._cancel.set()
        agent._llm = type("L", (), {"chat": lambda self, m, t: {"content": "ok"}})()
        agent.submit("hi")
        agent._thread.join(5)
        self.assertEqual(agent.get_history()[-1]["content"], "ok")


if __name__ == "__main__":
    unittest.main()
