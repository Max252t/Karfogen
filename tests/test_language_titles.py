import re
import tempfile
import time
import unittest
from unittest import mock

import support
from AIAssistant import config
from AIAssistant.agent import prompts
from AIAssistant.agent.agent import TITLE_TOOL_NAME, Agent
from AIAssistant.server import projects, titles
from AIAssistant.server.events import EventBus
from AIAssistant.ui import strings, view_state

import ui_fakes

try:
    import qml_harness
    HAVE_QT = True
except ImportError:
    HAVE_QT = False

TECH_WORDS = set("""
AI LLM API URL Base Enter Shift STL OBJ 3MF JPG JPEG PNG PETG PLA ABS TPU Spiral Consolas OpenAI Chat Completions
tools gpt https api openai com v1 STE Slicer Stereotech JSON MB KB G-code gcode code mm cm Generic normal stl
bracket cover plate with a very long file name for wrapping demo model Assistant English certs obj jpg jpeg png
""".split())


def latin_words(text):
    text = re.sub(r"(?s)<head>.*?</head>|<!DOCTYPE[^>]*>|<[^>]+>|&\w+;", " ", text or "")
    text = re.sub(r"\S*[\\/_]\S*", " ", text)
    words = re.findall(r"(?<![\w.-])[A-Za-z0-9][A-Za-z0-9.\-]*", text)
    words = [w.strip(".-") for w in words]
    return [w for w in words if re.search(r"[A-Za-z]{2}", w) and not re.search(r"[\d.]", w) and w not in TECH_WORDS]


class _Registry(object):
    def __init__(self):
        self.calls = []

    def list_openai(self):
        return [{"type": "function", "function": {"name": "analyze_mesh", "parameters": {"type": "object"}}}]

    def has(self, name):
        return name == "analyze_mesh"

    def call(self, name, args):
        self.calls.append(name)
        return {"size_mm": [1, 2, 3]}


class _ScriptedLlm(object):
    def __init__(self, replies):
        self.replies = list(replies)
        self.requests = []

    def chat(self, messages, tools):
        self.requests.append({"messages": [dict(m) for m in messages], "tools": [t["function"]["name"] for t in tools]})
        return self.replies.pop(0) if self.replies else {"content": "Готово."}


def call(name, arguments, call_id="c1"):
    import json
    return {"id": call_id, "type": "function", "function": {"name": name, "arguments": json.dumps(arguments, ensure_ascii=False)}}


def run_turn(agent, text):
    ok, _ = agent.submit(text)
    agent._thread.join(10)
    return ok


