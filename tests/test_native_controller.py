import os
import tempfile
import time
import unittest
from unittest import mock

import support
from AIAssistant import config
from AIAssistant.agent import llm_client
from AIAssistant.server import projects, uploads

try:
    import qml_harness
    from AIAssistant.ui import controller as controller_module
    HAVE_QT = True
except ImportError:
    HAVE_QT = False

import ui_fakes

PNG = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
       b"\x00\x00\x00\rIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfe\xa7\x9a\xa0\xa0\x00\x00\x00\x00IEND\xaeB`\x82")


def write_file(name, data=b"solid x\nendsolid x\n"):
    folder = tempfile.mkdtemp()
    path = os.path.join(folder, name)
    with open(path, "wb") as handle:
        handle.write(data)
    return path


@unittest.skipUnless(HAVE_QT, "PyQt5 is required for the controller tests")
class ControllerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = qml_harness.app()

    def setUp(self):
        objects = [ui_fakes.scene_object("obj1", "bracket.stl", 62, 40, 35),
                   ui_fakes.scene_object("obj2", "cover.stl", 120, 80, 3)]
        self.controller, self.agent, self.bus, self.registry, self.manager = ui_fakes.fresh_environment(objects=objects)
        self.controller.refreshScene()

    def tearDown(self):
        self.controller.stop()

    def pump(self, until=None, timeout=5.0):
        deadline = time.time() + timeout
        while time.time() < deadline:
            self.app.processEvents()
            if until is None or until():
                return True
            time.sleep(0.01)
        return False

    def test_auto_mode_sends_no_forced_mode(self):
        self.assertEqual(self.controller.mode, "auto")
        self.assertTrue(self.controller.send("Кронштейн"))
        self.assertIsNone(self.agent.submitted[-1]["mode"])

    def test_forced_modes(self):
        for mode in ("classic", "cylindrical", "cylindrical_full"):
            self.agent.running = False
            self.controller.tick()
            self.controller.setMode(mode)
            self.assertTrue(self.controller.send("деталь"))
            self.assertEqual(self.agent.submitted[-1]["mode"], mode)
        self.controller.setMode("bogus")
        self.assertEqual(self.controller.mode, "auto")

    def test_send_is_blocked_while_running(self):
        self.assertTrue(self.controller.send("первое"))
        self.assertTrue(self.controller.running)
        self.assertFalse(self.controller.send("второе"))
        self.assertEqual(len(self.agent.submitted), 1)

    def test_empty_message_is_ignored(self):
        self.assertFalse(self.controller.send("   "))
        self.assertEqual(self.agent.submitted, [])

    def test_send_requires_configuration(self):
        config.set_value("api_key", "")
        opened = []
        self.controller.openSettingsRequested.connect(lambda: opened.append(True))
        self.assertFalse(self.controller.configured)
        self.assertEqual(self.controller.connectionState, "not_configured")
        self.assertFalse(self.controller.send("x"))
        self.assertEqual(opened, [True])

    def test_scene_models_are_offered_and_passed_as_notes(self):
        self.assertEqual(self.controller.sceneModel.count, 2)
        self.controller.setUseScene(True)
        self.controller.toggleSceneObject("obj2")
        self.assertTrue(self.controller.send(""))
        sent = self.agent.submitted[-1]
        self.assertEqual(len(sent["notes"]), 1)
        self.assertIn("object_id=obj1", sent["notes"][0])
        self.assertEqual(sent["display"]["scene"], ["bracket.stl"])
        self.assertFalse(self.controller.useScene)

    def test_whole_scene(self):
        self.controller.selectWholeScene()
        self.assertTrue(self.controller.useScene)
        self.controller.send("всё")
        self.assertEqual(len(self.agent.submitted[-1]["notes"]), 2)

    def test_single_object_is_preselected(self):
        self.registry.objects = [ui_fakes.scene_object("obj9", "gear.stl", 10, 10, 5)]
        self.controller.refreshScene()
        self.controller.setUseScene(True)
        self.assertIn("gear.stl", self.controller.sceneSummary)

    def test_attachments_by_local_path(self):
        model = write_file("part.STL")
        image = write_file("photo.png", PNG)
        added = self.controller.addFiles(["file:///" + model.replace(os.sep, "/"), image])
        self.assertEqual(added, 2)
        items = self.controller.attachmentModel.items()
        self.assertEqual([i["kind"] for i in items], ["model", "image"])
        self.assertTrue(items[1]["url"].startswith("file:"))
        self.assertEqual(os.path.normcase(uploads.get_item(items[0]["id"])["path"]), os.path.normcase(model))
        self.assertTrue(self.controller.send("с файлами"))
        self.assertEqual(self.agent.submitted[-1]["ids"], [i["id"] for i in items])
        self.assertEqual(self.controller.attachmentModel.count, 0)

    def test_attachment_validation(self):
        toasts = []
        self.controller.notify.connect(lambda kind, message: toasts.append(kind))
        self.assertFalse(self.controller.addFile(write_file("virus.exe")))
        self.assertFalse(self.controller.addFile(os.path.join(tempfile.mkdtemp(), "missing.stl")))
        self.assertFalse(self.controller.addFile(write_file("empty.obj", b"")))
        path = write_file("big.3mf")
        with mock.patch.object(uploads, "MAX_BYTES", 3):
            self.assertFalse(self.controller.addFile(path))
        good = write_file("ok.obj")
        self.assertTrue(self.controller.addFile(good))
        self.assertFalse(self.controller.addFile(good))
        self.assertEqual(toasts, ["warning"] * 4 + ["success", "warning"])
        self.assertEqual(self.controller.attachmentModel.count, 1)

    def test_remove_attachment(self):
        self.controller.addFile(write_file("a.stl"))
        item = self.controller.attachmentModel.items()[0]
        self.controller.removeAttachment(item["id"])
        self.assertEqual(self.controller.attachmentModel.count, 0)

    def test_events_flow_into_models(self):
        self.controller.send("Кронштейн")
        ui_fakes.publish(self.bus, ui_fakes.CONVERSATION)
        self.controller.tick()
        self.assertTrue(self.controller.running)
        self.assertEqual(self.controller.sliceState, "slicing")
        self.assertIn("слайсинг", self.controller.statusText)
        self.assertIn("85 %", self.controller.statusText)
        kinds = [i["kind"] for i in self.controller.messageModel.items()]
        self.assertEqual(kinds, ["user", "activity"])
        self.assertAlmostEqual(self.controller.workProgress, 0.78 + 0.17 * 0.45)
        self.assertEqual(self.controller.changeModel.count, 3)
        ui_fakes.publish(self.bus, ui_fakes.FINISH)
        self.agent.running = False
        self.controller.tick()
        self.assertFalse(self.controller.running)
        self.assertEqual(self.controller.taskState, "done")
        self.assertEqual(self.controller.sliceInfo["time"], "2 ч 14 мин")
        self.assertTrue(self.controller.exports["gcode"].endswith("result.gcode"))
        self.assertEqual(self.controller.connectionState, "ok")

    def test_stop_cancels_agent(self):
        self.controller.send("x")
        self.assertTrue(self.controller.stopAgent())
        self.assertEqual(self.agent.cancelled, 1)

    def test_retry_continue_and_without_image(self):
        image = write_file("photo.png", PNG)
        self.controller.addFile(image)
        self.controller.setMode("cylindrical")
        self.controller.send("с фото")
        first = self.agent.submitted[-1]
        self.agent.running = False
        self.controller.tick()
        self.assertTrue(self.controller.retry())
        self.assertEqual(self.agent.submitted[-1]["ids"], first["ids"])
        self.agent.running = False
        self.controller.tick()
        self.assertTrue(self.controller.continueWithoutImage())
        self.assertEqual(self.agent.submitted[-1]["ids"], [])
        self.assertEqual(self.agent.submitted[-1]["text"], "с фото")
        self.agent.running = False
        self.controller.tick()
        self.assertTrue(self.controller.continueTask())
        self.assertEqual(self.agent.submitted[-1]["mode"], "cylindrical")
        self.assertEqual(self.agent.submitted[-1]["text"], self.controller.t("continue_prompt"))

    def test_error_actions_route(self):
        settings, files = [], []
        self.controller.openSettingsRequested.connect(lambda: settings.append(1))
        self.controller.pickFileRequested.connect(lambda: files.append(1))
        self.controller.runAction("settings")
        self.controller.runAction("pick_file")
        self.assertEqual((settings, files), ([1], [1]))

    def test_projects_lifecycle(self):
        self.controller.send("Первая деталь")
        self.assertEqual(self.controller.projectName, "Новый проект")
        ui_fakes.publish(self.bus, [("user_message", {"text": "Первая деталь"}), ("done", {})])
        self.manager.save_current()
        self.agent.running = False
        self.controller.tick()
        first = self.controller.projectId
        self.assertTrue(first)
        self.assertEqual(self.controller.projectName, "Первая деталь")
        self.assertTrue(self.controller.createProject(False))
        self.assertNotIn("reset_settings", self.registry.calls)
        second = self.controller.projectId
        self.assertNotEqual(first, second)
        self.assertEqual(self.controller.messageModel.count, 0)
        self.assertTrue(self.controller.renameProject(second, "Корпус"))
        self.assertEqual(self.controller.projectName, "Корпус")
        self.assertTrue(self.controller.openProject(first))
        self.assertEqual(self.controller.projectId, first)
        self.assertEqual(self.controller.projectModel.count, 2)
        self.assertTrue(self.controller.deleteProject(second))
        self.assertEqual(self.controller.projectModel.count, 1)

    def test_new_project_can_clear_scene(self):
        with mock.patch.object(projects.ProjectManager, "prepare_slicer") as prepare:
            self.controller.createProject(True)
        self.assertTrue(prepare.called)

    def test_switching_project_is_blocked_while_running(self):
        meta = projects.create_project("Другой")
        self.controller.send("работаю")
        current = self.controller.projectId
        toasts = []
        self.controller.toast.connect(toasts.append)
        self.assertFalse(self.controller.openProject(meta["id"]))
        self.assertFalse(self.controller.createProject(False))
        self.assertEqual(self.controller.projectId, current)
        self.assertTrue(self.controller.openProject(current))
        self.assertIn(self.controller.t("proj_busy"), toasts)

    def test_reopen_restores_state(self):
        self.controller.send("Кронштейн")
        ui_fakes.publish(self.bus, ui_fakes.CONVERSATION)
        self.controller.tick()
        before = self.controller.messageModel.items()
        reopened = controller_module.NativeChatController(agent=self.agent, bus=self.bus, registry=self.registry,
                                                          manager=self.manager, start_timer=False)
        try:
            self.assertEqual(reopened.messageModel.items(), before)
            self.assertTrue(reopened.running)
            self.assertEqual(reopened.sliceState, "slicing")
        finally:
            reopened.stop()

    def test_settings_save_keeps_key_when_empty(self):
        self.controller.saveSettings({"base_url": " https://x.example/v1 ", "model": "m2", "api_key": "",
                                      "explain": False, "language": "en"})
        self.assertEqual(config.get("api_key"), "test-key-value")
        self.assertEqual(config.get("base_url"), "https://x.example/v1")
        self.assertFalse(config.get("explain"))
        self.assertEqual(self.controller.language, "en")
        self.assertEqual(self.controller.strings["send"], "Send")
        settings = self.controller.settings
        self.assertNotIn("test-key-value", str(settings))
        self.controller.saveSettings({"api_key": "new-secret-key-1234"})
        self.assertEqual(config.get("api_key"), "new-secret-key-1234")

    def test_connection_test_uses_entered_values(self):
        results = []
        self.controller.testFinished.connect(lambda ok, message: results.append((ok, message)))
        with mock.patch.object(llm_client, "test_connection", return_value="ok") as tester:
            self.controller.testConnection({"base_url": "https://other/v1", "model": "m", "api_key": "k"})
            self.assertTrue(self.pump(lambda: results))
        tester.assert_called_with({"base_url": "https://other/v1", "model": "m", "api_key": "k"})
        self.assertTrue(results[0][0])
        self.assertEqual(config.get("base_url"), "https://llm.example/v1")
        self.assertEqual(self.controller.connectionState, "unchecked")

    def test_connection_test_failure_is_explained(self):
        results = []
        self.controller.testFinished.connect(lambda ok, message: results.append((ok, message)))
        error = llm_client.LLMError("Ключ API отклонён (HTTP 401)", 401)
        with mock.patch.object(llm_client, "test_connection", side_effect=error):
            self.controller.testConnection({})
            self.assertTrue(self.pump(lambda: results))
        self.assertFalse(results[0][0])
        self.assertIn(self.controller.t("err_title_auth"), results[0][1])
        self.assertEqual(self.controller.connectionState, "error")

    def test_export_runs_in_background(self):
        import threading
        threads = []
        original = self.registry.call

        def call(name, args):
            threads.append(threading.current_thread() is threading.main_thread())
            return original(name, args)
        self.registry.call = call
        self.registry.has = lambda name: True
        self.assertTrue(self.controller.exportFile("gcode"))
        self.assertTrue(self.pump(lambda: self.controller.exports["gcode"] != "" and self.controller.exports["busy"] == ""))
        self.assertEqual(threads, [False])
        self.assertFalse(self.controller.exportFile("pdf"))

    def test_reset_changes(self):
        self.bus.publish("setting_changed", {"key": "wall_line_count", "old": 2, "value": 4})
        self.controller.tick()
        self.assertEqual(self.controller.changeModel.count, 1)
        self.assertTrue(self.controller.resetChanges())
        self.assertTrue(self.pump(lambda: self.controller.changeModel.count == 0))

    def test_window_geometry_is_not_owned_by_the_controller(self):
        self.assertFalse(hasattr(self.controller, "windowGeometry"))
        self.assertFalse(hasattr(self.controller, "saveGeometry"))

    def test_screenshot_without_window_reports_failure(self):
        toasts = []
        self.controller.toast.connect(toasts.append)
        self.assertEqual(self.controller.saveScreenshot(), "")
        self.assertEqual(toasts, [self.controller.t("toast_screenshot_fail")])

    def test_next_screenshot_path(self):
        folder = tempfile.mkdtemp()
        self.assertTrue(controller_module.next_screenshot_path(folder).endswith("chat_1.png"))
        open(os.path.join(folder, "chat_4.png"), "wb").close()
        self.assertTrue(controller_module.next_screenshot_path(folder).endswith("chat_5.png"))

    def test_project_switch_discards_previous_retry_and_attachments(self):
        self.controller.send("first project request")
        self.agent.running = False
        self.controller.tick()
        self.controller.addFile(write_file("pending.stl"))
        other = projects.create_project("Other")
        self.assertTrue(self.controller.openProject(other["id"]))
        self.assertFalse(self.controller.canRetry)
        self.assertFalse(self.controller.retry())
        self.assertEqual(self.controller.attachmentModel.count, 0)
        self.assertEqual(self.controller.mode, "auto")

    def test_manual_tool_blocks_concurrent_operations(self):
        import threading
        entered, release = threading.Event(), threading.Event()
        original = self.registry.call

        def call(name, args):
            if name == "export_gcode":
                entered.set()
                release.wait(5)
            return original(name, args)

        self.registry.call = call
        other = projects.create_project("Other")
        try:
            self.assertTrue(self.controller.exportFile("gcode"))
            self.assertTrue(entered.wait(2))
            self.assertTrue(self.controller.busy)
            self.assertFalse(self.controller.send("interleaved"))
            self.assertFalse(self.controller.createProject(False))
            self.assertFalse(self.controller.openProject(other["id"]))
            self.assertFalse(self.controller.deleteProject(other["id"]))
            self.assertFalse(self.controller.resetChanges())
        finally:
            release.set()
            self.assertTrue(self.pump(lambda: not self.controller.busy))

    def test_manual_export_refuses_active_agent(self):
        self.agent.running = True
        self.assertFalse(self.controller.exportFile("gcode"))
        self.assertNotIn("export_gcode", self.registry.calls)

    def test_results_folder_switch_does_not_reuse_old_chat(self):
        self.controller.send("Old folder")
        self.agent.running = False
        self.controller.tick()
        old_id = self.controller.projectId
        old_folder = config.get_results_dir()
        self.assertTrue(self.controller.saveSettings({"results_dir": tempfile.mkdtemp()}))
        self.assertIsNone(self.manager.current_id)
        self.assertEqual(self.agent.history, [])
        self.assertFalse(self.controller.canRetry)
        self.assertTrue(os.path.isfile(os.path.join(old_folder, "_projects", old_id, "project.json")))

    def test_settings_cannot_change_during_agent_turn(self):
        self.agent.running = True
        before = config.get("model")
        self.assertFalse(self.controller.saveSettings({"model": "changed"}))
        self.assertEqual(config.get("model"), before)


class NoHttpTest(unittest.TestCase):
    FORBIDDEN = ("XMLHttpRequest", "fetch(", "/api/", "http_server", "urllib", "localhost", "127.0.0.1", "webbrowser")

    def files(self):
        for folder in (os.path.join(support.PLUGIN_DIR, "qml"), os.path.join(support.PLUGIN_DIR, "ui")):
            for name in os.listdir(folder):
                if name.endswith((".qml", ".py", "qmldir")):
                    yield os.path.join(folder, name)

    def test_native_ui_has_no_http(self):
        for path in self.files():
            with open(path, encoding="utf-8") as handle:
                text = handle.read()
            for token in self.FORBIDDEN:
                self.assertNotIn(token, text, "%s uses %s" % (os.path.basename(path), token))

    def test_plugin_does_not_open_browser(self):
        with open(os.path.join(support.PLUGIN_DIR, "AIAssistant.py"), encoding="utf-8") as handle:
            text = handle.read()
        self.assertNotIn("webbrowser", text)
        self.assertIn("AssistantWindow.qml", text)


if __name__ == "__main__":
    unittest.main()
