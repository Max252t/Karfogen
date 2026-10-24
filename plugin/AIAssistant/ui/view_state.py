import json
import re
from collections import OrderedDict

from . import strings

MODE_LABELS = OrderedDict([("classic", "3D"), ("cylindrical", "5D Spiral"), ("cylindrical_full", "5D")])
FORCED_MODES = tuple(MODE_LABELS.keys())
MAX_DETAILS = 6000

TOOL_GROUPS = {
    "load_model": "tool_load_model",
    "analyze_mesh": "tool_geometry",
    "get_object_bounds": "tool_geometry",
    "list_objects": "tool_geometry",
    "list_materials": "tool_material",
    "set_material": "tool_material",
    "set_setting": "tool_settings",
    "set_settings": "tool_settings",
    "get_setting": "tool_read_settings",
    "search_settings": "tool_read_settings",
    "get_changed_settings": "tool_read_settings",
    "reset_settings": "tool_reset",
    "create_profile": "tool_settings",
    "list_quality_profiles": "tool_quality",
    "set_quality_profile": "tool_quality",
    "get_print_mode": "tool_mode",
    "set_print_mode": "tool_mode",
    "select_machine": "tool_machine",
    "get_machine": "tool_machine",
    "suggest_orientation": "tool_orientation",
    "set_orientation": "tool_orientation",
    "lay_flat": "tool_orientation",
    "align_symmetry_axis": "tool_orientation",
    "rotate_object": "tool_orientation",
    "move_object": "tool_placement",
    "scale_object": "tool_placement",
    "arrange_all": "tool_placement",
    "delete_object": "tool_remove",
    "clear_scene": "tool_remove",
    "recommend_setup": "tool_recommend",
    "slice": "tool_slice",
    "get_slice_status": "tool_slice",
    "get_slice_result": "tool_slice",
    "export_gcode": "tool_export",
    "save_project_3mf": "tool_export",
}

TOOL_ICONS = {
    "tool_load_model": "load",
    "tool_geometry": "scale",
    "tool_material": "printer-3d-nozzle",
    "tool_settings": "settings",
    "tool_read_settings": "settings",
    "tool_quality": "layers-outline",
    "tool_mode": "view_3d",
    "tool_reset": "reset",
    "tool_machine": "printer-3d",
    "tool_orientation": "rotate",
    "tool_placement": "translate",
    "tool_remove": "cross1",
    "tool_recommend": "star",
    "tool_slice": "layers-outline",
    "tool_export": "check-outline",
}

MUTATING_TOOLS = set([
    "load_model", "set_material", "set_setting", "set_settings", "reset_settings", "set_quality_profile",
    "set_print_mode", "select_machine", "set_orientation", "lay_flat", "align_symmetry_axis", "rotate_object",
    "move_object", "scale_object", "arrange_all", "delete_object", "clear_scene", "slice",
])

ERROR_ACTIONS = {
    "not_configured": ["settings"],
    "auth": ["settings", "retry"],
    "not_found": ["settings", "retry"],
    "rate_limit": ["retry"],
    "network": ["retry", "settings"],
    "timeout": ["retry"],
    "server": ["retry"],
    "ssl": ["settings", "retry"],
    "bad_request": ["retry", "settings"],
    "image": ["no_image", "pick_file"],
    "step_limit": ["continue"],
    "internal": ["retry"],
}

IMAGE_HINTS = ("image", "vision", "multimodal", "изображ", "image_url")


def mode_label(mode):
    return MODE_LABELS.get(mode, mode or "")


def normalize_mode(mode):
    return mode if mode in FORCED_MODES else None


def classify_error(data):
    code = data.get("code") or ""
    message = str(data.get("message") or "")
    lowered = message.lower()
    if "certificate" in lowered or "ssl" in lowered:
        return "ssl"
    if code == "bad_request" and any(hint in lowered for hint in IMAGE_HINTS):
        return "image"
    if code in ERROR_ACTIONS:
        return code
    if "не задан" in lowered or "not set" in lowered:
        return "not_configured"
    if "лимит шагов" in lowered:
        return "step_limit"
    if "http 401" in lowered or "http 403" in lowered:
        return "auth"
    if "http 404" in lowered:
        return "not_found"
    if "http 429" in lowered:
        return "rate_limit"
    if "недоступна" in lowered:
        return "network"
    if "не ответила" in lowered:
        return "timeout"
    return "internal"