class LanguageChainTest(unittest.TestCase):
    def tearDown(self):
        config.set_value("language", "auto")

    def test_explicit_language_beats_slicer_language(self):
        with mock.patch.object(config, "slicer_language", return_value="en"):
            config.set_value("language", "ru")
            self.assertEqual(config.effective_language(), "ru")
        with mock.patch.object(config, "slicer_language", return_value="ru"):
            config.set_value("language", "en")
            self.assertEqual(config.effective_language(), "en")

    def test_auto_uses_supported_environment_languages_with_documented_fallback(self):
        config.set_value("language", "auto")
        for slicer, expected in (("ru_RU", "ru"), ("ru", "ru"), ("en_US", "en"), ("de_DE", "en"), ("", "en"),
                                 ("zh-CN", "en")):
            with mock.patch.object(config, "slicer_language", return_value=slicer), \
                    mock.patch.object(config, "system_language", return_value="en_US"):
                self.assertEqual(config.effective_language(), expected, slicer)

    def test_russian_windows_locale_wins_over_english_slicer_in_auto(self):
        config.set_value("language", "auto")
        with mock.patch.object(config, "slicer_language", return_value="en_US"), \
                mock.patch.object(config, "system_language", return_value="ru_RU"):
            self.assertEqual(config.effective_language(), "ru")

    def test_auto_turn_contract_follows_russian_request(self):
        config.set_value("language", "auto")
        with mock.patch.object(config, "slicer_language", return_value="en_US"), \
                mock.patch.object(config, "system_language", return_value="en_US"):
            llm = _ScriptedLlm([{"content": "Готово."}])
            agent = Agent(registry=_Registry(), bus=EventBus(), llm=llm)
            run_turn(agent, "Что делать?")
        messages = llm.requests[0]["messages"]
        self.assertTrue(messages[0]["content"].endswith(prompts.LANGUAGE_CONTRACTS["ru"]))
        self.assertTrue(messages[-1]["content"].endswith(prompts.TURN_LANGUAGE_NOTES["ru"]))

    def test_auto_uses_system_language_when_slicer_has_no_supported_language(self):
        config.set_value("language", "auto")
        with mock.patch.object(config, "slicer_language", return_value=""), \
                mock.patch.object(config, "system_language", return_value="ru_RU"):
            self.assertEqual(config.effective_language(), "ru")

    def test_invalid_language_update_does_not_replace_the_current_mode(self):
        config.set_value("language", "ru")
        config.update_settings({"language": "<script>"})
        self.assertEqual(config.language_mode(), "ru")

    def test_unknown_stored_value_is_auto(self):
        config.set_value("language", "klingon")
        self.assertEqual(config.language_mode(), "auto")
        self.assertEqual(config.public_settings()["language"], "auto")

    def test_saving_settings_writes_preferences_to_disk(self):
        with mock.patch.object(config, "persist", return_value=True) as persist:
            config.update_settings({"language": "ru"})
        self.assertTrue(persist.called)
        self.assertEqual(config.get("language"), "ru")

    def test_outgoing_prompt_ends_with_the_strict_contract(self):
        config.set_value("language", "ru")
        llm = _ScriptedLlm([{"content": "Здравствуйте! Опишите деталь."}])
        agent = Agent(registry=_Registry(), bus=EventBus(), llm=llm)
        run_turn(agent, "Привет")
        messages = llm.requests[0]["messages"]
        self.assertEqual(messages[0]["role"], "system")
        self.assertTrue(messages[0]["content"].endswith(prompts.LANGUAGE_CONTRACTS["ru"]))
        self.assertIn("только на русском языке", messages[0]["content"])
        self.assertTrue(messages[-1]["content"].endswith(prompts.TURN_LANGUAGE_NOTES["ru"]))

    def test_switching_ru_en_ru_changes_the_next_request(self):
        llm = _ScriptedLlm([])
        agent = Agent(registry=_Registry(), bus=EventBus(), llm=llm)
        for language in ("ru", "en", "ru"):
            config.update_settings({"language": language})
            run_turn(agent, "Шестерня")
            system = llm.requests[-1]["messages"][0]["content"]
            self.assertTrue(system.endswith(prompts.LANGUAGE_CONTRACTS[language]), language)
            self.assertTrue(llm.requests[-1]["messages"][-1]["content"].endswith(prompts.TURN_LANGUAGE_NOTES[language]))

    def test_russian_ui_strings_have_no_english_words(self):
        problems = []
        for key, value in strings.RU.items():
            words = latin_words(value)
            if words:
                problems.append((key, words))
        self.assertEqual(problems, [])

    def test_work_card_and_errors_follow_the_language(self):
        for language, needle in (("ru", "Подготовка завершена"), ("en", "Preparation complete")):
            state = view_state.ChatViewState(language)
            for kind, data in ui_fakes.CONVERSATION + ui_fakes.FINISH:
                state.apply({"type": kind, "data": data})
            self.assertEqual(state.items[1]["title"], needle)
        state = view_state.ChatViewState("ru")
        state.apply({"type": "error", "data": {"message": "HTTP 401", "code": "auth"}})
        self.assertEqual(latin_words(state.items[-1]["title"] + state.items[-1]["text"]), [])


