import json
import tempfile
import unittest
import urllib.error
import urllib.request

import support
from AIAssistant import config
from AIAssistant.mcp.registry import get_registry
from AIAssistant.server import projects
from AIAssistant.server.events import EventBus
from AIAssistant.server.http_server import AssistantServer


class FakeAgent(object):
    def __init__(self):
        self.history = []
        self.running = False
        self.on_finished = None

    def is_running(self):
        return self.running

    def get_history(self):
        return list(self.history)

    def set_history(self, history):
        self.history = list(history)


def fresh_manager():
    config.set_value("results_dir", tempfile.mkdtemp())
    manager = projects.ProjectManager()
    manager.attach(FakeAgent(), EventBus())
    return manager


class StoreTest(unittest.TestCase):
    def setUp(self):
        config.set_value("results_dir", tempfile.mkdtemp())

    def test_create_list_rename_delete(self):
        first = projects.create_project()
        second = projects.create_project("Корпус")
        names = [p["name"] for p in projects.list_projects()]
        self.assertEqual(sorted(names), sorted(["Новый проект", "Корпус"]))
        projects.rename_project(first["id"], "  Шестерня   привода ")
        self.assertIn("Шестерня привода", [p["name"] for p in projects.list_projects()])
        projects.delete_project(second["id"])
        self.assertEqual(len(projects.list_projects()), 1)

    def test_empty_name_rejected(self):
        meta = projects.create_project()
        with self.assertRaises(projects.ProjectError):
            projects.rename_project(meta["id"], "   ")

    def test_bad_id_rejected(self):
        for bad in ("../x", "", "a b"):
            with self.assertRaises(projects.ProjectError):
                projects.load_project(bad)

    def test_unknown_project_is_404(self):
        with self.assertRaises(projects.ProjectError) as ctx:
            projects.load_project("abc123")
        self.assertEqual(ctx.exception.status, 404)

    def test_save_strips_images_and_trims_results(self):
        meta = projects.create_project()
        history = [{"role": "user", "content": [{"type": "text", "text": "hi"},
                                                {"type": "image_url", "image_url": {"url": "data:xxx"}}]}]
        events = [{"id": 1, "ts": 0, "type": "tool_result", "data": {"result": "z" * 50000}}]
        projects.save_project(meta["id"], events, history)
        loaded = projects.load_project(meta["id"])
        self.assertNotIn("data:xxx", json.dumps(loaded, ensure_ascii=False))
        self.assertLess(len(loaded["events"][0]["data"]["result"]), 21000)
        self.assertEqual(loaded["messages"], 1)

    def test_auto_name_only_until_renamed(self):
        meta = projects.create_project()
        projects.save_project(meta["id"], [], [], "Первое имя")
        self.assertEqual(projects.load_project(meta["id"])["name"], "Первое имя")
        projects.rename_project(meta["id"], "Своё")
        projects.save_project(meta["id"], [], [], "Другое")
        self.assertEqual(projects.load_project(meta["id"])["name"], "Своё")

    def test_name_from_history_uses_model_file(self):
        history = [{"role": "user", "content": "Сделай деталь\n\nПрикреплён файл: Шестерня.stl, путь: C:/x/Шестерня.stl"}]
        self.assertEqual(projects.name_from_history(history), "Шестерня")
        self.assertEqual(projects.name_from_history([{"role": "user", "content": "Кронштейн под нагрузку"}]),
                         "Кронштейн под нагрузку")


