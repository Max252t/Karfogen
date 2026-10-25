import json
import random
import unittest

import support
from AIAssistant.server.events import EventBus
from AIAssistant.ui import live_status, markdown, progress, strings, view_state

import ui_fakes

try:
    import qml_harness
    HAVE_QT = True
except ImportError:
    HAVE_QT = False


def run(events, language="ru"):
    state = view_state.ChatViewState(language)
    for kind, data in events:
        state.apply({"type": kind, "data": data})
    return state


def call(call_id, name, ok=True, result=None, error="boom"):
    events = [("tool_call", {"call_id": call_id, "name": name, "arguments": {}})]
    data = {"call_id": call_id, "name": name, "ok": ok}
    if ok:
        data["result"] = result if result is not None else {}
    else:
        data["error"] = error
    events.append(("tool_result", data))
    return events


class ProgressTrackerTest(unittest.TestCase):
    def test_unknown_stage_is_indeterminate(self):
        tracker = progress.ProgressTracker()
        tracker.start()
        self.assertTrue(tracker.indeterminate)
        self.assertEqual(tracker.percent, 0)
        tracker.tool_started("mystery_tool")
        self.assertTrue(tracker.indeterminate)
        tracker.tool_started("analyze_mesh")
        self.assertFalse(tracker.indeterminate)
        self.assertEqual(tracker.stage, "geometry")
        self.assertEqual(tracker.percent, 20)

    def test_tools_map_to_stages(self):
        expected = {"load_model": "scene", "analyze_mesh": "geometry", "get_object_bounds": "geometry",
                    "recommend_setup": "recommend", "set_material": "recommend", "set_settings": "settings",
                    "lay_flat": "orientation", "arrange_all": "orientation", "slice": "slicing",
                    "get_slice_result": "slicing", "export_gcode": "export", "save_project_3mf": "export",
                    "reset_settings": "prepare"}
        for name, stage in expected.items():
            self.assertEqual(progress.stage_for_tool(name), stage, name)
        for name in view_state.TOOL_GROUPS:
            self.assertIn(progress.stage_for_tool(name), progress.STAGE_ORDER, name)

    def test_stage_ranges_cover_zero_to_hundred(self):
        self.assertEqual(progress.STAGES[0][1], 0.0)
        self.assertEqual(progress.STAGES[-1][2], 1.0)
        for previous, current in zip(progress.STAGES, progress.STAGES[1:]):
            self.assertAlmostEqual(previous[2], current[1])

    def test_skipped_stages_are_counted(self):
        tracker = progress.ProgressTracker()
        tracker.start()
        tracker.tool_started("slice")
        self.assertEqual(tracker.percent, 78)

    def test_repeated_tools_stay_inside_their_stage(self):
        tracker = progress.ProgressTracker()
        tracker.start()
        for _ in range(50):
            tracker.tool_started("set_settings")
            tracker.tool_finished("set_settings", ok=False)
            tracker.tool_started("set_settings")
            tracker.tool_finished("set_settings")
        low, high = progress.STAGE_RANGES["settings"]
        self.assertLess(tracker.value, high)
        self.assertGreater(tracker.value, low)
        self.assertLess(tracker.percent, 70)

    def test_progress_never_decreases_on_random_sequences(self):
        names = list(progress.TOOL_STAGES) + ["unknown"]
        rng = random.Random(7)
        for _ in range(200):
            tracker = progress.ProgressTracker()
            tracker.start()
            previous = tracker.value
            for _ in range(40):
                action = rng.random()
                name = rng.choice(names)
                if action < 0.4:
                    tracker.tool_started(name)
                elif action < 0.8:
                    tracker.tool_finished(name, rng.random() > 0.3)
                elif action < 0.95:
                    tracker.slice_progress(rng.random())
                else:
                    tracker.answer()
                self.assertGreaterEqual(tracker.value, previous)
                self.assertLess(tracker.percent, 100)
                previous = tracker.value

    def test_returning_to_an_earlier_stage_keeps_the_value(self):
        tracker = progress.ProgressTracker()
        tracker.start()
        tracker.slice_progress(0.5)
        value = tracker.value
        tracker.tool_started("set_settings")
        tracker.tool_finished("set_settings")
        self.assertEqual(tracker.stage, "settings")
        self.assertEqual(tracker.value, value)

    def test_hundred_only_after_done(self):
        tracker = progress.ProgressTracker()
        tracker.start()
        tracker.slice_progress(1.0)
        tracker.tool_started("export_gcode")
        tracker.tool_finished("export_gcode")
        tracker.answer()
        self.assertEqual(tracker.percent, 98)
        tracker.done()
        self.assertEqual((tracker.state, tracker.percent, tracker.value), ("done", 100, 1.0))

    def test_real_slicing_progress_maps_to_its_range(self):
        tracker = progress.ProgressTracker()
        tracker.start()
        for fraction, percent in ((0.0, 78), (0.10, 79), (0.55, 87), (0.95, 94), (1.0, 95)):
            tracker.slice_progress(fraction)
            self.assertEqual(tracker.percent, percent, fraction)

    def test_error_and_cancel_keep_the_reached_value(self):
        for finish, state in (("fail", "error"), ("cancel", "cancelled")):
            tracker = progress.ProgressTracker()
            tracker.start()
            tracker.tool_started("analyze_mesh")
            tracker.tool_finished("analyze_mesh")
            value = tracker.value
            getattr(tracker, finish)()
            tracker.done()
            tracker.slice_progress(0.9)
            self.assertEqual((tracker.state, tracker.value), (state, value))
            self.assertLess(tracker.percent, 100)