@unittest.skipUnless(HAVE_QT, "PyQt5 is required for the controller tests")
class LanguageControllerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = qml_harness.app()

    def setUp(self):
        self.controller, self.agent, self.bus, self.registry, self.manager = ui_fakes.fresh_environment()

    def tearDown(self):
        config.set_value("language", "auto")
        self.controller.stop()

    def test_saving_through_the_qml_slot_updates_the_ui_immediately(self):
        changed = []
        self.controller.languageChanged.connect(lambda: changed.append(True))
        with mock.patch.object(config, "persist", return_value=True):
            self.assertTrue(self.controller.saveSettings({"language": "en"}))
            self.assertEqual(self.controller.strings["tab_projects"], "Projects")
            self.assertTrue(self.controller.saveSettings({"language": "ru"}))
        self.assertEqual(config.get("language"), "ru")
        self.assertEqual(self.controller.language, "ru")
        self.assertEqual(self.controller.strings["tab_projects"], "Проекты")
        self.assertEqual(self.controller.settings["language"], "ru")
        self.assertEqual(len(changed), 2)

    def test_invalid_language_from_qml_is_ignored(self):
        with mock.patch.object(config, "persist", return_value=True):
            self.controller.saveSettings({"language": "ru"})
            self.controller.saveSettings({"language": "<script>"})
        self.assertEqual(config.get("language"), "ru")

    def test_default_project_name_is_localized(self):
        with mock.patch.object(config, "persist", return_value=True):
            self.controller.saveSettings({"language": "ru"})
            self.manager.ensure_current()
            self.controller.refreshProjects()
            self.assertEqual(self.controller.projectName, "Новый проект")
            self.controller.saveSettings({"language": "en"})
            self.assertEqual(self.controller.projectName, "New project")
            self.assertEqual(self.controller.projectModel.items()[0]["name"], "New project")

    def test_russian_window_shows_no_english_ui_text(self):
        with mock.patch.object(config, "persist", return_value=True):
            self.controller.saveSettings({"language": "ru"})
        engine, context, component, window, errors = qml_harness.create(self.controller)
        self.assertEqual(errors, [])
        try:
            window.show()
            self.controller.send("Кронштейн")
            ui_fakes.publish(self.bus, ui_fakes.CONVERSATION)
            self.controller.tick()
            self.pump()
            ui_fakes.publish(self.bus, ui_fakes.FINISH)
            self.agent.running = False
            self.controller.tick()
            self.pump()
            found = {}
            for tab in ("chat", "result", "projects"):
                self.controller.showTab.emit(tab)
                self.pump()
                for item in visual_items(window.contentItem()):
                    if not item.isVisible() or item.metaObject().indexOfProperty("text") < 0:
                        continue
                    text = item.property("text")
                    if isinstance(text, str) and latin_words(text):
                        found[text] = latin_words(text)
            self.assertEqual(found, {})
        finally:
            window.close()
            window.deleteLater()
            self.pump()

    def pump(self, seconds=0.3):
        deadline = time.time() + seconds
        while time.time() < deadline:
            self.app.processEvents()
            time.sleep(0.01)


def visual_items(root):
    stack = [root]
    while stack:
        item = stack.pop(0)
        yield item
        stack.extend(item.childItems())


