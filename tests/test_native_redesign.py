import os
import re
import tempfile
import unittest
from unittest import mock

import support
from AIAssistant import config
from AIAssistant.mcp.registry import ToolError
from AIAssistant.tools import slice_tools
from AIAssistant.ui import strings, view_state

try:
    import qml_harness
    from PyQt5.QtCore import QUrl
    HAVE_QT = True
except ImportError:
    HAVE_QT = False

import ui_fakes

QML_DIR = os.path.join(support.PLUGIN_DIR, "qml")


def read_qml(name):
    with open(os.path.join(QML_DIR, name), encoding="utf-8") as handle:
        return handle.read()


class SliceReadinessTest(unittest.TestCase):
    def setUp(self):
        config.set_value("results_dir", tempfile.mkdtemp())
        self.monitor = slice_tools.SliceMonitor()
        patcher = mock.patch.object(slice_tools, "_monitor", self.monitor)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_slicing_from_the_slicer_ui_enables_export(self):
        self.monitor.on_state(2)
        self.assertFalse(slice_tools.slice_ready())
        self.monitor.on_state(3)
        self.assertTrue(slice_tools.slice_ready())

    def test_invalidated_slice_is_not_ready(self):
        self.monitor.on_state(3)
        self.monitor.on_state(1)
        with mock.patch.object(slice_tools, "_gcode_available", return_value=True):
            self.assertFalse(slice_tools.slice_ready())

    def test_existing_gcode_counts_before_any_state_was_observed(self):
        with mock.patch.object(slice_tools, "run_on_main", side_effect=lambda func, *a, **k: func()):
            with mock.patch.object(slice_tools, "_gcode_available", return_value=True):
                self.assertTrue(slice_tools.slice_ready())
            with mock.patch.object(slice_tools, "_gcode_available", return_value=False):
                self.assertFalse(slice_tools.slice_ready())

    def test_export_gcode_after_manual_slice(self):
        with mock.patch.object(slice_tools, "run_on_main", side_effect=lambda func, *a, **k: False):
            with self.assertRaises(ToolError):
                slice_tools.export_gcode({"model_name": "part"})
        self.monitor.on_state(3)
        with mock.patch.object(slice_tools, "_write_gcode", return_value=123) as writer:
            result = slice_tools.export_gcode({"model_name": "part"})
        self.assertEqual(result["bytes"], 123)
        self.assertTrue(result["path"].endswith(os.path.join("part", "result.gcode")))
        writer.assert_called_once_with(result["path"])


class LiveSliceTest(unittest.TestCase):
    def test_live_slice_formats_metrics(self):
        view = view_state.live_slice("ru", {"state": "done", "ready": True, "print_time_s": 3720,
                                            "material_m": 2.5, "material_g": 7.4})
        self.assertEqual(view["state"], "done")
        self.assertEqual(view["time"], "1 ч 02 мин")
        self.assertEqual(view["length"], "2.5 м")
        self.assertEqual(view["weight"], "7 г")
        self.assertEqual(view_state.live_slice("en", {"state": "processing", "progress": 0.4})["state"], "slicing")
        self.assertEqual(view_state.live_slice("en", {"state": "not_started"})["state"], "idle")
        self.assertIsNone(view_state.live_slice("en", None))

    def test_running_titles_exist_for_every_tool_group(self):
        for group in set(view_state.TOOL_GROUPS.values()):
            for language in ("ru", "en"):
                self.assertIn("run_" + group, strings.table(language))
        self.assertEqual(view_state.tool_running_title("ru", "analyze_mesh"), "Анализирую модель")
        self.assertEqual(view_state.tool_running_title("ru", "set_material"), "Подбираю материал")
        self.assertEqual(view_state.tool_running_title("ru", "set_settings"), "Настраиваю печать")
        self.assertEqual(view_state.tool_running_title("ru", "slice"), "Выполняю слайсинг")
        self.assertEqual(view_state.tool_running_title("ru", "export_gcode"), "Сохраняю результат")

    def test_tool_card_changes_title_when_done(self):
        state = view_state.ChatViewState("ru")
        state.apply({"type": "tool_call", "data": {"call_id": "1", "name": "analyze_mesh", "arguments": {}}})
        self.assertEqual(state.items[0]["title"], "Анализирую модель")
        state.apply({"type": "tool_result", "data": {"call_id": "1", "name": "analyze_mesh", "ok": False, "error": "x"}})
        self.assertEqual(state.items[0]["title"], "Анализ геометрии")
        self.assertEqual(state.items[0]["status"], "error")


