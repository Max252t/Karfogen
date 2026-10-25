from .. import config
from ..agent import knowledge
from ..mcp.registry import get_registry, ToolError
from .main_thread import run_on_main

registry = get_registry()

PRINT_MODES = ["classic", "cylindrical", "cylindrical_full"]
MODE_LABELS = {"classic": "3D", "cylindrical": "5D Spiral", "cylindrical_full": "5D"}
DEFAULT_MACHINE_DEFINITION = "hte530v5.2.4"


def _app():
    from steslicer.SteSlicerApplication import SteSlicerApplication
    return SteSlicerApplication.getInstance()


def _global_stack():
    stack = _app().getGlobalContainerStack()
    if stack is None:
        raise ToolError("No active printer. Call select_machine first.")
    return stack


def _extruder_stack(position):
    stack = _global_stack()
    ext = stack.extruders.get(str(position))
    if ext is None:
        raise ToolError("No extruder at position %s" % position)
    return ext


SLICER_LOCALES = {"ru": "ru_RU"}
_catalogs = {}


def _catalog_names(stack):
    try:
        import os
        from UM.Settings.ContainerRegistry import ContainerRegistry
        definition = stack.getBottom()
        suffix = ContainerRegistry.getMimeTypeForContainer(type(definition)).preferredSuffix
        names = [os.path.basename(definition.getId() + "." + suffix)]
        names.extend(os.path.basename(path) for path in definition.getInheritedFiles())
        return tuple(names)
    except Exception:
        return ()


def _catalogs_for(stack, language):
    locale = SLICER_LOCALES.get(language)
    names = _catalog_names(stack)
    if not locale or not names:
        return []
    cache_key = (locale, names)
    if cache_key not in _catalogs:
        try:
            from UM.i18n import i18nCatalog
            found = [i18nCatalog(name, locale) for name in names]
        except Exception:
            found = []
        _catalogs[cache_key] = [catalog for catalog in found if catalog.hasTranslationLoaded()]
    return _catalogs[cache_key]


def translate_label(stack, key, label):
    if not label:
        return label
    for catalog in _catalogs_for(stack, config.effective_language()):
        translated = catalog.i18nc("%s label" % key, label)
        if translated != label:
            return translated
    return label


def setting_label(stack, key):
    return translate_label(stack, key, stack.getProperty(key, "label"))


def _plain(value):
    if isinstance(value, (bool, int, float, str)) or value is None:
        return value
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    if isinstance(value, dict):
        return dict((str(k), _plain(v)) for k, v in value.items())
    return str(value)


def _setting_info(stack, key):
    return {
        "key": key,
        "label": setting_label(stack, key),
        "type": stack.getProperty(key, "type"),
        "unit": stack.getProperty(key, "unit"),
        "value": _plain(stack.getProperty(key, "value")),
        "options": _plain(stack.getProperty(key, "options")),
        "minimum": _plain(stack.getProperty(key, "minimum_value")),
        "maximum": _plain(stack.getProperty(key, "maximum_value")),
        "per_extruder": bool(stack.getProperty(key, "settable_per_extruder")),
        "description": stack.getProperty(key, "description"),
    }


def _convert_value(stack, key, value):
    stype = stack.getProperty(key, "type")
    if stype is None:
        raise ToolError("Unknown setting '%s'. Use search_settings to find the right key." % key)
    if stype == "bool":
        if isinstance(value, str):
            low = value.strip().lower()
            if low in ("true", "1", "yes", "on"):
                return True
            if low in ("false", "0", "no", "off"):
                return False
            raise ToolError("Setting '%s' expects boolean, got '%s'" % (key, value))
        return bool(value)
    if stype in ("int", "float"):
        if isinstance(value, bool):
            raise ToolError("Setting '%s' expects a number" % key)
        try:
            number = float(value)
        except (TypeError, ValueError):
            raise ToolError("Setting '%s' expects a number, got '%s'" % (key, value))
        result = int(round(number)) if stype == "int" else number
        for prop, cmp_ in (("minimum_value", lambda a, b: a < b), ("maximum_value", lambda a, b: a > b)):
            bound = stack.getProperty(key, prop)
            if isinstance(bound, (int, float)) and not isinstance(bound, bool) and cmp_(result, bound):
                raise ToolError("Setting '%s'=%s violates %s=%s" % (key, result, prop, bound))
        return result
    if stype == "enum":
        options = stack.getProperty(key, "options") or {}
        if value in options:
            return value
        for opt_key, label in options.items():
            if str(label).lower() == str(value).lower():
                return opt_key
        raise ToolError("Setting '%s' must be one of: %s" % (key, ", ".join(sorted(str(k) for k in options))))
    if stype in ("str", "extruder", "optional_extruder"):
        return str(value)
    raise ToolError("Setting type '%s' of '%s' cannot be changed by this tool" % (stype, key))