class TitleTest(unittest.TestCase):
    def test_greetings_never_become_titles(self):
        for text in ("Привет", "привет!", "Здравствуйте, спасибо", "Добрый день", "Hi", "Hello there!", "Thanks",
                     "Что ты умеешь?", "Ок", "👋"):
            self.assertIsNone(titles.suggest_title(text), text)

    def test_russian_requests(self):
        self.assertEqual(titles.suggest_title("Подготовь кронштейн для печати из PETG"), "Кронштейн из PETG")
        self.assertEqual(titles.suggest_title("Нужно напечатать шестерню для редуктора"), "Шестерня редуктора")
        self.assertEqual(titles.suggest_title("Нужно крепление для датчика", ["bracket_final_v12.stl"]),
                         "Крепление датчика")

    def test_english_requests(self):
        self.assertEqual(titles.suggest_title("Prepare a bracket for printing in PETG", language="en"), "PETG bracket")
        self.assertEqual(titles.suggest_title("I need to print a gear for a gearbox", language="en"),
                         "Gear for gearbox")

    def test_model_file_is_used_without_extension_or_versions(self):
        self.assertEqual(titles.suggest_title("Сделай прочнее", ["bracket_final_v12.stl"]), "Bracket")
        self.assertEqual(titles.title_from_file("C:/models/GearBoxCover-rev3_2024.3mf"), "Gear Box Cover")
        self.assertIsNone(titles.suggest_title("Привет"))

    def test_service_notes_are_ignored(self):
        text = ("\n\nПрикреплён файл: Шестерня.stl, путь: C:/x/Шестерня.stl\nЯзык ответа: русский.\n"
                "Режим печати зафиксирован пользователем: 5D.")
        self.assertIsNone(titles.title_from_text(text))
        self.assertEqual(titles.suggest_title(text, ["Шестерня.stl"]), "Шестерня")
        self.assertIsNone(projects.title_from_events([
            {"type": "user_message", "data": {"text": strings.RU["continue_prompt"]}}, {"type": "done", "data": {}}]))

    def test_long_request_is_short(self):
        text = ("Напечатай, пожалуйста, очень прочный корпус редуктора привода конвейерной ленты для пищевого "
                "производства с рёбрами жёсткости и посадочными местами под подшипники, нагрузка большая")
        title = titles.suggest_title(text)
        self.assertLessEqual(len(title), titles.MAX_TITLE_CHARS)
        self.assertLessEqual(len(title.split()), titles.MAX_TITLE_WORDS)
        self.assertTrue(title.startswith("Очень прочный корпус"))

    def test_agent_titles_are_sanitized(self):
        self.assertEqual(titles.sanitize_title("«Проект: Кронштейн из PETG.»"), "Кронштейн из PETG")
        self.assertIsNone(titles.sanitize_title("Привет"))
        self.assertIsNone(titles.sanitize_title("C:/x/part.stl"))
        self.assertEqual(titles.sanitize_title("шестерня редуктора"), "Шестерня редуктора")