def escape(text):
    return (str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def markdown_to_styled(text):
    lines = []
    for raw in str(text or "").replace("\r\n", "\n").split("\n"):
        line = escape(raw)
        line = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", line)
        line = re.sub(r"`([^`]+)`", r"<i>\1</i>", line)
        heading = re.match(r"^#{1,6}\s+(.*)$", line)
        if heading:
            line = "<b>%s</b>" % heading.group(1)
        bullet = re.match(r"^(\s*)[-*•]\s+(.*)$", line)
        if bullet:
            line = "%s• %s" % ("&nbsp;" * (2 * len(bullet.group(1)) + 2), bullet.group(2))
        lines.append(line)
    return "<br>".join(lines)


def plain_to_styled(text):
    return "<br>".join(escape(line) for line in str(text or "").replace("\r\n", "\n").split("\n"))


def _dump(value):
    if isinstance(value, str):
        text = value
    else:
        try:
            text = json.dumps(value, ensure_ascii=False, indent=2, default=str)
        except (TypeError, ValueError):
            text = str(value)
    if len(text) > MAX_DETAILS:
        text = text[:MAX_DETAILS] + "\n…"
    return text


def format_size(language, size):
    size = int(size or 0)
    if size < 1024:
        return strings.text(language, "size_b", size)
    if size < 1024 * 1024:
        return strings.text(language, "size_kb", size // 1024)
    return strings.text(language, "size_mb", size / (1024.0 * 1024.0))


def format_dims(size):
    if isinstance(size, dict):
        values = [size.get("x"), size.get("y"), size.get("z")]
    else:
        values = list(size or [])
    try:
        return " × ".join("%.1f" % float(v) for v in values[:3])
    except (TypeError, ValueError):
        return ""


def tool_group(name):
    return TOOL_GROUPS.get(name)


def tool_title(language, name):
    group = tool_group(name)
    if group is None:
        return strings.text(language, "tool_other", name)
    return strings.text(language, group)


def tool_summary(language, name, result):
    t = lambda key, *args: strings.text(language, key, *args)
    if not isinstance(result, dict):
        return t("tool_ok")
    if name == "load_model":
        loaded = result.get("loaded") or []
        if loaded:
            first = loaded[0]
            dims = format_dims(first.get("size_mm"))
            text = t("sum_loaded", first.get("name", ""))
            return text + ("; " + t("sum_size", dims) if dims else "")
    if name in ("analyze_mesh", "get_object_bounds"):
        dims = format_dims(result.get("size_mm"))
        if dims:
            return t("sum_size", dims)
    if name in ("list_objects", "arrange_all"):
        return t("sum_objects", len(result.get("objects") or []))
    if name == "set_settings":
        return t("sum_changed", len(result.get("applied") or []))
    if name == "set_setting":
        return t("sum_changed", len(result.get("changes") or []) or 1)
    if name == "set_material":
        return t("sum_material", result.get("name") or result.get("new") or "")
    if name == "set_quality_profile":
        return t("sum_quality", result.get("name") or result.get("new") or "")
    if name == "set_print_mode":
        return t("sum_mode", mode_label(result.get("new")))
    if name == "reset_settings":
        return t("sum_reset")
    if name == "recommend_setup":
        material = (result.get("material") or {}).get("id", "")
        key = "sum_recommend" if result.get("applied") else "sum_recommend_preview"
        return t(key, result.get("mode_label") or mode_label(result.get("mode")), material)
    if name in ("slice", "get_slice_result"):
        return t("sum_sliced", result.get("print_time", ""), "%s g" % result.get("material_g", 0))
    if name in ("export_gcode", "save_project_3mf"):
        return t("sum_saved", result.get("path", ""))
    if name in ("delete_object", "clear_scene"):
        return t("sum_removed", result.get("removed", ""))
    return t("tool_ok")


def _empty_slice():
    return {"state": "idle", "progress": 0.0, "time": "", "length": "", "weight": ""}


class ChatViewState(object):
    def __init__(self, language="ru"):
        self.language = language
        self.reset()

    def t(self, key, *args):
        return strings.text(self.language, key, *args)

    def reset(self):
        self.items = []
        self._tool_index = {}
        self._tool_args = {}
        self.changes = OrderedDict()
        self.decisions = []
        self.slice = _empty_slice()
        self.exports = {}
        self.running = False
        self.task_state = "idle"
        self.status = ""
        self.status_tool = ""
        self.last_error = None
        self.setup = {"mode": "", "material": "", "quality": ""}
        self.tool_count = 0
        self._turn_changed = False
        self._next_id = 0
        self.ops = []

    def rebuild(self, events):
        self.reset()
        for event in events:
            self.apply(event)
        self.ops = [("reset",)]
        return self.ops

    def take_ops(self):
        ops = self.ops
        self.ops = []
        return ops

    def _append(self, item):
        self._next_id += 1
        base = {"uid": "i%d" % self._next_id, "kind": "", "text": "", "title": "", "summary": "", "status": "",
                "details": "", "meta": "", "actions": "", "icon": "", "impact": ""}
        base.update(item)
        self.items.append(base)
        self.ops.append(("append", len(self.items) - 1))
        return len(self.items) - 1

    def _update(self, index, **fields):
        self.items[index].update(fields)
        self.ops.append(("update", index))

    def apply(self, event):
        handler = getattr(self, "_on_" + str(event.get("type")), None)
        if handler is not None:
            handler(event.get("data") or {})

    def _on_user_message(self, data):
        self.running = True
        self.task_state = "running"
        self.status = "thinking"
        self.status_tool = ""
        self.last_error = None
        self._turn_changed = False
        meta = []
        for item in data.get("files") or []:
            meta.append("%s|%s" % (item.get("kind", "model"), item.get("name", "")))
        for name in data.get("scene") or []:
            meta.append("scene|%s" % name)
        mode = data.get("forced_mode")
        self._append({"kind": "user", "text": plain_to_styled(data.get("text", "")),
                      "meta": "\n".join(meta), "summary": mode_label(mode) if mode else ""})

    def _on_assistant_message(self, data):
        code = data.get("code")
        if code == "cancelled":
            self._append({"kind": "notice", "text": self.t("notice_cancelled"), "actions": "continue"})
            return
        if code == "images_dropped":
            self._append({"kind": "notice", "text": self.t("notice_images_dropped")})
            return
        text = data.get("text") or ""
        if not text.strip():
            return
        self._append({"kind": "assistant", "text": markdown_to_styled(text),
                      "summary": "intermediate" if data.get("intermediate") else "final"})

    def _on_status(self, data):
        text = data.get("text") or ""
        if text == "slice_state":
            state = data.get("state")
            if state in ("not_started", "disabled"):
                self.slice = _empty_slice()
            elif state == "error":
                self.slice["state"] = "error"
            elif state == "processing":
                self.slice = _empty_slice()
                self.slice["state"] = "slicing"
            return
        if text == "slicing":
            return
        if text.startswith("Выполняю инструмент:"):
            self.status = "tool"
            self.status_tool = text.split(":", 1)[1].strip()
        elif text == "Жду ответ LLM":
            self.status = "thinking"
        elif text == "Останавливаю":
            self.status = "stopping"

    def _on_tool_call(self, data):
        name = data.get("name", "")
        call_id = data.get("call_id")
        self.tool_count += 1
        self.status = "tool"
        self.status_tool = name
        group = tool_group(name) or ""
        index = self._append({"kind": "tool", "title": tool_title(self.language, name), "status": "running",
                              "summary": self.t("tool_running"), "icon": TOOL_ICONS.get(group, "settings"),
                              "meta": name,
                              "details": "%s\n%s" % (self.t("arguments"), _dump(data.get("arguments") or {}))})
        self._tool_index[call_id] = index
        self._tool_args[call_id] = data.get("arguments") or {}
        if name == "slice":
            self.slice = _empty_slice()
            self.slice["state"] = "slicing"

    def _on_tool_result(self, data):
        call_id = data.get("call_id")
        name = data.get("name", "")
        ok = data.get("ok", True)
        index = self._tool_index.get(call_id)
        if index is None:
            index = self._append({"kind": "tool", "title": tool_title(self.language, name), "meta": name,
                                  "icon": TOOL_ICONS.get(tool_group(name) or "", "settings")})
        args_text = "%s\n%s" % (self.t("arguments"), _dump(self._tool_args.get(call_id, {})))
        if ok:
            result = data.get("result")
            details = "%s\n\n%s\n%s" % (args_text, self.t("result"), _dump(result))
            self._update(index, status="ok", summary=tool_summary(self.language, name, result), details=details)
            if name in MUTATING_TOOLS or (name == "recommend_setup" and isinstance(result, dict) and result.get("applied")):
                self._turn_changed = True
            self._absorb_result(name, result)
        else:
            error = str(data.get("error") or "")
            details = "%s\n\n%s\n%s" % (args_text, self.t("result"), _dump(error))
            actions = "pick_file" if name == "load_model" else ""
            self._update(index, status="error", summary=error.split("\n")[0][:300], details=details,
                         impact=self.t("tool_error_hint"), actions=actions)
            if name == "slice":
                self.slice["state"] = "error"
        if self.running:
            self.status = "thinking"

    def _absorb_result(self, name, result):
        if not isinstance(result, dict):
            return
        if name in ("export_gcode", "save_project_3mf") and result.get("path"):
            self.exports["gcode" if name == "export_gcode" else "3mf"] = result["path"]
        if name == "slice":
            self.slice["state"] = "done"
            self.slice["progress"] = 1.0
        if name == "set_material":
            self.setup["material"] = result.get("name") or result.get("new") or ""
        if name == "set_quality_profile":
            self.setup["quality"] = result.get("name") or result.get("new") or ""
        if name == "set_print_mode":
            self.setup["mode"] = mode_label(result.get("new"))
        if name == "reset_settings":
            self.changes.clear()
            self.setup = {"mode": self.setup.get("mode", ""), "material": "", "quality": ""}

    def _on_setting_changed(self, data):
        key = data.get("key") or ""
        if not key:
            return
        previous = self.changes.get(key)
        old = previous["old"] if previous else data.get("old")
        self.changes[key] = {"key": key, "label": str(data.get("label") or key),
                             "old": "" if old is None else str(old),
                             "value": "" if data.get("value") is None else str(data.get("value"))}
        if key == "print_mode":
            self.setup["mode"] = str(data.get("value") or "")
        elif key == "material":
            self.setup["material"] = str(data.get("value") or "")
        elif key == "quality":
            self.setup["quality"] = str(data.get("value") or "")

    def _on_slice_progress(self, data):
        self.slice["state"] = "slicing"
        try:
            self.slice["progress"] = max(0.0, min(1.0, float(data.get("progress") or 0)))
        except (TypeError, ValueError):
            pass

    def _on_slice_result(self, data):
        self.slice.update({"state": "done", "progress": 1.0, "time": str(data.get("time") or ""),
                           "length": str(data.get("length") or ""), "weight": str(data.get("weight") or "")})

    def _on_decision(self, data):
        rows = []
        for row in data.get("rows") or []:
            row = list(row) + ["", "", ""]
            rows.append({"label": str(row[0]), "value": str(row[1]), "reason": str(row[2])})
        self.decisions = rows
        lines = ["<b>%s</b>: %s" % (escape(r["label"]), escape(r["value"])) for r in rows]
        self._append({"kind": "decision", "title": str(data.get("title") or self.t("res_decisions")),
                      "text": "<br>".join(lines)})

    def _on_error(self, data):
        code = classify_error(data)
        self.task_state = "error"
        self.last_error = code
        impact = self.t("impact_changed") if self._turn_changed else self.t("impact_none")
        actions = list(ERROR_ACTIONS.get(code, ["retry"]))
        if self._turn_changed and code != "not_configured" and "continue" not in actions:
            actions.append("continue")
        self._append({"kind": "error", "title": self.t("err_title_" + code), "text": self.t("err_text_" + code),
                      "impact": impact, "details": str(data.get("message") or ""), "actions": ",".join(actions),
                      "meta": code})

    def _on_done(self, data):
        self.running = False
        self.status = ""
        self.status_tool = ""
        if self.task_state == "running":
            self.task_state = "done"

    def add_local_error(self, title_key, message, actions=""):
        self._append({"kind": "error", "title": self.t(title_key), "text": plain_to_styled(message),
                      "actions": actions, "meta": "local"})

    def changes_list(self):
        return list(self.changes.values())

    def status_text(self, slicing_progress=None):
        if self.status == "stopping":
            return self.t("run_stopping")
        if self.slice["state"] == "slicing" and self.running:
            return self.t("run_slicing", int(round(self.slice["progress"] * 100)))
        if self.status == "tool" and self.status_tool:
            return self.t("run_tool", tool_title(self.language, self.status_tool))
        if self.status == "thinking":
            return self.t("run_thinking")
        return self.t("run_working")


def scene_note(objects):
    notes = []
    for obj in objects:
        notes.append("Модель уже в сцене: %s (object_id=%s, габариты %s мм). Не загружай её повторно, работай с этим object_id."
                     % (obj.get("name", ""), obj.get("id", ""), format_dims(obj.get("size"))))
    return notes