def _extruder_position(extruder):
    if isinstance(extruder, bool):
        raise ToolError("extruder must be an integer")
    try:
        number = float(extruder)
        position = int(number)
    except (TypeError, ValueError, OverflowError):
        raise ToolError("extruder must be an integer, got '%s'" % (extruder,))
    if number != position:
        raise ToolError("extruder must be an integer, got '%s'" % (extruder,))
    return position


def _target_stacks(stack, key, extruder):
    if not stack.getProperty(key, "settable_per_extruder"):
        return [("global", stack)]
    position = 0 if extruder is None else _extruder_position(extruder)
    if position < 0:
        return [("extruder %s" % pos, ext) for pos, ext in sorted(stack.extruders.items()) if ext.isEnabled]
    ext = stack.extruders.get(str(position))
    if ext is None:
        raise ToolError("No extruder at position %s" % position)
    return [("extruder %s" % position, ext)]


def check_key_allowed(key):
    low = str(key or "").lower()
    if low.startswith("machine_") or "gcode" in low:
        raise ToolError("Setting '%s' is protected and cannot be changed by the assistant" % key)


def _apply_setting(key, value, extruder):
    check_key_allowed(key)
    stack = _global_stack()
    converted = _convert_value(stack, key, value)
    changes = []
    for scope, target in _target_stacks(stack, key, extruder):
        old = _plain(target.getProperty(key, "value"))
        target.userChanges.setProperty(key, "value", converted)
        new = _plain(target.getProperty(key, "value"))
        changes.append({"key": key, "label": setting_label(stack, key), "scope": scope, "old": old, "new": new})
    return changes


def apply_settings_on_main(items):
    applied = []
    errors = []
    for item in items:
        key = item.get("key")
        try:
            applied.extend(_apply_setting(key, item.get("value"), item.get("extruder")))
        except ToolError as e:
            errors.append({"key": key, "error": str(e)})
        except (TypeError, ValueError, AttributeError) as e:
            errors.append({"key": key, "error": "%s: %s" % (e.__class__.__name__, e)})
    return {"applied": applied, "errors": errors}


@registry.tool("select_machine",
               "Select the active printer. Default is Stereotech Hybrid 530 V5.2.4 (definition 'hte530v5.2.4'). "
               "Call this first if get_machine shows a different printer.",
               {"definition_id": {"type": "string", "description": "Machine definition id, default hte530v5.2.4"}})
def select_machine(args):
    definition_id = args.get("definition_id") or DEFAULT_MACHINE_DEFINITION

    def work():
        from UM.Settings.ContainerRegistry import ContainerRegistry
        app = _app()
        mm = app.getMachineManager()
        stacks = ContainerRegistry.getInstance().findContainerStacks(type="machine")
        for st in stacks:
            if st.definition.getId() == definition_id:
                if app.getGlobalContainerStack() is not st:
                    mm.setActiveMachine(st.getId())
                return {"machine_id": st.getId(), "name": st.getName(), "created": False}
        defs = ContainerRegistry.getInstance().findDefinitionContainersMetadata(id=definition_id)
        if not defs:
            raise ToolError("Unknown machine definition '%s'" % definition_id)
        name = defs[0].get("name", definition_id)
        mm.addMachine(name, definition_id)
        stack = app.getGlobalContainerStack()
        return {"machine_id": stack.getId(), "name": stack.getName(), "created": True}
    return run_on_main(work, _timeout=60)


