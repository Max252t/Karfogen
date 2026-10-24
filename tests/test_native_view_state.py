import os
import re
import unittest

import support
from AIAssistant.server.events import EventBus
from AIAssistant.ui import strings, view_state

import ui_fakes

QML_DIR = os.path.join(support.PLUGIN_DIR, "qml")


def run(events, language="ru"):
    state = view_state.ChatViewState(language)
    for kind, data in events:
        state.apply({"type": kind, "data": data})
    return state


class ViewStateTest(unittest.TestCase):
    def test_conversation_becomes_readable_items(self):
        state = run(ui_fakes.CONVERSATION + ui_fakes.FINISH)
        self.assertEqual([item["kind"] for item in state.items], ["user", "activity", "assistant"])
        activity = state.items[1]
        self.assertEqual((activity["phase"], activity["title"], activity["percent"]), ("done", "Подготовка завершена", 100))
        stages = activity["stages"]
        self.assertEqual([s["title"] for s in stages],
                         ["Модель получена", "Модель проанализирована", "Параметры печати подобраны",
                          "Настройки применены", "Слайсинг завершён", "Результат сохранён"])
        self.assertEqual(stages[0]["summary"], "bracket.stl")
        self.assertEqual(stages[1]["summary"], "62 × 40 × 35 мм")
        self.assertEqual(stages[3]["summary"], "Изменено параметров: 2")
        self.assertTrue(stages[3]["fixed"])
        self.assertEqual(stages[3]["status"], "ok")
        self.assertEqual(activity["summary"], "3D · Generic PETG · normal")
        self.assertEqual([m["value"] for m in activity["metrics"]], ["2 ч 14 мин", "14,6 м", "46 г"])
        self.assertEqual(activity["stageCount"], "6 этапов")
        self.assertFalse(state.running)
        self.assertEqual(state.task_state, "done")

    def test_raw_json_only_in_details(self):
        state = run(ui_fakes.CONVERSATION)
        load = state.items[1]["stages"][0]
        self.assertNotIn("{", load["summary"])
        self.assertNotIn("{", state.items[1]["title"])
        self.assertIn('"path"', load["details"])
        self.assertIn("C:/models/bracket.stl", load["details"])
        self.assertIn("Загружаю модель и анализирую геометрию.", load["details"])
        self.assertNotIn("assistant", [i["kind"] for i in state.items])

    def test_running_tool_then_result_updates_same_card(self):
        state = view_state.ChatViewState("ru")
        state.apply({"type": "user_message", "data": {"text": "x"}})
        self.assertEqual(state.take_ops(), [("append", 0), ("append", 1)])
        state.apply({"type": "tool_call", "data": {"call_id": "a", "name": "slice", "arguments": {}}})
        self.assertEqual(state.take_ops(), [("update", 1)])
        self.assertEqual(state.items[1]["stages"][0]["status"], "running")
        self.assertEqual(state.slice["state"], "slicing")
        state.apply({"type": "slice_progress", "data": {"progress": 0.5}})
        self.assertEqual(state.items[1]["title"], "Выполняю слайсинг")
        self.assertEqual(state.status_text(), "Выполняю слайсинг · 86 %")
        state.apply({"type": "tool_result", "data": {"call_id": "a", "name": "slice", "ok": True,
                                                     "result": {"print_time": "1h 00m", "material_g": 10}}})
        self.assertEqual(state.take_ops(), [("update", 1)])
        self.assertEqual(state.items[1]["stages"][0]["status"], "ok")
        self.assertEqual(len(state.items), 2)
        self.assertEqual(state.slice["state"], "done")

    def test_changes_keep_first_old_value_and_latest_new(self):
        state = run([("setting_changed", {"key": "infill_sparse_density", "label": "Заполнение", "old": "20 %", "value": "30 %"}),
                     ("setting_changed", {"key": "infill_sparse_density", "label": "Заполнение", "old": "30 %", "value": "40 %"})])
        changes = state.changes_list()
        self.assertEqual(len(changes), 1)
        self.assertEqual((changes[0]["old"], changes[0]["value"]), ("20 %", "40 %"))
        self.assertEqual(changes[0]["key"], "infill_sparse_density")

    def test_reset_settings_clears_changes(self):
        state = run([("setting_changed", {"key": "wall_line_count", "old": 2, "value": 4}),
                     ("tool_call", {"call_id": "r", "name": "reset_settings", "arguments": {}}),
                     ("tool_result", {"call_id": "r", "name": "reset_settings", "ok": True, "result": {"ok": True}})])
        self.assertEqual(state.changes_list(), [])

    def test_slice_result_and_exports(self):
        state = run(ui_fakes.CONVERSATION + ui_fakes.FINISH)
        self.assertEqual(state.slice["time"], "2 ч 14 мин")
        self.assertEqual(state.slice["weight"], "46 г")
        self.assertTrue(state.exports["gcode"].endswith("result.gcode"))
        self.assertEqual(len(state.decisions), 3)
        self.assertEqual(state.setup["material"], "Generic PETG")

    def test_error_explains_impact_and_actions(self):
        state = run([("user_message", {"text": "x"}),
                     ("error", {"message": "Ключ API отклонён (HTTP 401)", "code": "auth", "status": 401}),
                     ("done", {})])
        error = state.items[-1]
        self.assertEqual(error["kind"], "error")
        self.assertEqual(error["title"], strings.RU["err_title_auth"])
        self.assertEqual(error["impact"], strings.RU["impact_none"])
        self.assertEqual(error["actions"].split(","), ["settings", "retry"])
        self.assertIn("HTTP 401", error["details"])
        self.assertEqual(state.task_state, "error")

    def test_error_after_changes_offers_continue(self):
        state = run([("user_message", {"text": "x"}),
                     ("tool_call", {"call_id": "1", "name": "set_settings", "arguments": {}}),
                     ("tool_result", {"call_id": "1", "name": "set_settings", "ok": True, "result": {"applied": []}}),
                     ("error", {"message": "LLM недоступна: timed out", "code": "network"})])
        error = state.items[-1]
        self.assertEqual(error["impact"], strings.RU["impact_changed"])
        self.assertIn("continue", error["actions"].split(","))

    def test_classify_error_without_code(self):
        self.assertEqual(view_state.classify_error({"message": "Не задан ключ API."}), "not_configured")
        self.assertEqual(view_state.classify_error({"message": "Достигнут лимит шагов (25)."}), "step_limit")
        self.assertEqual(view_state.classify_error({"message": "LLM недоступна: CERTIFICATE_VERIFY_FAILED"}), "ssl")
        self.assertEqual(view_state.classify_error({"code": "bad_request", "message": "does not support image_url"}), "image")
        self.assertEqual(view_state.classify_error({"message": "weird"}), "internal")

    def test_error_text_is_localized(self):
        state = run([("error", {"message": "Ключ API отклонён", "code": "auth"})], language="en")
        self.assertEqual(state.items[-1]["title"], "The API key was rejected")

    def test_cancel_and_image_notices(self):
        state = run([("assistant_message", {"text": "Остановлено пользователем.", "intermediate": True, "code": "cancelled"}),
                     ("assistant_message", {"text": "x", "intermediate": True, "code": "images_dropped"})])
        self.assertEqual([i["kind"] for i in state.items], ["notice", "notice"])
        self.assertEqual(state.items[0]["actions"], "continue")

    def test_markdown_is_escaped(self):
        html = view_state.markdown_to_styled("**bold** <script>alert(1)</script>\n- item")
        self.assertIn("<b>bold</b>", html)
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("• item", html)

    def test_user_message_shows_files_scene_and_mode(self):
        state = run([("user_message", {"text": "a < b", "files": [{"name": "p.png", "kind": "image"}],
                                       "scene": ["bracket.stl"], "forced_mode": "cylindrical"})])
        item = state.items[0]
        self.assertEqual(item["text"], "a &lt; b")
        self.assertEqual(item["meta"].split("\n"), ["image|p.png", "scene|bracket.stl"])
        self.assertEqual(item["summary"], "5D Spiral")

    def test_rebuild_from_bus_snapshot(self):
        bus = EventBus()
        ui_fakes.publish(bus, ui_fakes.CONVERSATION)
        state = view_state.ChatViewState("ru")
        ops = state.rebuild(bus.snapshot())
        self.assertEqual(ops, [("reset",)])
        again = view_state.ChatViewState("ru")
        again.rebuild(bus.snapshot())
        self.assertEqual(state.items, again.items)

    def test_scene_note_names_object_id(self):
        notes = view_state.scene_note([{"id": "obj3", "name": "gear.stl", "size": {"x": 10, "y": 20, "z": 5}}])
        self.assertIn("object_id=obj3", notes[0])
        self.assertIn("10.0 × 20.0 × 5.0", notes[0])

    def test_modes(self):
        self.assertIsNone(view_state.normalize_mode("auto"))
        self.assertEqual(view_state.normalize_mode("cylindrical_full"), "cylindrical_full")
        self.assertIsNone(view_state.normalize_mode("evil"))

    def test_bus_revision_detects_project_switch(self):
        bus = EventBus()
        bus.publish("user_message", {"text": "a"})
        revision, reset, events = bus.read(None, 0)
        self.assertTrue(reset)
        revision, reset, events = bus.read(revision, events[-1]["id"])
        self.assertEqual((reset, events), (False, []))
        bus.load([])
        self.assertTrue(bus.read(revision, 1)[1])