class ProjectTitleFlowTest(unittest.TestCase):
    def setUp(self):
        config.set_value("results_dir", tempfile.mkdtemp())
        config.set_value("language", "ru")
        self.bus = EventBus()
        self.registry = _Registry()

    def tearDown(self):
        config.set_value("language", "auto")

    def manager_with(self, replies):
        llm = _ScriptedLlm(replies)
        agent = Agent(registry=self.registry, bus=self.bus, llm=llm)
        manager = projects.ProjectManager()
        manager.attach(agent, self.bus)
        manager.ensure_current()
        return manager, agent, llm

    def name(self, manager):
        return manager.current()["name"]

    def test_greetings_keep_the_default_until_a_task_appears(self):
        manager, agent, llm = self.manager_with([{"content": "Здравствуйте!"}, {"content": "Привет ещё раз"},
                                                 {"content": "Готово."}])
        run_turn(agent, "Привет")
        self.assertEqual(self.name(manager), "Новый проект")
        run_turn(agent, "Добрый день!")
        self.assertEqual(self.name(manager), "Новый проект")
        run_turn(agent, "Нужно напечатать шестерню для редуктора")
        self.assertEqual(self.name(manager), "Шестерня редуктора")
        self.assertFalse(manager.current()["wants_title"])

    def test_agent_title_is_used_silently_and_only_once(self):
        manager, agent, llm = self.manager_with([
            {"content": "", "tool_calls": [call(TITLE_TOOL_NAME, {"title": "Крепление датчика"}, "t1"),
                                           call("analyze_mesh", {}, "t2")]},
            {"content": "Готово, модель проанализирована."},
            {"content": "Ещё раз."}])
        run_turn(agent, "Вот модель крепления, сделай прочнее")
        self.assertIn(TITLE_TOOL_NAME, llm.requests[0]["tools"])
        self.assertEqual(self.name(manager), "Крепление датчика")
        events = self.bus.snapshot()
        dumped = repr(events)
        self.assertNotIn(TITLE_TOOL_NAME, dumped)
        self.assertNotIn("Крепление датчика", dumped)
        self.assertEqual([e["data"]["name"] for e in events if e["type"] == "tool_call"], ["analyze_mesh"])
        run_turn(agent, "Нужно напечатать шестерню для редуктора")
        self.assertNotIn(TITLE_TOOL_NAME, llm.requests[-1]["tools"])
        self.assertEqual(self.name(manager), "Крепление датчика")

    def test_pending_title_removes_the_internal_tool_before_autosave(self):
        manager, agent, llm = self.manager_with([])
        self.assertTrue(manager.wants_title())
        self.assertTrue(manager.propose_title("Крепление датчика"))
        self.assertFalse(manager.wants_title())

    def test_title_tool_does_not_create_a_work_card(self):
        manager, agent, llm = self.manager_with([
            {"content": "", "tool_calls": [call(TITLE_TOOL_NAME, {"title": "Кронштейн из PETG"})]},
            {"content": "Уточните нагрузку."}])
        run_turn(agent, "Подготовь кронштейн для печати из PETG")
        state = view_state.ChatViewState("ru")
        state.rebuild(self.bus.snapshot())
        self.assertEqual(state.items[1]["phase"], "quiet")
        self.assertEqual(self.name(manager), "Кронштейн из PETG")

    def test_manual_rename_is_never_overwritten(self):
        manager, agent, llm = self.manager_with([
            {"content": "", "tool_calls": [call(TITLE_TOOL_NAME, {"title": "Шестерня"})]}, {"content": "Ок"}])
        projects.rename_project(manager.current_id, "Моё название")
        self.assertFalse(manager.wants_title())
        self.assertFalse(manager.propose_title("Шестерня"))
        run_turn(agent, "Нужно напечатать шестерню для редуктора")
        self.assertNotIn(TITLE_TOOL_NAME, llm.requests[0]["tools"])
        self.assertEqual(self.name(manager), "Моё название")

    def test_repeated_saves_keep_a_stable_title(self):
        manager, agent, llm = self.manager_with([{"content": "Готово."}, {"content": "Готово."}])
        run_turn(agent, "Подготовь кронштейн для печати из PETG")
        self.assertEqual(self.name(manager), "Кронштейн из PETG")
        run_turn(agent, "А теперь шестерню для редуктора")
        manager.save_current()
        manager.save_current()
        self.assertEqual(self.name(manager), "Кронштейн из PETG")

    def test_english_default_and_title(self):
        config.set_value("language", "en")
        manager, agent, llm = self.manager_with([{"content": "Hello!"}, {"content": "Done."}])
        self.assertEqual(self.name(manager), "New project")
        run_turn(agent, "Hi")
        self.assertEqual(self.name(manager), "New project")
        run_turn(agent, "Prepare a bracket for printing in PETG")
        self.assertEqual(self.name(manager), "PETG bracket")

    def test_old_projects_without_new_fields_still_open(self):
        meta = projects.create_project()
        project = projects.load_project(meta["id"])
        for key in ("title_source",):
            project.pop(key, None)
        project["name"] = "Привет"
        projects._write(project)
        self.assertTrue(projects._meta(projects.load_project(meta["id"]))["wants_title"])
        legacy = projects.create_project()
        project = projects.load_project(legacy["id"])
        project.pop("title_source", None)
        project["name"] = "Кронштейн под нагрузку"
        projects._write(project)
        manager = projects.ProjectManager()
        manager.attach(Agent(registry=self.registry, bus=self.bus, llm=_ScriptedLlm([])), self.bus)
        manager.open(legacy["id"])
        self.assertFalse(manager.wants_title())
        manager.save_current()
        self.assertEqual(manager.current()["name"], "Кронштейн под нагрузку")
        manager.open(meta["id"])
        self.bus.publish("user_message", {"text": "Нужна втулка"})
        self.bus.publish("done", {})
        manager.save_current()
        self.assertEqual(manager.current()["name"], "Втулка")


if __name__ == "__main__":
    unittest.main()