class ChangeListTest(unittest.TestCase):
    def test_unchanged_and_reverted_values_are_hidden(self):
        state = view_state.ChatViewState("ru")
        for data in ({"key": "print_mode", "old": "3D", "value": "3D"},
                     {"key": "quality", "old": "draft", "value": "Draft"},
                     {"key": "wall_line_count", "old": "2", "value": "4"},
                     {"key": "infill_sparse_density", "old": "20 %", "value": "40 %"},
                     {"key": "infill_sparse_density", "old": "40 %", "value": "20 %"}):
            state.apply({"type": "setting_changed", "data": data})
        self.assertEqual([c["key"] for c in state.changes_list()], ["wall_line_count"])
        self.assertEqual(state.setup["mode"], "3D")


class QmlInteractionRulesTest(unittest.TestCase):
    def test_buttons_do_not_stack_a_second_hover_area(self):
        for name in os.listdir(QML_DIR):
            if name.endswith(".qml"):
                self.assertNotIn("UM.TooltipArea", read_qml(name), name)

    def test_clickable_components_show_a_hand_cursor(self):
        for name in ("AButton.qml", "IconButton.qml", "ContextChip.qml", "Segmented.qml", "TabBar.qml",
                     "Disclosure.qml", "CheckRow.qml"):
            self.assertIn("Qt.PointingHandCursor", read_qml(name), name)
            self.assertNotIn("acceptedButtons: Qt.NoButton\n        visible", read_qml(name), name)

    def test_icon_only_buttons_have_tooltips(self):
        text = read_qml("IconButton.qml")
        self.assertIn("HoverTip", text)
        for name in os.listdir(QML_DIR):
            if not name.endswith(".qml"):
                continue
            for block in re.findall(r"IconButton\s*\{(.*?)\n\s*\}", read_qml(name), re.S):
                self.assertIn("tooltip", block, name)

    def test_icons_exist(self):
        used = set()
        for name in os.listdir(QML_DIR):
            if name.endswith(".qml"):
                used.update(re.findall(r'(?:iconName|name):\s*"([a-z0-9-]+)"', read_qml(name)))
        missing = [icon for icon in used if not os.path.isfile(os.path.join(QML_DIR, "icons", icon + ".svg"))]
        self.assertEqual(missing, [])


@unittest.skipUnless(HAVE_QT, "PyQt5 is required for the controller tests")
class RedesignControllerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = qml_harness.app()

    def setUp(self):
        objects = [ui_fakes.scene_object("obj1", "gear.stl", 33.1, 10.1, 33.1)]
        self.controller, self.agent, self.bus, self.registry, self.manager = ui_fakes.fresh_environment(objects=objects)
        self.controller.refreshScene()

    def tearDown(self):
        self.controller.stop()

    def test_live_slice_makes_gcode_available(self):
        self.assertFalse(self.controller.sliceInfo["ready"])
        self.controller._slicer_setup["slice"] = view_state.live_slice("ru", {"state": "done", "print_time_s": 600,
                                                                               "material_m": 1, "material_g": 3})
        info = self.controller.sliceInfo
        self.assertTrue(info["ready"])
        self.assertFalse(info["historical"])
        self.assertEqual(info["time"], "0 ч 10 мин")

    def test_history_result_is_marked_as_stale(self):
        ui_fakes.publish(self.bus, ui_fakes.CONVERSATION + ui_fakes.FINISH)
        self.agent.running = False
        self.controller.tick()
        self.controller._slicer_setup["slice"] = view_state.live_slice("ru", {"state": "not_started"})
        info = self.controller.sliceInfo
        self.assertFalse(info["ready"])
        self.assertTrue(info["historical"])
        self.assertEqual(info["time"], "2 ч 14 мин")
        self.assertEqual(self.controller.sliceState, "idle")

    def test_add_files_accepts_dialog_values(self):
        folder = tempfile.mkdtemp()
        paths = []
        for name in ("a.stl", "b.obj", "c.3mf"):
            path = os.path.join(folder, name)
            with open(path, "wb") as handle:
                handle.write(b"solid")
            paths.append(path)

        class JSValue(object):
            def __init__(self, value):
                self.value = value

            def toVariant(self):
                return self.value
        self.assertEqual(self.controller.addFiles(QUrl.fromLocalFile(paths[0]).toString()), 1)
        self.assertEqual(self.controller.addFiles(JSValue([QUrl.fromLocalFile(paths[1])])), 1)
        self.assertEqual(self.controller.addFiles([paths[2]]), 1)
        self.assertEqual(self.controller.attachmentModel.count, 3)

    def test_scene_subtitle_and_requested_mode(self):
        self.assertEqual(self.controller.sceneSubtitle, "gear.stl · 33.1 × 10.1 × 33.1 мм")
        self.assertEqual(self.controller.requestedMode, "")
        self.controller.setMode("cylindrical")
        self.controller.send("Колесо")
        self.assertEqual(self.controller.requestedMode, "5D Spiral")

    def test_notifications_carry_a_kind(self):
        kinds = []
        self.controller.notify.connect(lambda kind, message: kinds.append(kind))
        self.controller._notify("error", "failed")
        self.assertEqual(kinds, ["error"])


if __name__ == "__main__":
    unittest.main()
