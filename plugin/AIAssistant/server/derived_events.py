from ..agent import knowledge

SCENE_TOOLS = set([
    "load_model", "delete_object", "clear_scene", "rotate_object", "move_object", "scale_object",
    "set_orientation", "lay_flat", "align_symmetry_axis", "arrange_all", "suggest_orientation", "recommend_setup",
    "create_parametric_model", "update_parametric_model",
])

GENERATED_TOOLS = set(["create_parametric_model", "update_parametric_model", "validate_generated_model"])

MODE_LABELS = {"classic": "3D", "cylindrical": "5D Spiral", "cylindrical_full": "5D"}

TEXTS = {
    "ru": {"yes": "да", "no": "нет", "time": "%d ч %02d мин", "m": "%.1f м", "g": "%.0f г",
           "mode": "режим", "material": "материал", "quality": "профиль качества",
           "decisions": "Принятые решения", "row_mode": "Режим", "row_material": "Материал",
           "row_quality": "Профиль качества", "row_orientation": "Ориентация", "row_note": "Примечание", "alternatives": "альтернативы: %s"},
    "en": {"yes": "yes", "no": "no", "time": "%d h %02d min", "m": "%.1f m", "g": "%.0f g",
           "mode": "mode", "material": "material", "quality": "quality profile",
           "decisions": "Decisions made", "row_mode": "Mode", "row_material": "Material",
           "row_quality": "Quality profile", "row_orientation": "Orientation", "row_note": "Note", "alternatives": "alternatives: %s"},
}


def tr(key):
    from .. import config
    return TEXTS.get(config.effective_language(), TEXTS["en"])[key]


def format_value(key, value):
    if isinstance(value, bool):
        return tr("yes") if value else tr("no")
    if key == "infill_sparse_density" and isinstance(value, (int, float)):
        return "%g %%" % value
    if key == "print_mode":
        return MODE_LABELS.get(value, value)
    return value


def _setting_events(changes):
    events = []
    for change in changes:
        key = change["key"]
        events.append({"key": key, "label": change.get("label") or key,
                       "old": format_value(key, change.get("old")),
                       "value": format_value(key, change.get("new"))})
    return events


def _format_time(seconds):
    return tr("time") % (seconds // 3600, (seconds % 3600) // 60)


def _decision_rows(plan):
    rows = [[tr("row_mode"), plan["mode_label"], "; ".join(plan.get("mode_reasons") or [])]]
    material = plan["material"]
    material_note = tr("alternatives") % ", ".join(material.get("alternatives") or [])
    if material.get("properties"):
        material_note = knowledge.reason("mat_profile", ", ".join(material["properties"])) + "; " + material_note
    if material.get("reason"):
        material_note = material["reason"] + "; " + material_note
    if material.get("skipped"):
        material_note += "; " + knowledge.reason("mat_unavailable", ", ".join(material["skipped"]))
    rows.append([tr("row_material"), "%s (%s)" % (material["id"], material["type"]), material_note])
    rows.append([tr("row_quality"), plan["quality_type"], plan.get("quality_reason") or ""])
    for item in plan.get("settings") or []:
        rows.append([item["key"], str(format_value(item["key"], item["value"])), item.get("reason") or ""])
    rows.append([tr("row_orientation"), plan.get("orientation") or "", ""])
    for note in (material.get("limitations") or []) + (plan.get("notes") or []):
        rows.append([tr("row_note"), "", note])
    return rows


def _scene(registry):
    result = registry.call("list_objects", {})
    return [{"name": o["name"], "size": [o["size_mm"]["x"], o["size_mm"]["y"], o["size_mm"]["z"]]}
            for o in result.get("objects", []) if "size_mm" in o]


def generated_model_event(payload):
    validation = payload.get("validation") or {}
    return {"model_id": payload.get("model_id"), "object_id": payload.get("object_id"),
            "part_type": payload.get("part_type"), "title": payload.get("title"),
            "revision": payload.get("revision"), "parameters": payload.get("parameters") or {},
            "defaults_applied": payload.get("defaults_applied") or [], "size_mm": payload.get("size_mm"),
            "geometry_path": payload.get("geometry_path"), "warnings": payload.get("warnings") or [],
            "validation": {"status": validation.get("status"), "errors": validation.get("errors") or [],
                           "warnings": validation.get("warnings") or []}}


def publish_derived(bus, registry, name, args, payload):
    if not isinstance(payload, dict):
        return
    if name in GENERATED_TOOLS:
        bus.publish("generated_model", generated_model_event(payload))
    if name == "set_print_mode":
        bus.publish("setting_changed", {"key": "print_mode", "raw": payload.get("new"), "label": tr("mode"),
                                        "old": format_value("print_mode", payload.get("old")),
                                        "value": format_value("print_mode", payload.get("new"))})
    elif name == "set_setting":
        for event in _setting_events(payload.get("changes", [])):
            bus.publish("setting_changed", event)
    elif name == "set_settings":
        for event in _setting_events(payload.get("applied", [])):
            bus.publish("setting_changed", event)
    elif name == "set_material":
        bus.publish("setting_changed", {"key": "material", "label": tr("material"),
                                        "old": payload.get("old"), "value": payload.get("name") or payload.get("new")})
    elif name == "set_quality_profile":
        bus.publish("setting_changed", {"key": "quality", "label": tr("quality"),
                                        "old": payload.get("old"), "value": payload.get("name") or payload.get("new")})
    elif name == "slice":
        seconds = int(payload.get("print_time_s", 0))
        bus.publish("slice_result", {"time": _format_time(seconds), "length": tr("m") % payload.get("material_m", 0),
                                     "weight": tr("g") % payload.get("material_g", 0), "layers": "-"})
    elif name == "recommend_setup" and payload.get("applied"):
        bus.publish("decision", {"title": tr("decisions"), "rows": _decision_rows(payload)})
    if name in SCENE_TOOLS and (name != "recommend_setup" or payload.get("applied")):
        if name != "suggest_orientation" or payload.get("applied"):
            bus.publish("scene", {"objects": _scene(registry)})