class ManagerTest(unittest.TestCase):
    def test_switching_restores_history_and_events(self):
        manager = fresh_manager()
        manager.ensure_current()
        first = manager.current_id
        manager.agent.history = [{"role": "user", "content": "Первый"}]
        manager.bus.publish("user_message", {"text": "Первый"})
        manager.create()
        self.assertEqual(manager.agent.history, [])
        self.assertEqual(manager.bus.snapshot(), [])
        manager.bus.publish("user_message", {"text": "Второй"})
        manager.agent.history = [{"role": "user", "content": "Второй"}]
        manager.open(first)
        self.assertEqual(manager.agent.history[0]["content"], "Первый")
        self.assertEqual(manager.bus.snapshot()[0]["data"]["text"], "Первый")
        second = [p for p in projects.list_projects() if p["id"] != first][0]
        manager.open(second["id"])
        self.assertEqual(manager.agent.history[0]["content"], "Второй")

    def test_new_project_prepares_slicer(self):
        from AIAssistant.mcp.registry import get_registry
        calls = []
        registry = get_registry()
        registry.register("clear_scene", "", {"type": "object", "properties": {}}, lambda a: calls.append("clear_scene") or {})
        registry.register("reset_settings", "", {"type": "object", "properties": {}}, lambda a: calls.append("reset_settings") or {})
        manager = fresh_manager()
        manager.ensure_current()
        self.assertEqual(calls, ["clear_scene", "reset_settings"])
        manager.create()
        self.assertEqual(calls, ["clear_scene", "reset_settings"] * 2)
        manager.open(manager.current_id)
        self.assertEqual(len(calls), 4)

    def test_create_profile_is_hidden_from_llm(self):
        from AIAssistant.agent import agent as agent_module
        self.assertIn("create_profile", agent_module.LLM_EXCLUDED_TOOLS)

    def test_busy_agent_blocks_switching(self):
        manager = fresh_manager()
        manager.ensure_current()
        manager.agent.running = True
        with self.assertRaises(projects.ProjectError) as ctx:
            manager.create()
        self.assertEqual(ctx.exception.status, 409)

    def test_current_project_opens_while_agent_runs(self):
        manager = fresh_manager()
        manager.ensure_current()
        current = manager.current_id
        manager.agent.running = True
        self.assertEqual(manager.open(current)["id"], current)
        other = projects.create_project("Другой")
        with self.assertRaises(projects.ProjectError):
            manager.open(other["id"])

    def test_other_project_can_be_deleted_while_agent_runs(self):
        manager = fresh_manager()
        manager.ensure_current()
        other = projects.create_project("Лишний")
        manager.agent.running = True
        manager.delete(other["id"])
        self.assertEqual([p["id"] for p in projects.list_projects()], [manager.current_id])
        with self.assertRaises(projects.ProjectError):
            manager.delete(manager.current_id)

    def test_delete_current_clears_state(self):
        manager = fresh_manager()
        manager.ensure_current()
        manager.bus.publish("x", {})
        manager.delete(manager.current_id)
        self.assertIsNone(manager.current())
        self.assertEqual(manager.bus.snapshot(), [])

    def test_finish_hook_saves(self):
        manager = fresh_manager()
        manager.ensure_current()
        manager.agent.history = [{"role": "user", "content": "Фигурка"}]
        manager.agent.on_finished()
        meta = manager.current()
        self.assertEqual(meta["name"], "Фигурка")
        self.assertEqual(meta["messages"], 1)


class ProjectsApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        config.set_value("results_dir", tempfile.mkdtemp())
        config.set_value("port", 0)
        cls.server = AssistantServer()
        cls.base = "http://127.0.0.1:%d" % cls.server.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()

    def call(self, payload=None):
        if payload is None:
            return json.loads(urllib.request.urlopen(self.base + "/api/projects").read().decode("utf-8"))
        request = urllib.request.Request(self.base + "/api/projects", data=json.dumps(payload).encode("utf-8"),
                                         method="POST", headers={"Content-Type": "application/json"})
        return json.loads(urllib.request.urlopen(request).read().decode("utf-8"))

    def test_lifecycle(self):
        state = self.call({"action": "create", "name": "Тест"})
        self.assertEqual(state["current"]["name"], "Тест")
        project_id = state["current"]["id"]
        state = self.call({"action": "rename", "id": project_id, "name": "Переименован"})
        self.assertIn("Переименован", [p["name"] for p in state["projects"]])
        state = self.call({"action": "delete", "id": project_id})
        self.assertNotIn(project_id, [p["id"] for p in state["projects"]])

    def test_unknown_action_and_project(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.call({"action": "explode"})
        self.assertEqual(ctx.exception.code, 400)
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.call({"action": "open", "id": "nope123"})
        self.assertEqual(ctx.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
