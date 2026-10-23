import unittest

import support
from AIAssistant import config
from AIAssistant.mcp import protocol
from AIAssistant.mcp.registry import ToolRegistry
from AIAssistant.server.events import EventBus


def make_registry():
    registry = ToolRegistry()
    registry.register("list_objects", "", {"type": "object", "properties": {}},
                      lambda a: {"objects": [{"name": "a.stl", "size_mm": {"x": 1.0, "y": 2.0, "z": 3.0}}]})
    registry.register("set_print_mode", "", {"type": "object", "properties": {}},
                      lambda a: {"key": "printing_mode", "old": "classic", "new": "cylindrical_full"})
    registry.register("set_settings", "", {"type": "object", "properties": {}}, lambda a: {
        "applied": [{"key": "infill_sparse_density", "label": "Infill", "scope": "extruder 0", "old": 20, "new": 40},
                    {"key": "support_enable", "label": "Support", "scope": "global", "old": True, "new": False}],
        "errors": []})
    registry.register("slice", "", {"type": "object", "properties": {}},
                      lambda a: {"print_time_s": 11520, "material_m": 14.63, "material_g": 46.2})
    registry.register("rotate_object", "", {"type": "object", "properties": {}}, lambda a: {"object_id": "obj1"})
    registry.register("recommend_setup", "", {"type": "object", "properties": {}}, lambda a: {
        "applied": True, "mode_label": "5D", "mode_reasons": ["a", "b"], "quality_type": "fast",
        "quality_reason": "q", "material": {"id": "generic_petg", "type": "PETG", "alternatives": ["PC"]},
        "settings": [{"key": "wall_line_count", "value": 4, "reason": "r"}], "orientation": "o"})
    return registry


class DerivedEventsTest(unittest.TestCase):
    def setUp(self):
        config.set_value("language", "ru")
        self.bus = EventBus()
        self.registry = make_registry()

    def call(self, name):
        protocol.call_tool(name, {}, self.registry, self.bus)
        return self.bus.get_since(0)["events"]

    def of_type(self, events, kind):
        return [e["data"] for e in events if e["type"] == kind]

    def test_print_mode(self):
        data = self.of_type(self.call("set_print_mode"), "setting_changed")[0]
        self.assertEqual(data["key"], "print_mode")
        self.assertEqual(data["raw"], "cylindrical_full")
        self.assertEqual(data["value"], "5D")
        self.assertEqual(data["old"], "3D")

    def test_settings_are_formatted(self):
        changes = self.of_type(self.call("set_settings"), "setting_changed")
        self.assertEqual(changes[0]["value"], "40 %")
        self.assertEqual(changes[0]["old"], "20 %")
        self.assertEqual(changes[1]["value"], "нет")
        self.assertEqual(changes[1]["old"], "да")

    def test_slice_result(self):
        data = self.of_type(self.call("slice"), "slice_result")[0]
        self.assertEqual(data["time"], "3 ч 12 мин")
        self.assertEqual(data["length"], "14.6 м")
        self.assertEqual(data["weight"], "46 г")

    def test_scene_after_scene_tool(self):
        data = self.of_type(self.call("rotate_object"), "scene")[0]
        self.assertEqual(data["objects"], [{"name": "a.stl", "size": [1.0, 2.0, 3.0]}])

    def test_decision_rows(self):
        events = self.call("recommend_setup")
        rows = self.of_type(events, "decision")[0]["rows"]
        self.assertEqual(rows[0][:2], ["Режим", "5D"])
        self.assertEqual(rows[1][1], "generic_petg (PETG)")
        self.assertEqual(rows[3][0], "wall_line_count")
        self.assertEqual(len(self.of_type(events, "scene")), 1)

    def test_failed_tool_has_no_derived_events(self):
        registry = ToolRegistry()
        registry.register("set_material", "", {"type": "object", "properties": {}}, lambda a: 1 / 0)
        protocol.call_tool("set_material", {}, registry, self.bus)
        types = [e["type"] for e in self.bus.get_since(0)["events"]]
        self.assertEqual(types, ["tool_call", "tool_result"])


if __name__ == "__main__":
    unittest.main()