@registry.tool("get_machine", "Return the active printer, its definition id, build volume and extruders with material and nozzle.")
def get_machine(args):
    def work():
        stack = _global_stack()
        extruders = []
        for pos, ext in sorted(stack.extruders.items()):
            extruders.append({
                "position": int(pos),
                "enabled": bool(ext.isEnabled),
                "material_id": ext.material.getId(),
                "material_name": ext.material.getName(),
                "nozzle": ext.variant.getName(),
                "material_diameter": _plain(ext.getProperty("material_diameter", "value")),
            })
        mm = _app().getMachineManager()
        return {
            "machine_id": stack.getId(),
            "name": stack.getName(),
            "definition_id": stack.definition.getId(),
            "print_mode": stack.getProperty("printing_mode", "value"),
            "build_volume_mm": {
                "width": _plain(stack.getProperty("machine_width", "value")),
                "depth": _plain(stack.getProperty("machine_depth", "value")),
                "height": _plain(stack.getProperty("machine_height", "value")),
            },
            "quality_type": mm.activeQualityType,
            "extruders": extruders,
        }
    return run_on_main(work)


@registry.tool("get_print_mode", "Return the current printing mode: classic (3D), cylindrical (5D Spiral) or cylindrical_full (5D).")
def get_print_mode(args):
    def work():
        mode = _global_stack().getProperty("printing_mode", "value")
        return {"mode": mode, "label": MODE_LABELS.get(mode, mode)}
    return run_on_main(work)


@registry.tool("set_print_mode",
               "Switch the printing mode. classic = regular 3D, cylindrical = 5D Spiral, cylindrical_full = 5D. "
               "Switching changes the backend and the build volume, so do it before arranging models and choosing quality.",
               {"mode": {"type": "string", "enum": PRINT_MODES}}, ["mode"])
def set_print_mode(args):
    mode = args["mode"]

    def work():
        stack = _global_stack()
        old = stack.getProperty("printing_mode", "value")
        if old != mode:
            stack.userChanges.setProperty("printing_mode", "value", mode)
        return {"key": "printing_mode", "old": old, "new": stack.getProperty("printing_mode", "value"),
                "label": MODE_LABELS.get(mode, mode)}
    return run_on_main(work)


def _quality_groups():
    app = _app()
    stack = _global_stack()
    return app.getQualityManager().getQualityGroups(stack)


def _layer_height(group, stack):
    from UM.Settings.SettingFunction import SettingFunction
    value = None
    try:
        node = group.node_for_global
        container = node.getContainer() if node else None
        if container is not None:
            value = container.getProperty("layer_height", "value")
        if isinstance(value, SettingFunction):
            value = value(stack)
        if value is None:
            value = stack.definition.getProperty("layer_height", "default_value")
        return round(float(value), 3)
    except (TypeError, ValueError, AttributeError):
        return None


@registry.tool("list_quality_profiles",
               "List quality profiles available for the current printer, material and print mode, with layer height. "
               "Choose one for set_quality_profile.")
def list_quality_profiles(args):
    def work():
        groups = _quality_groups()
        mm = _app().getMachineManager()
        result = []
        stack = _global_stack()
        for qtype, group in groups.items():
            result.append({"quality_type": qtype, "name": group.name,
                           "available": bool(group.is_available), "layer_height": _layer_height(group, stack)})
        result.sort(key=lambda r: (r["layer_height"] is None, r["layer_height"] or 0.0, r["quality_type"]))
        return {"active": mm.activeQualityType, "profiles": result}
    return run_on_main(work)


@registry.tool("set_quality_profile", "Select a quality profile by quality_type taken from list_quality_profiles.",
               {"quality_type": {"type": "string"}}, ["quality_type"])
