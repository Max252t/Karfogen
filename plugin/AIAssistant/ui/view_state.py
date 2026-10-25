import json
import os
import re
from collections import OrderedDict

from . import markdown, progress, strings

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


def tool_running_title(language, name):
    group = tool_group(name)
    if group is None:
        return strings.text(language, "tool_other", name)
    return strings.text(language, "run_" + group)


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


LIVE_STATES = {"done": "done", "processing": "slicing", "error": "error"}


def live_slice(language, snapshot):
    from ..server.derived_events import TEXTS
    if not snapshot:
        return None
    texts = TEXTS.get(language, TEXTS["en"])
    view = _empty_slice()
    view["state"] = LIVE_STATES.get(snapshot.get("state"), "idle")
    try:
        view["progress"] = 1.0 if view["state"] == "done" else max(0.0, min(1.0, float(snapshot.get("progress") or 0)))
    except (TypeError, ValueError):
        pass
    if view["state"] == "done":
        seconds = int(snapshot.get("print_time_s") or 0)
        view["time"] = texts["time"] % (seconds // 3600, (seconds % 3600) // 60) if seconds else ""
        view["length"] = texts["m"] % float(snapshot.get("material_m") or 0)
        view["weight"] = texts["g"] % float(snapshot.get("material_g") or 0)
    return view


STAGE_GROUPS = {
    "get_changed_settings": "context",
    "get_setting": "context",
    "search_settings": "context",
    "get_print_mode": "context",
    "get_machine": "context",
    "list_materials": "context",
    "list_quality_profiles": "context",
    "list_objects": "context",
    "load_model": "model",
    "analyze_mesh": "geometry",
    "get_object_bounds": "geometry",
    "recommend_setup": "recommend",
    "set_material": "recommend",
    "set_quality_profile": "recommend",
    "set_print_mode": "recommend",
    "select_machine": "recommend",
    "set_setting": "settings",
    "set_settings": "settings",
    "create_profile": "settings",
    "reset_settings": "reset",
    "suggest_orientation": "placement",
    "set_orientation": "placement",
    "lay_flat": "placement",
    "align_symmetry_axis": "placement",
    "rotate_object": "placement",
    "move_object": "placement",
    "scale_object": "placement",
    "arrange_all": "placement",
    "slice": "slicing",
    "get_slice_status": "slicing",
    "get_slice_result": "slicing",
    "export_gcode": "export",
    "save_project_3mf": "export",
    "delete_object": "scene",
    "clear_scene": "scene",
}

DECISION_FIELDS = {"режим": "mode", "mode": "mode", "материал": "material", "material": "material",
                   "профиль качества": "quality", "quality profile": "quality"}
SERVICE_TOOLS = set(name for name, group in STAGE_GROUPS.items() if group == "context")
NUMBER = re.compile(r"(?<![\w.])-?\d+\.\d+(?![\w.])")


def stage_group(name):
    return STAGE_GROUPS.get(name, "other")


def format_dims_view(language, size):
    if isinstance(size, dict):
        values = [size.get("x"), size.get("y"), size.get("z")]
    else:
        values = list(size or [])
    try:
        return " × ".join(format_number(language, float(v)) for v in values[:3])
    except (TypeError, ValueError):
        return ""


def format_number(language, value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    text = ("%.3f" % number).rstrip("0").rstrip(".") if abs(number - round(number)) > 1e-9 else "%d" % round(number)
    return text.replace(".", ",") if language == "ru" else text


def format_value(language, value):
    if value is None:
        return ""
    if isinstance(value, bool):
        return strings.text(language, "value_on" if value else "value_off")
    if isinstance(value, float):
        return format_number(language, value)
    text = str(value).strip()
    if text.lower() in ("true", "false"):
        return strings.text(language, "value_on" if text.lower() == "true" else "value_off")
    return NUMBER.sub(lambda m: format_number(language, m.group(0)), text)


class Turn(object):
    def __init__(self, index, manual=False):
        self.index = index
        self.manual = manual
        self.progress = progress.ProgressTracker()
        self.progress.start()
        self.stages = []
        self.pending = []
        self.calls = {}
        self.changes = OrderedDict()
        self.decisions = []
        self.metrics = {}
        self.exports = OrderedDict()
        self.setup = {"mode": "", "material": "", "quality": ""}
        self.state = "running"
        self.answered = False
        self.sliced = False
        self.percent = -1


class ChatViewState(object):
    def __init__(self, language="ru"):
        self.language = language
        self.reset()

    def t(self, key, *args):
        return strings.text(self.language, key, *args)

    def reset(self):
        self.items = []
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
        self.turn = None
        self.last_turn = None
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
        ops = []
        seen = set()
        for op in self.ops:
            if op[0] == "update" and op in seen:
                continue
            seen.add(op)
            ops.append(op)
        self.ops = []
        return ops

    def _append(self, item):
        self._next_id += 1
        base = {"uid": "i%d" % self._next_id, "kind": "", "text": "", "title": "", "summary": "", "status": "",
                "details": "", "meta": "", "actions": "", "icon": "", "impact": "", "phase": "", "progress": 0.0,
                "percent": 0, "indeterminate": False, "stageKey": "", "stages": [], "metrics": [], "changes": [],
                "decisions": [], "exports": [], "blocks": [], "collapsible": False, "plain": "", "stageCount": "",
                "serious": False}
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

    def _start_turn(self, manual=False):
        index = self._append({"kind": "activity", "phase": "running", "indeterminate": True,
                              "title": self.t("prog_estimating")})
        self.turn = Turn(index, manual)
        self.last_turn = self.turn
        return self.turn

    def _ensure_turn(self):
        return self.turn if self.turn is not None else self._start_turn(manual=True)

    def _on_user_message(self, data):
        if self.turn is not None:
            self._finish_turn(self.turn)
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
        self._append({"kind": "user", "text": plain_to_styled(data.get("text", "")), "plain": str(data.get("text", "")),
                      "meta": "\n".join(meta), "summary": mode_label(mode) if mode else ""})
        self._start_turn()

    def _on_assistant_message(self, data):
        code = data.get("code")
        turn = self.turn
        if code == "cancelled":
            if turn is not None:
                turn.progress.cancel()
                turn.state = "cancelled"
                self._refresh(turn)
            else:
                self._append({"kind": "notice", "text": self.t("notice_cancelled"), "actions": "continue"})
            return
        if code == "images_dropped":
            self._append({"kind": "notice", "text": self.t("notice_images_dropped")})
            return
        text = data.get("text") or ""
        if not text.strip():
            return
        if data.get("intermediate") and turn is not None:
            self._note(turn, text)
            return
        if turn is not None:
            turn.answered = True
            turn.progress.answer()
            self._refresh(turn)
        self._append({"kind": "assistant", "text": markdown_to_styled(text), "plain": text,
                      "blocks": markdown.parse_blocks(text), "collapsible": markdown.should_collapse(text),
                      "summary": "intermediate" if data.get("intermediate") else "final"})

    def _note(self, turn, text):
        entry = {"call_id": None, "name": "", "note": text.strip(), "ok": True, "service": True}
        if turn.stages:
            turn.stages[-1]["entries"].append(entry)
        else:
            turn.pending.append(entry)
        self._refresh(turn)

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
            if self.turn is not None and self.turn.state == "running":
                self.turn.state = "stopping"
                self._refresh(self.turn)

    def _stage_for(self, turn, group, service):
        if service:
            return turn.stages[-1] if turn.stages else None
        if turn.stages and turn.stages[-1]["group"] == group:
            return turn.stages[-1]
        stage = {"group": group, "entries": list(turn.pending), "changes": []}
        del turn.pending[:]
        turn.stages.append(stage)
        return stage

    def _on_tool_call(self, data):
        name = data.get("name", "")
        call_id = data.get("call_id")
        self.tool_count += 1
        self.status = "tool"
        self.status_tool = name
        turn = self._ensure_turn()
        service = name in SERVICE_TOOLS
        entry = {"call_id": call_id, "name": name, "ok": None, "service": service, "summary": "", "error": "",
                 "args": data.get("arguments") or {}, "result": None}
        stage = self._stage_for(turn, stage_group(name), service)
        if stage is None:
            turn.pending.append(entry)
        else:
            stage["entries"].append(entry)
        turn.calls[call_id] = entry
        turn.progress.tool_started(name)
        if name == "slice":
            self.slice = _empty_slice()
            self.slice["state"] = "slicing"
        self._refresh(turn)

    def _on_tool_result(self, data):
        call_id = data.get("call_id")
        name = data.get("name", "")
        ok = bool(data.get("ok", True))
        turn = self._ensure_turn()
        entry = turn.calls.get(call_id)
        if entry is None:
            self._on_tool_call({"call_id": call_id, "name": name, "arguments": {}})
            self.tool_count -= 1
            entry = turn.calls[call_id]
        entry["ok"] = ok
        if ok:
            result = data.get("result")
            entry["result"] = result
            entry["summary"] = tool_summary(self.language, name, result)
            if name in MUTATING_TOOLS or (name == "recommend_setup" and isinstance(result, dict) and result.get("applied")):
                self._turn_changed = True
            self._absorb_result(turn, name, result)
        else:
            entry["error"] = str(data.get("error") or "")
            if name == "slice":
                self.slice["state"] = "error"
        turn.progress.tool_finished(name, ok)
        if self.running:
            self.status = "thinking"
        if turn.manual:
            if ok:
                turn.progress.done()
            else:
                turn.progress.fail()
            turn.state = "done" if ok else "error"
            self._finish_turn(turn)
        else:
            self._refresh(turn)

    def _absorb_result(self, turn, name, result):
        if not isinstance(result, dict):
            return
        if name in ("export_gcode", "save_project_3mf") and result.get("path"):
            kind = "gcode" if name == "export_gcode" else "3mf"
            self.exports[kind] = result["path"]
            turn.exports[kind] = result["path"]
        if name == "slice":
            self.slice["state"] = "done"
            self.slice["progress"] = 1.0
            turn.sliced = True
        if name == "set_material":
            self.setup["material"] = turn.setup["material"] = result.get("name") or result.get("new") or ""
        if name == "set_quality_profile":
            self.setup["quality"] = turn.setup["quality"] = result.get("name") or result.get("new") or ""
        if name == "set_print_mode":
            self.setup["mode"] = turn.setup["mode"] = mode_label(result.get("new"))
        if name == "recommend_setup" and result.get("applied"):
            turn.setup["mode"] = turn.setup["mode"] or result.get("mode_label") or mode_label(result.get("mode"))
            turn.setup["material"] = turn.setup["material"] or (result.get("material") or {}).get("id", "")
            turn.setup["quality"] = turn.setup["quality"] or result.get("quality_type") or ""
        if name == "reset_settings":
            self.changes.clear()
            turn.changes.clear()
            self.setup = {"mode": self.setup.get("mode", ""), "material": "", "quality": ""}

    def _on_setting_changed(self, data):
        key = data.get("key") or ""
        if not key:
            return
        for table in [self.changes] + ([self.turn.changes] if self.turn is not None else []):
            previous = table.get(key)
            old = previous["old"] if previous else data.get("old")
            entry = {"key": key, "label": str(data.get("label") or key),
                     "old": "" if old is None else str(old),
                     "value": "" if data.get("value") is None else str(data.get("value"))}
            if entry["old"] != "" and entry["old"].strip().lower() == entry["value"].strip().lower():
                table.pop(key, None)
            else:
                table[key] = entry
        if key in ("print_mode", "material", "quality"):
            field = "mode" if key == "print_mode" else key
            self.setup[field] = str(data.get("value") or "")
            if self.turn is not None:
                self.turn.setup[field] = self.setup[field]
        if self.turn is not None:
            if self.turn.stages and key not in self.turn.stages[-1]["changes"]:
                self.turn.stages[-1]["changes"].append(key)
            self._refresh(self.turn)

    def _on_slice_progress(self, data):
        self.slice["state"] = "slicing"
        try:
            self.slice["progress"] = max(0.0, min(1.0, float(data.get("progress") or 0)))
        except (TypeError, ValueError):
            pass
        turn = self.turn
        if turn is not None and not turn.manual:
            turn.progress.slice_progress(self.slice["progress"])
            if turn.progress.percent != turn.percent:
                self._refresh(turn)

    def _on_slice_result(self, data):
        self.slice.update({"state": "done", "progress": 1.0, "time": str(data.get("time") or ""),
                           "length": str(data.get("length") or ""), "weight": str(data.get("weight") or "")})
        if self.turn is not None:
            self.turn.sliced = True
            self.turn.metrics = dict((key, format_value(self.language, self.slice[key]))
                                     for key in ("time", "length", "weight"))
            self._refresh(self.turn)

    def _on_decision(self, data):
        rows = []
        for row in data.get("rows") or []:
            row = list(row) + ["", "", ""]
            label = str(row[0])
            known = self.changes.get(label)
            rows.append({"label": known["label"] if known else label, "value": format_value(self.language, row[1]),
                         "reason": str(row[2])})
        self.decisions = rows
        turn = self.turn or self.last_turn
        if turn is not None:
            turn.decisions = rows
            for row in data.get("rows") or []:
                field = DECISION_FIELDS.get(str(list(row)[0]).strip().lower()) if row else None
                if field and not turn.setup[field] and len(row) > 1:
                    value = str(row[1])
                    turn.setup[field] = value.split(" (")[0] if field == "material" else value
            self._refresh(turn)

    def _on_error(self, data):
        code = classify_error(data)
        self.task_state = "error"
        self.last_error = code
        impact = self.t("impact_changed") if self._turn_changed else self.t("impact_none")
        actions = list(ERROR_ACTIONS.get(code, ["retry"]))
        if self._turn_changed and code != "not_configured" and "continue" not in actions:
            actions.append("continue")
        if self.turn is not None:
            self.turn.progress.fail()
            self.turn.state = "error"
            self._refresh(self.turn)
        self._append({"kind": "error", "title": self.t("err_title_" + code), "text": self.t("err_text_" + code),
                      "impact": impact, "details": str(data.get("message") or ""), "actions": ",".join(actions),
                      "meta": code})

    def _on_done(self, data):
        self.running = False
        self.status = ""
        self.status_tool = ""
        if self.task_state == "running":
            self.task_state = "done"
        if self.turn is not None:
            self._finish_turn(self.turn)

    def _finish_turn(self, turn, interrupted=False):
        if turn.state in ("running", "stopping"):
            if interrupted and not turn.answered:
                turn.progress.cancel()
                turn.state = "cancelled"
            else:
                turn.progress.done()
                turn.state = "done"
        if turn.pending:
            turn.stages.append({"group": "context", "entries": list(turn.pending), "changes": []})
            del turn.pending[:]
        if not turn.stages and not turn.decisions and turn.state in ("done", "error"):
            turn.state = "quiet"
        if self.turn is turn:
            self.turn = None
        self._refresh(turn)

    def finish_open_turn(self):
        if self.turn is not None:
            self.running = False
            if self.task_state == "running":
                self.task_state = "done"
            self._finish_turn(self.turn, interrupted=True)

    def add_local_error(self, title_key, message, actions=""):
        self._append({"kind": "error", "title": self.t(title_key), "text": plain_to_styled(message),
                      "actions": actions, "meta": "local"})

    def _change_view(self, entry):
        return {"key": entry["key"], "label": entry["label"], "old": format_value(self.language, entry["old"]),
                "value": format_value(self.language, entry["value"])}

    def changes_list(self):
        return [self._change_view(entry) for entry in self.changes.values()]

    def _stage_status(self, stage):
        entries = [e for e in stage["entries"] if e.get("call_id") is not None]
        if any(e["ok"] is None for e in entries):
            return "running", False
        primary = [e for e in entries if not e["service"]] or entries
        if not primary:
            return "ok", False
        failed = [e for e in primary if e["ok"] is False]
        if primary[-1]["ok"] is False:
            return "error", False
        return "ok", bool(failed)

    def _stage_summary(self, turn, stage, status):
        group = stage["group"]
        entries = [e for e in stage["entries"] if e.get("call_id") is not None]
        if status == "error":
            failed = [e for e in entries if e["ok"] is False]
            return failed[-1]["error"].split("\n")[0][:200] if failed else ""
        done = [e for e in entries if e["ok"] and not e["service"]]
        changed = [key for key in stage["changes"] if key in turn.changes]
        if group == "settings" and changed:
            return self.t("sum_changed", len(changed))
        if group == "recommend":
            parts = [turn.setup.get("mode"), turn.setup.get("material"), turn.setup.get("quality")]
            if any(parts):
                return " · ".join(p for p in parts if p)
        if group == "slicing" and turn.metrics:
            return " · ".join(v for v in (turn.metrics.get("time"), turn.metrics.get("weight")) if v and v != "-")
        if group == "model":
            loaded = [e["result"].get("loaded") or [] for e in done if isinstance(e["result"], dict)]
            names = [item.get("name", "") for chunk in loaded for item in chunk]
            if names:
                return ", ".join(names)
        if group == "geometry":
            for entry in reversed(done):
                dims = format_dims_view(self.language, (entry["result"] or {}).get("size_mm"))
                if dims:
                    return self.t("unit_mm", dims)
        if group == "export" and turn.exports:
            return ", ".join(os.path.basename(p) for p in turn.exports.values())
        if done and status == "ok":
            summary = done[-1]["summary"]
            return "" if summary == self.t("tool_ok") else summary
        return ""

    def _facts(self, turn, stage):
        facts = []
        t = self.t

        def add(label, value):
            if value not in (None, ""):
                facts.append({"label": label, "value": str(value)})

        for entry in stage["entries"]:
            result = entry.get("result")
            if not entry.get("ok") or not isinstance(result, dict):
                continue
            name = entry["name"]
            if name == "load_model":
                for item in result.get("loaded") or []:
                    add(t("fact_file"), item.get("name", ""))
                    dims = format_dims_view(self.language, item.get("size_mm"))
                    add(t("fact_size"), t("unit_mm", dims) if dims else "")
            elif name in ("analyze_mesh", "get_object_bounds"):
                dims = format_dims_view(self.language, result.get("size_mm"))
                add(t("fact_size"), t("unit_mm", dims) if dims else "")
                if result.get("volume_cm3") is not None:
                    add(t("fact_volume"), t("unit_cm3", format_number(self.language, result["volume_cm3"])))
                if result.get("surface_area_cm2") is not None:
                    add(t("fact_area"), t("unit_cm2", format_number(self.language, result["surface_area_cm2"])))
                if result.get("mean_wall_mm") is not None:
                    add(t("fact_wall"), t("unit_mm", format_number(self.language, result["mean_wall_mm"])))
                symmetry = result.get("axisymmetry")
                if isinstance(symmetry, dict) and symmetry.get("is_axisymmetric"):
                    add(t("fact_axis"), str(symmetry.get("axis") or "").upper())
                fit = result.get("fit") if isinstance(result.get("fit"), dict) else result
                if "fits" in fit:
                    add(t("fact_fits"), t("value_yes") if fit.get("fits") else t("value_no"))
        if stage["group"] == "recommend":
            add(t("fact_mode"), turn.setup.get("mode"))
            add(t("fact_material"), turn.setup.get("material"))
            add(t("fact_quality"), turn.setup.get("quality"))
        if stage["group"] == "settings":
            for key in stage["changes"]:
                change = turn.changes.get(key)
                if change:
                    view = self._change_view(change)
                    add(view["label"], ("%s → %s" % (view["old"], view["value"])) if view["old"] else view["value"])
        if stage["group"] == "slicing" and turn.metrics:
            add(t("fact_time"), turn.metrics.get("time"))
            add(t("fact_length"), turn.metrics.get("length"))
            add(t("fact_weight"), turn.metrics.get("weight"))
        if stage["group"] == "export":
            for kind, path in turn.exports.items():
                add(t("file_gcode") if kind == "gcode" else t("file_3mf"), path)
        return facts

    def _details(self, stage):
        parts = []
        for entry in stage["entries"]:
            if entry.get("note"):
                parts.append("%s\n%s" % (self.t("assistant_note"), entry["note"]))
                continue
            mark = "…" if entry["ok"] is None else ("✓" if entry["ok"] else "✗")
            text = "%s %s (%s)\n%s\n%s" % (mark, tool_title(self.language, entry["name"]), entry["name"],
                                           self.t("arguments"), _dump(entry["args"]))
            if entry["ok"] is not None:
                text += "\n%s\n%s" % (self.t("result"), _dump(entry["result"] if entry["ok"] else entry["error"]))
            parts.append(text)
        return "\n\n".join(parts)

    def _stage_view(self, turn, stage):
        status, fixed = self._stage_status(stage)
        suffix = {"running": "_run", "ok": "_done", "error": "_fail"}[status]
        return {"group": stage["group"], "status": status, "fixed": fixed,
                "title": self.t("grp_" + stage["group"] + suffix),
                "summary": self._stage_summary(turn, stage, status),
                "facts": self._facts(turn, stage), "details": self._details(stage)}

    def _activity_title(self, turn):
        if turn.state == "stopping":
            return self.t("work_stopping")
        if turn.state == "cancelled":
            return self.t("work_cancelled")
        if turn.state == "error":
            return self.t("work_error")
        if turn.state in ("done", "quiet"):
            return self.t("work_done_sliced" if turn.sliced else "work_done")
        stage = turn.progress.stage
        return self.t("stage_" + stage) if stage else self.t("prog_estimating")

    def _refresh(self, turn):
        stages = [self._stage_view(turn, stage) for stage in turn.stages]
        if turn.state in ("running", "stopping") and turn.pending and not stages:
            stages.append(self._stage_view(turn, {"group": "context", "entries": list(turn.pending), "changes": []}))
        setup = dict(turn.setup)
        if turn.sliced:
            for key in setup:
                setup[key] = setup[key] or self.setup.get(key, "")
        metrics = []
        for key, label in (("time", "metric_time"), ("length", "metric_length"), ("weight", "metric_weight")):
            value = turn.metrics.get(key)
            if value and value != "-":
                metrics.append({"value": value, "label": self.t(label)})
        exports = [{"kind": kind, "path": path, "name": os.path.basename(path),
                    "label": self.t("file_gcode") if kind == "gcode" else self.t("file_3mf")}
                   for kind, path in turn.exports.items()]
        snapshot = turn.progress.snapshot()
        turn.percent = snapshot["percent"]
        finished = len([s for s in stages if s["status"] != "running"])
        impact = self.t("work_kept", snapshot["percent"]) if turn.state in ("error", "cancelled") and stages else ""
        self._update(turn.index, phase=turn.state, title=self._activity_title(turn), progress=snapshot["value"],
                     percent=snapshot["percent"], indeterminate=snapshot["indeterminate"],
                     stageKey=snapshot["stage"], stages=stages, metrics=metrics,
                     changes=[self._change_view(c) for c in turn.changes.values()], decisions=list(turn.decisions),
                     exports=exports, summary=" · ".join(v for v in (setup["mode"], setup["material"], setup["quality"]) if v),
                     stageCount=strings.count(self.language, finished, "stages") if finished else "",
                     actions="continue" if turn.state == "cancelled" else "", impact=impact,
                     serious=any(s["status"] == "error" for s in stages[-1:]))

    def stage_history(self):
        for item in reversed(self.items):
            if item["kind"] == "activity" and item["stages"]:
                return [dict(s) for s in item["stages"]]
        return []

    def live_stage(self):
        turn = self.turn
        if turn is None or turn.state != "running":
            return None, False, False
        return turn.progress.stage, bool(self.items[turn.index]["serious"]), True

    def status_text(self, slicing_progress=None):
        if self.status == "stopping":
            return self.t("run_stopping")
        turn = self.turn
        if turn is not None and turn.progress.known:
            return "%s · %d %%" % (self._activity_title(turn), turn.progress.percent)
        if self.slice["state"] == "slicing" and self.running:
            return self.t("run_slicing", int(round(self.slice["progress"] * 100)))
        if self.status == "tool" and self.status_tool:
            return tool_running_title(self.language, self.status_tool) + "…"
        if self.status == "thinking":
            return self.t("run_thinking")
        return self.t("run_working")


def scene_note(objects):
    notes = []
    for obj in objects:
        notes.append("Модель уже в сцене: %s (object_id=%s, габариты %s мм). Не загружай её повторно, работай с этим object_id."
                     % (obj.get("name", ""), obj.get("id", ""), format_dims(obj.get("size"))))
    return notes
