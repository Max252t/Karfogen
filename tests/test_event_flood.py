import tempfile
import unittest

import support
from AIAssistant import config
from AIAssistant.server import projects
from AIAssistant.server.events import EventBus


class FakeAgent(object):
    def __init__(self):
        self.history = []
        self.running = False
        self.on_finished = None
        self.on_progress = None

    def is_running(self):
        return self.running

    def get_history(self):
        return list(self.history)

    def set_history(self, history):
        self.history = list(history)


def flood(bus, count=3000):
    for index in range(count):
        bus.publish("status", {"text": "step %d" % index})
        bus.publish("slice_progress", {"state": "slicing", "progress": index / 1000.0, "percent": index % 100})


class EventBusFloodTest(unittest.TestCase):
    def test_messages_survive_a_flood_of_progress_events(self):
        bus = EventBus()
        bus.publish("user_message", {"text": "Шестерня под нагрузку"})
        flood(bus)
        bus.publish("assistant_message", {"text": "Готово"})
        types = [event["type"] for event in bus.snapshot()]
        self.assertIn("user_message", types)
        self.assertIn("assistant_message", types)
        self.assertLessEqual(len(types), bus.MAX_EVENTS)

    def test_tool_events_are_kept_over_progress_events(self):
        bus = EventBus()
        for index in range(300):
            bus.publish("tool_call", {"call_id": "c%d" % index})
        flood(bus, 2000)
        kept = [event for event in bus.snapshot() if event["type"] == "tool_call"]
        self.assertEqual(len(kept), 300)

    def test_identical_progress_events_are_coalesced(self):
        bus = EventBus()
        for _ in range(50):
            bus.publish("slice_progress", {"state": "slicing", "progress": 0.5, "percent": 50})
            bus.publish("status", {"text": "slicing"})
        self.assertEqual(len(bus.snapshot()), 2)

    def test_only_volatile_events_are_coalesced(self):
        bus = EventBus()
        for _ in range(3):
            bus.publish("tool_call", {"call_id": "same"})
        self.assertEqual(len(bus.snapshot()), 3)

    def test_ids_stay_monotonic_after_eviction(self):
        bus = EventBus()
        flood(bus, 1500)
        ids = [event["id"] for event in bus.snapshot()]
        self.assertEqual(ids, sorted(ids))
        self.assertEqual(bus.get_since(ids[-1])["events"], [])

    def test_hard_cap_still_applies_to_important_events(self):
        bus = EventBus()
        for index in range(bus.MAX_EVENTS + 50):
            bus.publish("tool_call", {"call_id": "c%d" % index})
        self.assertEqual(len(bus.snapshot()), bus.MAX_EVENTS)


class SavedChatTest(unittest.TestCase):
    def setUp(self):
        config.set_value("results_dir", tempfile.mkdtemp())
        config.set_value("language", "ru")

    def tearDown(self):
        config.set_value("language", "auto")

    def manager(self):
        manager = projects.ProjectManager()
        manager.attach(FakeAgent(), EventBus())
        return manager

    def test_chat_with_a_long_slicing_is_restored_with_the_user_message(self):
        manager = self.manager()
        manager.ensure_current()
        first = manager.current_id
        manager.bus.publish("user_message", {"text": "Шестерня под нагрузку"})
        flood(manager.bus)
        manager.bus.publish("assistant_message", {"text": "Готово"})
        manager.agent.history = [{"role": "user", "content": "Шестерня под нагрузку\n\nЯзык ответа: русский."},
                                 {"role": "assistant", "content": "Готово"}]
        manager.save_current()
        manager.create()
        manager.open(first)
        events = manager.bus.snapshot()
        users = [event["data"]["text"] for event in events if event["type"] == "user_message"]
        self.assertEqual(users, ["Шестерня под нагрузку"])
        self.assertEqual(len([e for e in events if e["type"] == "assistant_message"]), 1)

    def test_saved_projects_compact_progress_events(self):
        events = [{"id": i, "ts": 0, "type": "status", "data": {"text": str(i)}} for i in range(500)]
        events += [{"id": 1000 + i, "ts": 0, "type": "slice_progress", "data": {"percent": i}} for i in range(500)]
        events.append({"id": 5000, "ts": 0, "type": "user_message", "data": {"text": "x"}})
        compact = projects.compact_volatile(events)
        self.assertEqual(sorted(e["type"] for e in compact), ["slice_progress", "status", "user_message"])
        self.assertEqual([e["data"] for e in compact if e["type"] == "status"], [{"text": "499"}])

    def test_damaged_project_gets_its_messages_back_from_history(self):
        history = [{"role": "user", "content": "Пыльник шруса\nПервая строка\n\nВторой абзац\n\nПрикреплён файл: a.stl, путь: x\nЯзык ответа: русский."},
                   {"role": "assistant", "content": "Выбран материал"}]
        damaged = [{"id": 900 + i, "ts": 0, "type": "tool_call", "data": {"call_id": "c%d" % i}} for i in range(5)]
        healed = projects.heal_events(damaged, history, projects.service_prompts())
        self.assertEqual([e["type"] for e in healed[:2]], ["user_message", "assistant_message"])
        self.assertEqual(healed[0]["data"]["text"], "Пыльник шруса\nПервая строка\n\nВторой абзац")
        self.assertEqual(healed[2:], damaged)

    def test_healthy_project_is_left_alone(self):
        history = [{"role": "user", "content": "Привет\n\nЯзык ответа: русский."}]
        events = [{"id": 1, "ts": 0, "type": "user_message", "data": {"text": "Привет"}}]
        self.assertEqual(projects.heal_events(events, history, ()), events)

    def test_service_prompts_are_not_restored_as_messages(self):
        service = projects.service_prompts()[0]
        history = [{"role": "user", "content": service}]
        self.assertEqual(projects.heal_events([], history, projects.service_prompts()), [])

    def test_notes_are_stripped_only_when_they_are_notes(self):
        self.assertEqual(projects.strip_notes("Текст\n\nЯзык ответа: русский."), "Текст")
        self.assertEqual(projects.strip_notes("Абзац один\n\nАбзац два"), "Абзац один\n\nАбзац два")


if __name__ == "__main__":
    unittest.main()