def set_quality_profile(args):
    qtype = args["quality_type"]

    def work():
        groups = _quality_groups()
        group = groups.get(qtype)
        if group is None:
            raise ToolError("Unknown quality_type '%s'. Available: %s" % (qtype, ", ".join(sorted(groups))))
        if not group.is_available:
            raise ToolError("Quality profile '%s' is not available for the current material/mode" % qtype)
        mm = _app().getMachineManager()
        old = mm.activeQualityType
        mm.setQualityGroup(group, no_dialog=True)
        return {"old": old, "new": mm.activeQualityType, "name": group.name}
    return run_on_main(work, _timeout=60)


def _available_materials(position):
    app = _app()
    stack = _global_stack()
    ext = _extruder_stack(position)
    nodes = app.getMaterialManager().getAvailableMaterialsForMachineExtruder(stack, ext) or {}
    return nodes


@registry.tool("list_materials",
               "List materials available for an extruder: id, brand, material type (PLA, PETG, ...), name. "
               "Use the id with set_material.",
               {"extruder": {"type": "integer", "description": "Extruder position, default 0"}})
def list_materials(args):
    position = args.get("extruder", 0)

    def work():
        nodes = _available_materials(position)
        active = _extruder_stack(position).material.getMetaDataEntry("base_file", "")
        result = []
        for root_id, node in sorted(nodes.items()):
            result.append({
                "id": root_id,
                "name": node.getMetaDataEntry("name", root_id),
                "brand": node.getMetaDataEntry("brand", ""),
                "type": node.getMetaDataEntry("material", ""),
            })
        return {"extruder": position, "active_material": active, "materials": result}
    return run_on_main(work)


@registry.tool("set_material", "Select the material for an extruder by id from list_materials. Choose the material before the quality profile.",
               {"material_id": {"type": "string"},
                "extruder": {"type": "integer", "description": "Extruder position, default 0"}},
               ["material_id"])
def set_material(args):
    material_id = args["material_id"]
    position = args.get("extruder", 0)

    def work():
        nodes = _available_materials(position)
        if material_id not in nodes:
            raise ToolError("Material '%s' is not available. Call list_materials." % material_id)
        ext = _extruder_stack(position)
        old = ext.material.getMetaDataEntry("base_file", "")
        _app().getMachineManager().setMaterialById(str(position), material_id)
        node = nodes[material_id]
        result = {"extruder": position, "old": old, "new": ext.material.getMetaDataEntry("base_file", ""),
                  "name": node.getMetaDataEntry("name", material_id)}
        warning = knowledge.material_warning(material_id)
        if warning:
            result["warning"] = warning
        return result
    return run_on_main(work, _timeout=60)


@registry.tool("get_setting", "Read a setting: current value, label, type, unit, limits and options.",
               {"key": {"type": "string"},
                "extruder": {"type": "integer", "description": "Extruder position for per-extruder settings"}},
               ["key"])
def get_setting(args):
    key = args["key"]
    extruder = args.get("extruder")

    def work():
        stack = _global_stack()
        if stack.getProperty(key, "type") is None:
            raise ToolError("Unknown setting '%s'. Use search_settings." % key)
        info = _setting_info(stack, key)
        if extruder is not None and stack.getProperty(key, "settable_per_extruder"):
            info["value"] = _plain(_extruder_stack(extruder).getProperty(key, "value"))
        return info
    return run_on_main(work)


@registry.tool("set_setting",
               "Set one slicer setting (stored as a user change). Values are validated against type and limits. "
               "Per-extruder settings go to extruder 0 unless extruder is given (-1 = all enabled extruders). "
               "Returns old and new values.",
               {"key": {"type": "string"}, "value": {"type": ["string", "number", "boolean"]},
                "extruder": {"type": "integer"}}, ["key", "value"])
def set_setting(args):
    key = args["key"]

    def work():
        return {"changes": _apply_setting(key, args["value"], args.get("extruder"))}
    return run_on_main(work)