class StringsTest(unittest.TestCase):
    def test_languages_have_same_keys(self):
        self.assertEqual(sorted(strings.RU.keys()), sorted(strings.EN.keys()))

    def test_format_placeholders_match(self):
        for key in strings.RU:
            self.assertEqual(re.findall(r"%[sd.0-9f]+", strings.RU[key]), re.findall(r"%[sd.0-9f]+", strings.EN[key]), key)

    def test_qml_uses_only_existing_strings(self):
        used = set()
        for name in os.listdir(QML_DIR):
            if name.endswith(".qml"):
                with open(os.path.join(QML_DIR, name), encoding="utf-8") as handle:
                    text = handle.read()
                used.update(re.findall(r"\btxt\.([a-z0-9_]+)", text))
                used.update(re.findall(r'txt\["([a-z0-9_]+)"\]', text))
        missing = sorted(k for k in used if k not in strings.RU)
        self.assertEqual(missing, [])

    def test_tool_titles_cover_requested_labels(self):
        titles = set(view_state.tool_title("ru", name) for name in view_state.TOOL_GROUPS)
        for label in ("Загрузка модели", "Анализ геометрии", "Выбор материала", "Изменение настроек",
                      "Ориентация модели", "Слайсинг", "Сохранение результата"):
            self.assertIn(label, titles)

    def test_error_codes_have_texts(self):
        for code in view_state.ERROR_ACTIONS:
            for language in ("ru", "en"):
                table = strings.table(language)
                self.assertIn("err_title_" + code, table)
                self.assertIn("err_text_" + code, table)
                for action in view_state.ERROR_ACTIONS[code]:
                    self.assertIn("act_" + action, table)


if __name__ == "__main__":
    unittest.main()
