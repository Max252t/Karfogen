import json
import tempfile
import time
import unittest
import urllib.request

import support
from AIAssistant import config
from AIAssistant.agent.agent import get_agent
from AIAssistant.mcp.registry import get_registry
from AIAssistant.server import projects
from AIAssistant.server.http_server import AssistantServer


class FakeLLM(object):
    def __init__(self):
        self.calls = 0

    def chat(self, messages, tools=None):
        self.calls += 1
        if self.calls == 1:
            return {"content": "", "tool_calls": [{"id": "1", "function": {"name": "echo2", "arguments": "{}"}}]}
        return {"content": "Готово, деталь настроена."}


class PersistenceFlowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        config.set_value("results_dir", tempfile.mkdtemp())
        config.set_value("port", 0)
        get_registry().register("echo2", "", {"type": "object", "properties": {}},
                                lambda a: {"numbers": [1.5, 2], "odd": set([1]), "obj": object})
        cls.server = AssistantServer()
        cls.base = "http://127.0.0.1:%d" % cls.server.start()
        get_agent()._llm = FakeLLM()

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()

    def post(self, path, payload):
        request = urllib.request.Request(self.base + path, data=json.dumps(payload).encode("utf-8"),
                                         method="POST", headers={"Content-Type": "application/json"})
        return json.loads(urllib.request.urlopen(request).read().decode("utf-8"))

    def events(self):
        return json.loads(urllib.request.urlopen(self.base + "/api/events?since=0").read().decode("utf-8"))["events"]

    def wait_idle(self):
        deadline = time.time() + 10
        while get_agent().is_running() and time.time() < deadline:
            time.sleep(0.05)
        time.sleep(0.2)

    def test_chat_survives_switching_projects(self):
        self.wait_idle()
        self.post("/api/projects", {"action": "create"})
        self.post("/api/message", {"text": "Шестерня под нагрузку"})
        self.wait_idle()
        before = [e["type"] for e in self.events()]
        self.assertIn("assistant_message", before)
        first = projects.get_manager().current_id
        other = self.post("/api/projects", {"action": "create", "name": "Второй"})["current"]["id"]
        self.assertEqual(self.events(), [])
        self.post("/api/projects", {"action": "open", "id": first})
        after = [e["type"] for e in self.events()]
        self.assertEqual(after, before)
        self.post("/api/projects", {"action": "open", "id": first})
        self.assertEqual([e["type"] for e in self.events()], before)
        saved = projects.load_project(first)
        self.assertGreaterEqual(saved["messages"], 1)
        self.assertEqual(saved["name"], "Шестерня под нагрузку")
        self.assertTrue(other)

    def test_chat_is_rebuilt_from_history_when_events_are_missing(self):
        manager = projects.get_manager()
        meta = projects.create_project("Старый")
        history = [{"role": "user", "content": "Привет\n\nПрикреплён файл: a.stl, путь: x"},
                   {"role": "assistant", "content": "Здравствуйте"}]
        projects.save_project(meta["id"], [], history)
        self.wait_idle()
        manager.open(meta["id"])
        events = self.events()
        self.assertEqual([e["type"] for e in events], ["user_message", "assistant_message"])
        self.assertEqual(events[0]["data"]["text"], "Привет")

    def test_autosave_is_throttled_but_saves(self):
        manager = projects.get_manager()
        self.wait_idle()
        manager.ensure_current()
        manager._last_autosave = 0
        get_agent().set_history([{"role": "user", "content": "Автосохранение"}])
        manager.autosave()
        self.assertEqual(projects.load_project(manager.current_id)["messages"], 1)
        get_agent().set_history([])
        manager.autosave()
        self.assertEqual(projects.load_project(manager.current_id)["messages"], 1)


if __name__ == "__main__":
    unittest.main()
