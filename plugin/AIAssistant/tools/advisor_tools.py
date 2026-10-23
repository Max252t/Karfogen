from ..agent import knowledge
from ..mcp.registry import get_registry, ToolError

registry = get_registry()

FUNCTIONAL_TAGS = set(["load_bearing", "wear", "chemical", "high_temp", "rotating", "stiff", "airtight"])


def _call(name, args=None):
    return registry.call(name, args or {})


def _clean_tags(tags):
    result = []
    for tag in tags or []:
        if tag not in knowledge.TAGS:
            raise ToolError("Unknown tag '%s'. Allowed: %s" % (tag, ", ".join(knowledge.TAGS)))
        if tag not in result:
            result.append(tag)
    return result


def _pick_quality(wanted, profiles):
    available = [p for p in profiles if p["available"] and p["layer_height"] is not None]
    for p in available:
        if p["quality_type"] == wanted:
            return p["quality_type"]
    target = knowledge.QUALITY_LAYER_HEIGHT.get(wanted)
    if target is None or not available:
        return None
    available.sort(key=lambda p: abs(p["layer_height"] - target))
    return available[0]["quality_type"]


@registry.tool("recommend_setup",
               "Deterministic expert rules: from the object geometry and requirement tags choose the print mode (3D / 5D Spiral / 5D), material, "
               "quality profile and key settings, with reasons. Fill tags from the user's task (allowed: %s). "
               "max_temp_c is the highest service temperature in Celsius. flexibility: rigid, semi or flexible. "
               "With apply=true everything is applied: printer, mode, orientation, material, quality profile, settings. "
               "Review the returned reasons and explain them to the user." % ", ".join(knowledge.TAGS.keys()),
               {"object_id": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
                "max_temp_c": {"type": "number"},
                "flexibility": {"type": "string", "enum": ["rigid", "semi", "flexible"]},
                "force_mode": {"type": "string", "enum": ["classic", "cylindrical", "cylindrical_full"]},
                "apply": {"type": "boolean"}})
def recommend_setup(args):
    tags = _clean_tags(args.get("tags"))
    analysis = _call("analyze_mesh", {"object_id": args["object_id"]} if args.get("object_id") else {})
    object_id = analysis["object_id"]

    mode, mode_reasons = knowledge.choose_mode(analysis, tags)
    if args.get("force_mode"):
        mode = args["force_mode"]
        mode_reasons = ["режим задан явно: %s" % knowledge.MODE_LABELS[mode]]

    ranked = knowledge.rank_materials(tags, args.get("max_temp_c"), args.get("flexibility"))
    materials = _call("list_materials", {})["materials"]
    available_ids = [m["id"] for m in materials]
    prefer_enduse = bool(set(tags) & FUNCTIONAL_TAGS) and "decorative" not in tags
    material_id = None
    material_type = None
    for candidate in ranked:
        material_id = knowledge.resolve_material_id(candidate["type"], available_ids, prefer_enduse)
        if material_id:
            material_type = candidate
            break
    if material_id is None:
        raise ToolError("No suitable material is available for the current printer")

    profiles = _call("list_quality_profiles", {})["profiles"]
    wanted_quality, settings, reasons = knowledge.recommend_settings(tags, mode)
    quality = _pick_quality(wanted_quality, profiles) or wanted_quality

    orientation_goal = "no_supports" if ("no_supports" in tags or "thin_features" in tags) else "balanced"
    plan = {
        "object_id": object_id,
        "mode": mode,
        "mode_label": knowledge.MODE_LABELS[mode],
        "mode_reasons": mode_reasons,
        "material": {"id": material_id, "type": material_type["type"], "score": material_type["score"],
                     "alternatives": [r["type"] for r in ranked[1:4]]},
        "quality_type": quality,
        "quality_reason": reasons.get("quality"),
        "settings": [{"key": k, "value": v, "reason": reasons.get(k, "")} for k, v in settings.items()],
        "orientation": "ось симметрии вертикально, по центру стола" if mode != "classic" else "ориентация по цели %s" % orientation_goal,
        "applied": False,
    }
    if not args.get("apply"):
        return plan

    _call("select_machine", {})
    _call("set_print_mode", {"mode": mode})
    if mode == "classic":
        _call("suggest_orientation", {"object_id": object_id, "goal": orientation_goal, "apply": True})
    else:
        _call("align_symmetry_axis", {"object_id": object_id})
        _call("move_object", {"object_id": object_id, "x": 0, "y": 0})
    _call("set_material", {"material_id": material_id})
    profiles_after = _call("list_quality_profiles", {})["profiles"]
    quality = _pick_quality(wanted_quality, profiles_after) or quality
    _call("set_quality_profile", {"quality_type": quality})
    plan["quality_type"] = quality
    outcome = _call("set_settings", {"changes": [{"key": k, "value": v} for k, v in settings.items()]})
    plan["applied"] = True
    plan["apply_result"] = outcome
    plan["size_after"] = _call("get_object_bounds", {"object_id": object_id})
    return plan