class TurnGroupingTest(unittest.TestCase):
    def test_related_tools_are_grouped_into_one_stage(self):
        events = [("user_message", {"text": "x"})]
        events += call("a", "get_changed_settings", result={"changes": []})
        events += call("b", "load_model", result={"loaded": [{"name": "part.stl", "size_mm": [1, 2, 3]}]})
        events += call("c", "analyze_mesh", result={"size_mm": [10, 20, 30.5], "volume_cm3": 4.25})
        events += call("d", "get_object_bounds", result={"size_mm": [10, 20, 30.5], "fits": True})
        events += call("e", "set_material", result={"name": "PETG"})
        events += call("f", "set_quality_profile", result={"name": "normal"})
        events += call("g", "search_settings", result={"settings": []})
        events += call("h", "set_setting", result={"changes": [{"key": "a"}]})
        events += call("i", "set_settings", result={"applied": [{"key": "b"}]})
        events += call("j", "lay_flat", result={})
        events += call("k", "move_object", result={})
        events += call("l", "slice", result={"print_time_s": 60})
        events += call("m", "get_slice_result", result={"print_time_s": 60})
        events += [("assistant_message", {"text": "Готово."}), ("done", {})]
        state = run(events)
        stages = state.items[1]["stages"]
        self.assertEqual([s["group"] for s in stages], ["model", "geometry", "recommend", "settings", "placement", "slicing"])
        self.assertEqual(stages[1]["summary"], "10 × 20 × 30,5 мм")
        facts = dict((f["label"], f["value"]) for f in stages[1]["facts"])
        self.assertEqual(facts["Объём"], "4,25 см³")
        self.assertEqual(facts["Помещается на стол"], "да")
        self.assertIn("get_changed_settings", stages[0]["details"])
        self.assertIn("search_settings", stages[2]["details"])
        self.assertTrue(all(s["status"] == "ok" for s in stages))

    def test_only_service_reads_become_a_quiet_context_line(self):
        state = run([("user_message", {"text": "Какой материал выбрать?"})] + call("a", "list_materials", result={})
                    + [("assistant_message", {"text": "PETG."}), ("done", {})])
        activity = state.items[1]
        self.assertEqual([s["title"] for s in activity["stages"]], ["Контекст проверен"])

    def test_turn_without_tools_hides_the_card(self):
        state = run([("user_message", {"text": "Привет"}), ("assistant_message", {"text": "Здравствуйте"}),
                     ("done", {})])
        self.assertEqual(state.items[1]["phase"], "quiet")

    def test_fixed_error_counts_as_success_and_stays_in_details(self):
        events = [("user_message", {"text": "x"})]
        events += call("a", "set_settings", ok=False, error="Setting 'wall_count' not found")
        state = run(events)
        stage = state.items[1]["stages"][0]
        self.assertEqual((stage["status"], stage["title"]), ("error", "Настройки не применены"))
        self.assertTrue(state.items[1]["serious"])
        for kind, data in call("b", "set_settings", result={"applied": [{"key": "wall_line_count"}]}):
            state.apply({"type": kind, "data": data})
        stage = state.items[1]["stages"][0]
        self.assertEqual((stage["status"], stage["fixed"], stage["title"]), ("ok", True, "Настройки применены"))
        self.assertIn("wall_count", stage["details"])
        self.assertFalse(state.items[1]["serious"])

    def test_unfixed_error_is_shown_inside_its_stage(self):
        events = [("user_message", {"text": "x"})] + call("a", "load_model", ok=False, error="File not found\nTrace")
        events += [("assistant_message", {"text": "Не нашёл файл."}), ("done", {})]
        state = run(events)
        stage = state.items[1]["stages"][0]
        self.assertEqual((stage["status"], stage["summary"]), ("error", "File not found"))
        self.assertEqual(state.items[1]["phase"], "done")

    def test_error_keeps_percent_and_explains_kept_work(self):
        events = [("user_message", {"text": "x"})] + call("a", "analyze_mesh", result={})
        events += [("error", {"message": "LLM недоступна", "code": "network"}), ("done", {})]
        state = run(events)
        activity = state.items[1]
        self.assertEqual(activity["phase"], "error")
        self.assertEqual(activity["percent"], 28)
        self.assertIn("28 %", activity["impact"])
        self.assertEqual(state.items[2]["kind"], "error")

    def test_cancel_shows_stopped_card_with_continue(self):
        events = [("user_message", {"text": "x"})] + call("a", "load_model", result={})
        events += [("status", {"text": "Останавливаю"})]
        state = run(events)
        self.assertEqual(state.items[1]["title"], "Останавливаю…")
        state.apply({"type": "assistant_message", "data": {"text": "Остановлено пользователем.", "intermediate": True,
                                                           "code": "cancelled"}})
        state.apply({"type": "done", "data": {}})
        activity = state.items[1]
        self.assertEqual((activity["phase"], activity["title"], activity["actions"]), ("cancelled", "Остановлено", "continue"))
        self.assertEqual(len(state.items), 2)

    def test_progress_is_restored_after_reopening(self):
        bus = EventBus()
        ui_fakes.publish(bus, ui_fakes.CONVERSATION)
        live = view_state.ChatViewState("ru")
        for event in bus.snapshot():
            live.apply(event)
        reopened = view_state.ChatViewState("ru")
        reopened.rebuild(bus.snapshot())
        self.assertEqual(reopened.items, live.items)
        self.assertEqual(reopened.items[1]["percent"], 85)
        self.assertEqual(reopened.items[1]["phase"], "running")

    def test_interrupted_turn_is_closed_when_the_agent_is_gone(self):
        state = run(ui_fakes.CONVERSATION[:7])
        state.finish_open_turn()
        self.assertEqual(state.items[1]["phase"], "cancelled")
        self.assertIsNone(state.turn)

    def test_manual_export_is_one_compact_line(self):
        state = run(call("x", "export_gcode", result={"path": "C:/r/part/result.gcode"}))
        self.assertEqual([i["kind"] for i in state.items], ["activity"])
        activity = state.items[0]
        self.assertEqual(activity["phase"], "done")
        self.assertEqual(activity["stages"][0]["summary"], "result.gcode")
        self.assertIsNone(state.turn)

    def test_updates_touch_only_the_changed_turn(self):
        state = run(ui_fakes.CONVERSATION + ui_fakes.FINISH)
        state.take_ops()
        state.apply({"type": "user_message", "data": {"text": "ещё"}})
        state.take_ops()
        for kind, data in call("z", "analyze_mesh", result={}):
            state.apply({"type": kind, "data": data})
        self.assertEqual(state.take_ops(), [("update", 4)])

    def test_parameter_changes_are_structured_and_localized(self):
        state = run([("user_message", {"text": "x"})] + call("a", "set_settings", result={"applied": []}) + [
            ("setting_changed", {"key": "layer_height", "label": "Высота слоя", "old": "0.2 мм", "value": "0.15 мм"}),
            ("setting_changed", {"key": "support_enable", "label": "Поддержки", "old": "True", "value": "False"}),
            ("setting_changed", {"key": "wall_line_count", "label": "Стенки", "old": 2, "value": 4}),
            ("setting_changed", {"key": "speed_print", "label": "Скорость", "old": "60", "value": "60"}),
            ("setting_changed", {"key": "infill_sparse_density", "label": "Заполнение", "old": 0.15000000000000002,
                                 "value": 0.4})])
        changes = dict((c["key"], (c["old"], c["value"])) for c in state.items[1]["changes"])
        self.assertEqual(changes["layer_height"], ("0,2 мм", "0,15 мм"))
        self.assertEqual(changes["support_enable"], ("Вкл.", "Выкл."))
        self.assertEqual(changes["wall_line_count"], ("2", "4"))
        self.assertEqual(changes["infill_sparse_density"], ("0,15", "0,4"))
        self.assertNotIn("speed_print", changes)
        self.assertEqual(state.items[1]["stages"][0]["summary"], "Изменено параметров: 4")
        english = view_state.format_value("en", "0.15 mm")
        self.assertEqual(english, "0.15 mm")

    def test_decisions_fill_the_summary(self):
        state = run([("user_message", {"text": "x"})] + call("a", "recommend_setup", result={}) + [
            ("decision", {"title": "Принятые решения", "rows": [["Режим", "3D", "не тело вращения"],
                                                                 ["Материал", "generic_petg (PETG)", "влага"],
                                                                 ["Профиль качества", "normal", ""]]}),
            ("done", {})])
        activity = state.items[1]
        self.assertEqual(activity["summary"], "3D · generic_petg · normal")
        self.assertEqual(activity["decisions"][0], {"label": "Режим", "value": "3D", "reason": "не тело вращения"})
        self.assertEqual([i["kind"] for i in state.items], ["user", "activity"])


