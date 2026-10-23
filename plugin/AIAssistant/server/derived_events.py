SCENE_TOOLS = set([
    "load_model", "delete_object", "clear_scene", "rotate_object", "move_object", "scale_object",
    "set_orientation", "lay_flat", "align_symmetry_axis", "arrange_all", "suggest_orientation", "recommend_setup",
])

MODE_LABELS = {"classic": "3D", "cylindrical": "5D Spiral", "cylindrical_full": "5D"}


def format_value(key, value):
    if isinstance(value, bool):
        return "да" if value else "нет"
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
    return "%d ч %02d мин" % (seconds // 3600, (seconds % 3600) // 60)


def _decision_rows(plan):
    rows = [["Режим", plan["mode_label"], "; ".join(plan.get("mode_reasons") or [])]]
    material = plan["material"]
    rows.append(["Материал", "%s (%s)" % (material["id"], material["type"]),
                 "альтернативы: %s" % ", ".join(material.get("alternatives") or [])])
    rows.append(["Профиль качества", plan["quality_type"], plan.get("quality_reason") or ""])
    for item in plan.get("settings") or []:
        rows.append([item["key"], str(format_value(item["key"], item["value"])), item.get("reason") or ""])
    rows.append(["Ориентация", plan.get("orientation") or "", ""])
    return rows


def _scene(registry):
    result = registry.call("list_objects", {})
    return [{"name": o["name"], "size": [o["size_mm"]["x"], o["size_mm"]["y"], o["size_mm"]["z"]]}
            for o in result.get("objects", []) if "size_mm" in o]


def publish_derived(bus, registry, name, args, payload):
    if not isinstance(payload, dict):
        return
    if name == "set_print_mode":
        bus.publish("setting_changed", {"key": "print_mode", "raw": payload.get("new"), "label": "режим",
                                        "old": format_value("print_mode", payload.get("old")),
                                        "value": format_value("print_mode", payload.get("new"))})
    elif name == "set_setting":
        for event in _setting_events(payload.get("changes", [])):
            bus.publish("setting_changed", event)
    elif name == "set_settings":
        for event in _setting_events(payload.get("applied", [])):
            bus.publish("setting_changed", event)
    elif name == "set_material":
        bus.publish("setting_changed", {"key": "material", "label": "материал",
                                        "old": payload.get("old"), "value": payload.get("name") or payload.get("new")})
    elif name == "set_quality_profile":
        bus.publish("setting_changed", {"key": "quality", "label": "профиль качества",
                                        "old": payload.get("old"), "value": payload.get("name") or payload.get("new")})
    elif name == "slice":
        seconds = int(payload.get("print_time_s", 0))
        bus.publish("slice_result", {"time": _format_time(seconds), "length": "%.1f м" % payload.get("material_m", 0),
                                     "weight": "%.0f г" % payload.get("material_g", 0), "layers": "-"})
    elif name == "recommend_setup" and payload.get("applied"):
        bus.publish("decision", {"title": "Принятые решения", "rows": _decision_rows(payload)})
    if name in SCENE_TOOLS and (name != "recommend_setup" or payload.get("applied")):
        if name != "suggest_orientation" or payload.get("applied"):
            bus.publish("scene", {"objects": _scene(registry)})
