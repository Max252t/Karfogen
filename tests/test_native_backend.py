import os
import tempfile
import unittest
from unittest import mock

import support
from AIAssistant import config
from AIAssistant.agent import agent as agent_module, llm_client
from AIAssistant.mcp.registry import get_registry
from AIAssistant.server import projects, uploads
from AIAssistant.server.events import EventBus


class FakeLLM(object):
    def __init__(self):
        self.messages = None

    def chat(self, messages, tools=None):
        self.messages = messages
        return {"content": "ok"}


class AgentNotesTest(unittest.TestCase):
    def setUp(self):
        config.set_value("results_dir", tempfile.mkdtemp())

    def test_notes_and_display_reach_llm_and_event(self):
        bus = EventBus()
        llm = FakeLLM()
        agent = agent_module.Agent(registry=get_registry(), bus=bus, llm=llm)
        ok, _ = agent.submit("Шестерня", [], None, "classic", ["Модель уже в сцене: g.stl (object_id=obj1)"],
                             {"scene": ["g.stl"]})
        self.assertTrue(ok)
        agent._thread.join(5)
        user = llm.messages[1]["content"]
        self.assertTrue(user.startswith("Шестерня\n\n"))
        self.assertIn("object_id=obj1", user)
        self.assertIn("force_mode=classic", user)
        event = [e for e in bus.snapshot() if e["type"] == "user_message"][0]["data"]
        self.assertEqual(event["scene"], ["g.stl"])
        self.assertEqual(event["forced_mode"], "classic")
        self.assertEqual(event["text"], "Шестерня")

    def test_submit_records_attachment_names(self):
        bus = EventBus()
        agent = agent_module.Agent(registry=get_registry(), bus=bus, llm=FakeLLM())
        path = os.path.join(tempfile.mkdtemp(), "part.stl")
        with open(path, "wb") as handle:
            handle.write(b"solid")
        item = uploads.register_file(path)
        agent.submit("x", [item["id"]])
        agent._thread.join(5)
        event = [e for e in bus.snapshot() if e["type"] == "user_message"][0]["data"]
        self.assertEqual(event["files"], [{"name": "part.stl", "kind": "model"}])

    def test_llm_errors_carry_codes(self):
        bus = EventBus()

        class Failing(object):
            def chat(self, messages, tools=None):
                raise llm_client.LLMError("Ключ API отклонён", 401)
        agent = agent_module.Agent(registry=get_registry(), bus=bus, llm=Failing())
        agent.submit("x")
        agent._thread.join(5)
        error = [e for e in bus.snapshot() if e["type"] == "error"][0]["data"]
        self.assertEqual(error["code"], "auth")


class LlmClientTest(unittest.TestCase):
    def test_codes_from_status(self):
        self.assertEqual(llm_client.LLMError("x", 403).code, "auth")
        self.assertEqual(llm_client.LLMError("x", 404).code, "not_found")
        self.assertEqual(llm_client.LLMError("x", 429).code, "rate_limit")
        self.assertEqual(llm_client.LLMError("x", 503).code, "server")
        self.assertEqual(llm_client.LLMError("x").code, "network")
        self.assertEqual(llm_client.LLMError("x", code="timeout").code, "timeout")

    def test_missing_settings_are_not_configured(self):
        config.set_value("base_url", "")
        config.set_value("api_key", "")
        config.set_value("model", "")
        self.assertFalse(llm_client.is_configured())
        with self.assertRaises(llm_client.LLMError) as ctx:
            llm_client.chat([{"role": "user", "content": "x"}])
        self.assertEqual(ctx.exception.code, "not_configured")

    def test_overrides_are_used_without_saving(self):
        config.set_value("base_url", "https://saved.example/v1")
        config.set_value("api_key", "saved-key")
        config.set_value("model", "saved-model")
        seen = {}

        class Response(object):
            def __enter__(self):
                return self

            def __exit__(self, *args):
                seen["closed"] = True

            def read(self):
                return b'{"choices": [{"message": {"content": "ok"}}]}'

        def fake_urlopen(request, timeout=None, context=None):
            seen["url"] = request.full_url
            seen["auth"] = request.get_header("Authorization")
            seen["body"] = request.data
            return Response()
        with mock.patch.object(llm_client.urllib.request, "urlopen", fake_urlopen):
            answer = llm_client.test_connection({"base_url": "https://typed.example/v1/", "model": "typed-model",
                                                 "api_key": "typed-key"})
        self.assertEqual(answer, "ok")
        self.assertTrue(seen["closed"])
        self.assertEqual(seen["url"], "https://typed.example/v1/chat/completions")
        self.assertEqual(seen["auth"], "Bearer typed-key")
        self.assertIn(b"typed-model", seen["body"])
        self.assertEqual(config.get("base_url"), "https://saved.example/v1")


class RegisterFileTest(unittest.TestCase):
    def setUp(self):
        config.set_value("results_dir", tempfile.mkdtemp())
        self.folder = tempfile.mkdtemp()

    def make(self, name, data=b"data"):
        path = os.path.join(self.folder, name)
        with open(path, "wb") as handle:
            handle.write(data)
        return path

    def test_registers_without_copying(self):
        path = self.make("Gear.OBJ")
        item = uploads.register_file(path)
        self.assertEqual(item["kind"], "model")
        self.assertEqual(item["path"], os.path.abspath(path))
        self.assertEqual(uploads.get_item(item["id"])["size"], 4)
        self.assertEqual(os.listdir(config.get_uploads_dir()), [])

    def test_rejects_bad_files(self):
        with self.assertRaises(uploads.UploadError):
            uploads.register_file(self.make("a.exe"))
        with self.assertRaises(uploads.UploadError):
            uploads.register_file(self.make("empty.png", b""))
        with self.assertRaises(uploads.UploadError):
            uploads.register_file(os.path.join(self.folder, "missing.stl"))
        with mock.patch.object(uploads, "MAX_BYTES", 2):
            with self.assertRaises(uploads.UploadError):
                uploads.register_file(self.make("big.stl"))


class ProjectsNativeTest(unittest.TestCase):
    def test_create_without_clearing_scene(self):
        config.set_value("results_dir", tempfile.mkdtemp())
        manager = projects.ProjectManager()

        class Agent(object):
            on_finished = None
            on_progress = None

            def is_running(self):
                return False

            def get_history(self):
                return []

            def set_history(self, history):
                pass
        manager.attach(Agent(), EventBus())
        with mock.patch.object(manager, "prepare_slicer") as prepare:
            manager.create(None, prepare=False)
            self.assertFalse(prepare.called)
            manager.create(None)
            self.assertTrue(prepare.called)

    def test_scene_model_names_project(self):
        history = [{"role": "user", "content": "Сделай прочнее\n\nМодель уже в сцене: gear_v2.stl (object_id=obj1, габариты 1 мм)."}]
        self.assertEqual(projects.name_from_history(history), "gear_v2")


if __name__ == "__main__":
    unittest.main()