class AnswerTest(unittest.TestCase):
    def test_long_answer_is_collapsible_without_losing_text(self):
        state = run([("user_message", {"text": "x"}), ("assistant_message", {"text": ui_fakes.LONG_ANSWER_RU})])
        answer = state.items[-1]
        self.assertTrue(answer["collapsible"])
        self.assertEqual(answer["plain"], ui_fakes.LONG_ANSWER_RU)
        joined = json.dumps(answer["blocks"], ensure_ascii=False)
        self.assertIn("напишите, переключу профиль на high", joined)

    def test_short_answer_questions_and_warnings_are_never_collapsed(self):
        self.assertFalse(markdown.should_collapse("Готово. Режим 3D."))
        question = ui_fakes.LONG_ANSWER_RU + "\n\nМасштабировать модель до 90 %?"
        self.assertTrue(markdown.is_long(question))
        self.assertFalse(markdown.should_collapse(question))
        warning = "⚠ Внимание: материал токсичен при нагреве. " + "x" * 600
        self.assertFalse(markdown.should_collapse(warning))

    def test_markdown_blocks(self):
        blocks = markdown.parse_blocks("# Итог\nТекст **жирный** и `code`\n\n- один\n  - вложенный\n1. первый\n\n"
                                       "| A | B |\n| --- | :-: |\n| 1 | 2 |\n\n```json\n{\"a\": 1}\n```\n[ссылка](https://example.com)")
        self.assertEqual([b["type"] for b in blocks], ["heading", "paragraph", "list", "list", "table", "code", "paragraph"])
        self.assertIn("<b>жирный</b>", blocks[1]["text"])
        self.assertIn("Consolas", blocks[1]["text"])
        self.assertEqual([i["level"] for i in blocks[2]["items"]], [0, 1])
        self.assertEqual(blocks[3]["items"][0]["marker"], "1.")
        self.assertEqual((blocks[4]["header"], blocks[4]["rows"]), (["A", "B"], [["1", "2"]]))
        self.assertEqual((blocks[5]["lang"], blocks[5]["text"]), ("json", '{"a": 1}'))
        self.assertIn('<a href="https://example.com">ссылка</a>', blocks[6]["text"])
        self.assertNotIn("---", json.dumps(blocks))

    def test_markdown_never_executes_html(self):
        blocks = markdown.parse_blocks('<img src=x onerror=alert(1)> **b** [x](javascript:alert(1)) `<b>`')
        text = blocks[0]["text"]
        self.assertNotIn("<img", text)
        self.assertNotIn('href="javascript', text)
        self.assertIn("&lt;img", text)
        self.assertIn("&lt;b&gt;", text)

    def test_markdown_markers_inside_url_cannot_break_link_markup(self):
        text = markdown.inline("[result](https://example.com/**part**?name=a_b)")
        self.assertEqual(text, '<a href="https://example.com/**part**?name=a_b">result</a>')
        self.assertNotIn("<b>", text)
        self.assertNotIn("<i>", text)

    def test_paths_with_underscores_are_not_italic(self):
        self.assertNotIn("<i>", markdown.inline("C:/results/gear_module_1_5/result.gcode"))


