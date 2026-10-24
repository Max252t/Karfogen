import tempfile

import support
from AIAssistant import config
from AIAssistant.server import projects
from AIAssistant.server.events import EventBus


class FakeAgent(object):
    def __init__(self):
        self.running = False
        self.history = []
        self.submitted = []
        self.cancelled = 0
        self.on_finished = None
        self.on_progress = None
        self.accept = True

    def is_running(self):
        return self.running

    def submit(self, text, attachment_ids=None, model_name=None, forced_mode=None, notes=None, display=None):
        if self.running or not self.accept:
            return False, "busy"
        self.submitted.append({"text": text, "ids": list(attachment_ids or []), "mode": forced_mode,
                               "notes": list(notes or []), "display": dict(display or {})})
        self.history.append({"role": "user", "content": text})
        self.running = True
        return True, "ok"

    def cancel(self):
        if not self.running:
            return False
        self.cancelled += 1
        return True

    def get_history(self):
        return list(self.history)

    def set_history(self, history):
        self.history = list(history)


class FakeRegistry(object):
    def __init__(self, objects=None):
        self.objects = list(objects or [])
        self.calls = []

    def has(self, name):
        return name in ("list_objects", "get_changed_settings", "reset_settings", "export_gcode", "save_project_3mf")

    def call(self, name, args):
        self.calls.append(name)
        if name == "list_objects":
            return {"objects": self.objects}
        if name == "get_changed_settings":
            return {"changes": [{"key": "wall_line_count"}, {"key": "infill_sparse_density"}]}
        if name == "reset_settings":
            return {"ok": True}
        if name == "export_gcode":
            return {"path": config.get_results_dir() + "/bracket/result.gcode", "bytes": 10, "model_name": "bracket"}
        if name == "save_project_3mf":
            return {"path": config.get_results_dir() + "/bracket/project.3mf", "bytes": 10, "model_name": "bracket"}
        raise KeyError(name)


def scene_object(object_id, name, x, y, z):
    return {"object_id": object_id, "name": name, "size_mm": {"x": x, "y": y, "z": z}}


def fresh_environment(configured=True, objects=None):
    from AIAssistant.ui.controller import NativeChatController
    config.set_value("results_dir", tempfile.mkdtemp())
    config.set_value("language", "ru")
    config.set_value("window_geometry", "")
    config.set_value("base_url", "https://llm.example/v1" if configured else "")
    config.set_value("model", "demo-model" if configured else "")
    config.set_value("api_key", "test-key-value" if configured else "")
    agent = FakeAgent()
    bus = EventBus()
    registry = FakeRegistry(objects)
    manager = projects.ProjectManager()
    manager.attach(agent, bus)
    controller = NativeChatController(agent=agent, bus=bus, registry=registry, manager=manager, start_timer=False)
    return controller, agent, bus, registry, manager


CONVERSATION = [
    ("user_message", {"text": "Кронштейн под нагрузку, PETG, без поддержек",
                      "files": [{"name": "bracket.stl", "kind": "model"}, {"name": "photo.jpg", "kind": "image"}]}),
    ("status", {"text": "Жду ответ LLM"}),
    ("assistant_message", {"text": "Загружаю модель и анализирую геометрию.", "intermediate": True}),
    ("tool_call", {"call_id": "c1", "name": "load_model", "arguments": {"path": "C:/models/bracket.stl"}}),
    ("tool_result", {"call_id": "c1", "name": "load_model", "ok": True,
                     "result": {"loaded": [{"object_id": "obj1", "name": "bracket.stl",
                                            "size_mm": {"x": 62, "y": 40, "z": 35}}]}}),
    ("tool_call", {"call_id": "c2", "name": "analyze_mesh", "arguments": {"object_id": "obj1"}}),
    ("tool_result", {"call_id": "c2", "name": "analyze_mesh", "ok": True,
                     "result": {"size_mm": [62, 40, 35], "volume_cm3": 21.4}}),
    ("tool_call", {"call_id": "c3", "name": "set_material", "arguments": {"material_id": "generic_petg"}}),
    ("tool_result", {"call_id": "c3", "name": "set_material", "ok": True,
                     "result": {"old": "generic_pla", "new": "generic_petg", "name": "Generic PETG"}}),
    ("setting_changed", {"key": "material", "label": "материал", "old": "generic_pla", "value": "Generic PETG"}),
    ("tool_call", {"call_id": "c4", "name": "set_settings", "arguments": {"changes": [{"key": "wall_line_count", "value": 4}]}}),
    ("tool_result", {"call_id": "c4", "name": "set_settings", "ok": False,
                     "error": "Setting 'wall_count' not found. Use search_settings."}),
    ("tool_call", {"call_id": "c5", "name": "set_settings", "arguments": {"changes": [{"key": "wall_line_count", "value": 4}]}}),
    ("tool_result", {"call_id": "c5", "name": "set_settings", "ok": True,
                     "result": {"applied": [{"key": "wall_line_count"}, {"key": "infill_sparse_density"}]}}),
    ("setting_changed", {"key": "wall_line_count", "label": "Количество линий стенки", "old": 2, "value": 4}),
    ("setting_changed", {"key": "infill_sparse_density", "label": "Плотность заполнения", "old": "20 %", "value": "40 %"}),
    ("decision", {"title": "Принятые решения", "rows": [["Режим", "3D", "деталь не тело вращения"],
                                                         ["Материал", "generic_petg (PETG)", "нагрузка и влага"],
                                                         ["Профиль качества", "normal", "баланс прочности и времени"]]}),
    ("tool_call", {"call_id": "c6", "name": "slice", "arguments": {}}),
    ("slice_progress", {"state": "slicing", "progress": 0.45}),
]

FINISH = [
    ("tool_result", {"call_id": "c6", "name": "slice", "ok": True,
                     "result": {"print_time_s": 8040, "print_time": "2h 14m", "material_g": 46.0, "material_m": 14.6}}),
    ("slice_result", {"time": "2 ч 14 мин", "length": "14.6 м", "weight": "46 г", "layers": "-"}),
    ("tool_call", {"call_id": "c7", "name": "export_gcode", "arguments": {"model_name": "bracket"}}),
    ("tool_result", {"call_id": "c7", "name": "export_gcode", "ok": True,
                     "result": {"path": "C:/Users/demo/AIAssistantResults/bracket/result.gcode"}}),
    ("assistant_message", {"text": "**Готово.** Режим 3D, материал PETG, профиль normal.\n\n- 4 стенки и 40 % заполнения для прочности\n- Поддержки не нужны: нависания 8 %\n\nВремя печати 2 ч 14 мин, расход 46 г."}),
    ("done", {}),
]


def publish(bus, events):
    for kind, data in events:
        bus.publish(kind, data)