@registry.tool("set_settings",
               "Set several settings at once. changes is a list of {key, value, extruder?}. Failed items are reported in 'errors' and do not stop the others.",
               {"changes": {"type": "array", "items": {
                   "type": "object",
                   "properties": {"key": {"type": "string"}, "value": {"type": ["string", "number", "boolean"]},
                                  "extruder": {"type": "integer"}},
                   "required": ["key", "value"]}}}, ["changes"])
def set_settings(args):
    items = args["changes"]
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("key"), str) or "value" not in item:
            raise ToolError("Each change must be an object with a string key and a value")
        if item.get("extruder") is not None:
            _extruder_position(item["extruder"])
        if isinstance(item["value"], (dict, list)):
            raise ToolError("Value of '%s' must be a string, number or boolean" % item["key"])
    return run_on_main(apply_settings_on_main, items)


@registry.tool("search_settings",
               "Find setting keys by substring of key, English or localized label, or English description. Returns up to 25 matches with current values.",
               {"query": {"type": "string"}}, ["query"])
def search_settings(args):
    query = args["query"].strip().lower()
    if not query:
        raise ToolError("query is empty")
    words = query.split()

    def work():
        stack = _global_stack()
        found = []
        for definition in stack.definition.findDefinitions():
            if definition.type in ("category",):
                continue
            hay_key = definition.key.lower()
            localized = translate_label(stack, definition.key, definition.label)
            hay = hay_key + " " + str(definition.label).lower() + " " + str(localized).lower()
            hay_desc = hay + " " + str(getattr(definition, "description", "")).lower()
            if all(w in hay for w in words):
                rank = 0
            elif all(w in hay_desc for w in words):
                rank = 1
            else:
                continue
            found.append((rank, hay_key, definition.key))
        found.sort()
        result = []
        for _, _, key in found[:25]:
            result.append({"key": key, "label": setting_label(stack, key),
                           "type": stack.getProperty(key, "type"),
                           "unit": stack.getProperty(key, "unit"),
                           "value": _plain(stack.getProperty(key, "value"))})
        return {"matches": result, "total": len(found)}
    return run_on_main(work)


@registry.tool("get_changed_settings", "List all user-changed settings (what differs from the selected profile).")
def get_changed_settings(args):
    def work():
        stack = _global_stack()
        out = []
        for scope, container_stack in [("global", stack)] + [("extruder %s" % p, e) for p, e in sorted(stack.extruders.items())]:
            for key in sorted(container_stack.userChanges.getAllKeys()):
                out.append({"scope": scope, "key": key, "label": setting_label(stack, key),
                            "value": _plain(container_stack.userChanges.getProperty(key, "value"))})
        return {"changes": out}
    return run_on_main(work)


@registry.tool("reset_settings", "Discard all user setting changes and any custom profile, returning to the standard profile of the same quality. The print mode is kept; change it with set_print_mode.")
def reset_settings(args):
    def work():
        stack = _global_stack()
        mode = stack.getProperty("printing_mode", "value")
        stack.userChanges.clear()
        for ext in stack.extruders.values():
            ext.userChanges.clear()
        mm = _app().getMachineManager()
        had_custom_profile = bool(mm.activeQualityChangesGroup)
        if mm.activeQualityGroup is not None:
            mm.resetToUseDefaultQuality()
        if stack.getProperty("printing_mode", "value") != mode:
            stack.userChanges.setProperty("printing_mode", "value", mode)
        return {"ok": True, "print_mode_kept": mode, "custom_profile_dropped": had_custom_profile}
    return run_on_main(work)


@registry.tool("create_profile", "Save the current user setting changes as a custom quality profile with the given name.",
               {"name": {"type": "string"}}, ["name"])
def create_profile(args):
    name = args["name"]

    def work():
        _app().getQualityManager().createQualityChanges(name)
        return {"ok": True, "name": name}
    return run_on_main(work)


def current_setup():
    stack = _global_stack()
    mm = _app().getMachineManager()
    return {
        "print_mode": stack.getProperty("printing_mode", "value"),
        "quality_type": mm.activeQualityType,
        "materials": dict((p, e.material.getMetaDataEntry("base_file", "")) for p, e in stack.extruders.items()),
    }