class LiveStatusTest(unittest.TestCase):
    def test_phrases_exist_for_every_stage_and_language(self):
        for language in ("ru", "en"):
            for stage in progress.STAGE_ORDER + ("unknown",):
                self.assertTrue(live_status.phrases(language, stage), (language, stage))
        self.assertEqual(sorted(live_status.PHRASES["ru"]), sorted(live_status.PHRASES["en"]))

    def test_rate_limit_and_no_repeats(self):
        status = live_status.LiveStatus("ru", seed=3)
        now = 1000.0
        self.assertTrue(status.update("geometry", "running", now))
        first = status.text
        self.assertFalse(status.update("geometry", "running", now + 5.9))
        self.assertEqual(status.text, first)
        changes = []
        previous = first
        for step in range(1, 200):
            now += 1.0
            if status.update("geometry", "running", now):
                changes.append(now)
                self.assertNotEqual(status.text, previous)
                previous = status.text
        gaps = [b - a for a, b in zip(changes, changes[1:])]
        self.assertTrue(gaps)
        self.assertTrue(all(live_status.MIN_INTERVAL <= gap <= live_status.MAX_INTERVAL + 1 for gap in gaps), gaps)

    def test_humor_is_rare_and_stops_on_problems(self):
        status = live_status.LiveStatus("ru", seed=11)
        funny = set(live_status.phrases("ru", "slicing", humor=True))
        picks = []
        for index in range(300):
            status.update("slicing", "running", index * 11.0)
            picks.append(status.text in funny)
        self.assertTrue(any(picks))
        self.assertLess(sum(picks), len(picks) / 3)
        self.assertFalse(any(a and b for a, b in zip(picks, picks[1:])))
        status.update("slicing", "running", 10000.0, serious=True)
        self.assertNotIn(status.text, funny)
        for state in ("error", "cancelled", "done"):
            status.update("slicing", state, 20000.0)
            self.assertEqual(status.text, "")

    def test_disabled_setting_hides_statuses(self):
        status = live_status.LiveStatus("en", seed=1)
        status.update("slicing", "running", 1.0, enabled=False)
        self.assertEqual(status.text, "")


@unittest.skipUnless(HAVE_QT, "PyQt5 is required for the controller tests")
class LiveStatusControllerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = qml_harness.app()

    def test_live_statuses_never_reach_history_events_or_project(self):
        from AIAssistant import config
        from AIAssistant.server import projects
        controller, agent, bus, registry, manager = ui_fakes.fresh_environment()
        try:
            controller.send("Кронштейн")
            ui_fakes.publish(bus, ui_fakes.CONVERSATION)
            controller.tick()
            text = controller.liveStatus
            self.assertTrue(text)
            known = set(p for table in (live_status.PHRASES, live_status.HUMOR) for stages in table.values()
                        for pool in stages.values() for p in pool)
            self.assertIn(text, known)
            dumped = json.dumps([agent.get_history(), bus.snapshot(), controller.messageModel.items()],
                                ensure_ascii=False)
            for phrase in known:
                self.assertNotIn(phrase, dumped)
            manager.save_current()
            saved = json.dumps(projects.load_project(manager.current_id), ensure_ascii=False)
            for phrase in known:
                self.assertNotIn(phrase, saved)
            config.set_value("live_status", False)
            controller.tick()
            self.assertEqual(controller.liveStatus, "")
        finally:
            config.set_value("live_status", True)
            controller.stop()

    def test_model_updates_only_changed_roles(self):
        controller, agent, bus, registry, manager = ui_fakes.fresh_environment()
        try:
            controller.send("x")
            ui_fakes.publish(bus, ui_fakes.CONVERSATION[:5])
            controller.tick()
            seen = []
            controller.messageModel.dataChanged.connect(lambda first, last, roles: seen.append((first.row(), list(roles))))
            bus.publish("tool_call", {"call_id": "q", "name": "analyze_mesh", "arguments": {}})
            controller.tick()
            names = controller.messageModel.roleNames()
            self.assertEqual([row for row, roles in seen], [1])
            changed = set(names[r].decode() for r in seen[0][1])
            self.assertIn("stages", changed)
            self.assertNotIn("text", changed)
            self.assertNotIn("uid", changed)
        finally:
            controller.stop()


class StringsCountTest(unittest.TestCase):
    def test_russian_plurals(self):
        self.assertEqual([strings.count("ru", n, "stages") for n in (1, 2, 5, 11, 21, 22, 25)],
                         ["1 этап", "2 этапа", "5 этапов", "11 этапов", "21 этап", "22 этапа", "25 этапов"])
        self.assertEqual(strings.count("en", 1, "changes"), "1 change")
        self.assertEqual(strings.count("en", 3, "changes"), "3 changes")


if __name__ == "__main__":
    unittest.main()
