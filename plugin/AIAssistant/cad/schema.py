import math
from collections import OrderedDict

from . import threads
from .errors import CadError

SCHEMA_VERSION = 1
MAX_HOLES = 16
HOLE_KEYS = ("x_mm", "y_mm", "diameter_mm")
MIN_EDGE_DISTANCE_MM = 1.0


def number(unit, minimum, maximum, default=None, critical=False, description=""):
    return {"type": "number", "unit": unit, "min": minimum, "max": maximum, "default": default,
            "critical": critical, "description": description}


def integer(minimum, maximum, default=None, critical=False, description=""):
    return {"type": "integer", "unit": "", "min": minimum, "max": maximum, "default": default,
            "critical": critical, "description": description}


def choice(values, default=None, critical=False, description=""):
    return {"type": "string", "unit": "", "enum": list(values), "default": default, "critical": critical,
            "description": description}


def flag(default, description=""):
    return {"type": "boolean", "unit": "", "default": default, "critical": False, "description": description}


def hole_list(description=""):
    return {"type": "array", "unit": "mm", "default": [], "critical": False, "max_items": MAX_HOLES,
            "item_keys": list(HOLE_KEYS), "description": description}


SIZE_NAMES = threads.size_names()

PARTS = OrderedDict()

PARTS["bolt"] = {
    "title": "Bolt",
    "description": "Metric bolt, axis along Z, head on the build plate and the shank pointing up. "
                   "Right-hand ISO profile thread, modeled as real geometry.",
    "standards": [threads.SOURCES["thread"], threads.SOURCES["bolt"]],
    "parameters": OrderedDict([
        ("thread_size", choice(SIZE_NAMES, critical=True, description="Nominal thread diameter, e.g. M8.")),
        ("length_mm", number("mm", 2.0, 200.0, critical=True, description="Shank length under the head.")),
        ("head_type", choice(["hex", "cylindrical", "countersunk"], critical=True,
                             description="hex: hexagonal head; cylindrical: socket cap head with hex socket; "
                                         "countersunk: flat 90 degree head with hex socket.")),
        ("pitch_mm", number("mm", 0.5, 2.5, description="Thread pitch. Default: coarse pitch of the size. "
                                                       "Allowed values depend on thread_size.")),
        ("thread_length_mm", number("mm", 1.0, 200.0, description="Threaded part of the shank, counted from the tip. "
                                                                 "Default: the full length.")),
        ("thread_mode", choice(["modeled", "cosmetic"], default="modeled",
                               description="modeled: real printable thread. cosmetic: not printable as a thread, "
                                           "replaced by a smooth cylinder with a warning.")),
        ("clearance_mm", number("mm", 0.0, 0.5, default=0.1,
                                description="Radial printing compensation: the thread is made smaller by this value "
                                            "on each side.")),
        ("load_bearing", flag(False, "True if the bolt is meant to carry load (adds a stronger warning).")),
    ]),
}

PARTS["nut"] = {
    "title": "Hex nut",
    "description": "Metric hex nut, axis along Z, flat face on the build plate. Internal right-hand ISO thread.",
    "standards": [threads.SOURCES["thread"], threads.SOURCES["nut"]],
    "parameters": OrderedDict([
        ("thread_size", choice(SIZE_NAMES, critical=True, description="Nominal thread diameter, e.g. M8.")),
        ("pitch_mm", number("mm", 0.5, 2.5, description="Thread pitch. Default: coarse pitch of the size.")),
        ("thickness_mm", number("mm", 1.0, 80.0, description="Nut height. Default: standard height of the size.")),
        ("thread_mode", choice(["modeled", "cosmetic"], default="modeled",
                               description="modeled: real printable thread. cosmetic: replaced by a smooth bore "
                                           "with a warning.")),
        ("clearance_mm", number("mm", 0.0, 0.6, default=0.15,
                                description="Radial printing compensation: the thread bore is larger by this value "
                                            "on each side, separately from the nominal size.")),
    ]),
}

PARTS["washer"] = {
    "title": "Washer",
    "description": "Plain flat washer, axis along Z.",
    "standards": [threads.SOURCES["washer"]],
    "parameters": OrderedDict([
        ("thread_size", choice(SIZE_NAMES, critical=True, description="Fastener size the washer is made for.")),
        ("thickness_mm", number("mm", 0.4, 10.0, description="Default: standard thickness of the size.")),
        ("clearance_mm", number("mm", 0.0, 0.5, default=0.1,
                                description="Radial printing compensation added to the inner hole radius.")),
    ]),
}

PARTS["plate"] = {
    "title": "Rectangular plate with holes",
    "description": "Rectangular plate centered on the origin with through holes. Holes are placed by their center "
                   "relative to the plate center: x to the right, y to the back.",
    "standards": [],
    "parameters": OrderedDict([
        ("width_mm", number("mm", 5.0, 300.0, critical=True, description="Size along X.")),
        ("depth_mm", number("mm", 5.0, 300.0, critical=True, description="Size along Y.")),
        ("thickness_mm", number("mm", 0.8, 50.0, critical=True, description="Size along Z.")),
        ("holes", hole_list("Up to %d holes, each {x_mm, y_mm, diameter_mm}. Nominal diameters; compensation "
                            "is added separately." % MAX_HOLES)),
        ("hole_clearance_mm", number("mm", 0.0, 0.6, default=0.2,
                                     description="Printing compensation added to every hole diameter.")),
    ]),
}

PARTS["bracket"] = {
    "title": "Angle bracket",
    "description": "Simple 90 degree angle bracket: a horizontal leg on the build plate and a vertical leg, "
                   "both with evenly spaced round holes along the leg center line.",
    "standards": [],
    "parameters": OrderedDict([
        ("length_mm", number("mm", 10.0, 200.0, critical=True, description="Outer length of the horizontal leg (X).")),
        ("height_mm", number("mm", 10.0, 200.0, critical=True, description="Outer height of the vertical leg (Z).")),
        ("width_mm", number("mm", 5.0, 200.0, critical=True, description="Width of both legs (Y).")),
        ("hole_diameter_mm", number("mm", 0.0, 30.0, critical=True,
                                    description="Nominal diameter of the mounting holes; 0 means no holes.")),
        ("thickness_mm", number("mm", 2.0, 20.0, default=4.0, description="Thickness of both legs.")),
        ("holes_per_leg", integer(1, 4, default=1, description="Number of holes in each leg.")),
        ("hole_clearance_mm", number("mm", 0.0, 0.6, default=0.2,
                                     description="Printing compensation added to every hole diameter.")),
    ]),
}


def part_types():
    return list(PARTS.keys())


def describe():
    result = []
    for part_type, part in PARTS.items():
        params = []
        for name, spec in part["parameters"].items():
            item = {"name": name, "type": spec["type"], "unit": spec["unit"], "critical": spec["critical"],
                    "default": spec["default"], "description": spec["description"]}
            for key in ("min", "max", "enum", "max_items", "item_keys"):
                if key in spec:
                    item[key] = spec[key]
            params.append(item)
        entry = {"part_type": part_type, "title": part["title"], "description": part["description"],
                 "standards": list(part["standards"]), "parameters": params}
        if "thread_size" in part["parameters"]:
            entry["thread_sizes"] = [{"thread_size": name, "pitches_mm": list(threads.size_data(name)["pitches"])}
                                     for name in SIZE_NAMES]
        result.append(entry)
    return result


def _type_name(value):
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def _check_number(field, value, spec, integer_only=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CadError(field, "must be a number in %s, got %s" % (spec["unit"] or "units", _type_name(value)))
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        raise CadError(field, "must be a finite number")
    if integer_only and float(value) != int(value):
        raise CadError(field, "must be an integer")
    if value < spec["min"] or value > spec["max"]:
        raise CadError(field, "%s is outside the allowed range %s..%s %s" % (value, spec["min"], spec["max"],
                                                                              spec["unit"]))
    return int(value) if integer_only else float(value)


def _check_holes(field, value, spec):
    if not isinstance(value, list):
        raise CadError(field, "must be an array of {x_mm, y_mm, diameter_mm}, got %s" % _type_name(value))
    if len(value) > spec["max_items"]:
        raise CadError(field, "at most %d holes are supported" % spec["max_items"])
    result = []
    for index, item in enumerate(value):
        name = "%s[%d]" % (field, index)
        if not isinstance(item, dict):
            raise CadError(name, "must be an object with x_mm, y_mm, diameter_mm")
        unknown = [key for key in item if key not in HOLE_KEYS]
        if unknown:
            raise CadError(name, "unknown keys: %s" % ", ".join(sorted(str(k) for k in unknown)))
        entry = {}
        for key in HOLE_KEYS:
            if key not in item:
                raise CadError("%s.%s" % (name, key), "is required")
            if key == "diameter_mm":
                sub = {"unit": "mm", "min": 0.5, "max": 100.0}
            else:
                sub = {"unit": "mm", "min": -1000.0, "max": 1000.0}
            entry[key] = _check_number("%s.%s" % (name, key), item[key], sub)
        result.append(entry)
    return result


def _check_value(field, value, spec):
    kind = spec["type"]
    if kind == "number":
        return _check_number(field, value, spec)
    if kind == "integer":
        return _check_number(field, value, spec, True)
    if kind == "boolean":
        if not isinstance(value, bool):
            raise CadError(field, "must be true or false, got %s" % _type_name(value))
        return value
    if kind == "string":
        if not isinstance(value, str) or value not in spec["enum"]:
            raise CadError(field, "must be one of: %s" % ", ".join(spec["enum"]))
        return value
    if kind == "array":
        return _check_holes(field, value, spec)
    raise CadError(field, "unsupported parameter type")


def normalize(part_type, given):
    part = PARTS.get(part_type)
    if part is None:
        raise CadError("part_type", "unknown part type '%s'. Supported: %s" % (part_type, ", ".join(part_types())))
    if not isinstance(given, dict):
        raise CadError("parameters", "must be an object")
    specs = part["parameters"]
    unknown = [key for key in given if key not in specs]
    if unknown:
        raise CadError("parameters.%s" % sorted(unknown)[0],
                       "unknown parameter. Allowed: %s" % ", ".join(specs.keys()))
    values = OrderedDict()
    defaults = []
    for name, spec in specs.items():
        if name in given and given[name] is not None:
            values[name] = _check_value(name, given[name], spec)
        elif spec["critical"]:
            raise CadError(name, "critical parameter is missing: ask the user for it, do not guess. %s"
                           % spec["description"])
        elif spec["default"] is not None:
            values[name] = list(spec["default"]) if isinstance(spec["default"], list) else spec["default"]
            defaults.append(name)
    _resolve_dependent(part_type, values, defaults)
    return values, defaults


def _resolve_dependent(part_type, values, defaults):
    if "thread_size" not in values:
        return
    data = threads.size_data(values["thread_size"])
    allowed = data["pitches"]
    if "pitch_mm" in values:
        if not any(abs(values["pitch_mm"] - p) < 1e-6 for p in allowed):
            raise CadError("pitch_mm", "%s has pitch values %s mm" % (values["thread_size"],
                                                                      ", ".join("%g" % p for p in allowed)))
    elif part_type in ("bolt", "nut"):
        values["pitch_mm"] = allowed[0]
        defaults.append("pitch_mm")
    if part_type == "bolt":
        if "thread_length_mm" in values:
            if values["thread_length_mm"] > values["length_mm"] + 1e-9:
                raise CadError("thread_length_mm", "cannot exceed length_mm (%g)" % values["length_mm"])
            if values["thread_length_mm"] < 2 * values["pitch_mm"]:
                raise CadError("thread_length_mm", "must be at least two pitches (%g mm)" % (2 * values["pitch_mm"]))
        else:
            values["thread_length_mm"] = values["length_mm"]
            defaults.append("thread_length_mm")
        if values["length_mm"] < 2 * values["pitch_mm"]:
            raise CadError("length_mm", "must be at least two pitches (%g mm)" % (2 * values["pitch_mm"]))
    elif part_type == "nut":
        if "thickness_mm" not in values:
            values["thickness_mm"] = data["nut_m"]
            defaults.append("thickness_mm")
        if values["thickness_mm"] < 2 * values["pitch_mm"]:
            raise CadError("thickness_mm", "must be at least two pitches (%g mm)" % (2 * values["pitch_mm"]))
    elif part_type == "washer":
        if "thickness_mm" not in values:
            values["thickness_mm"] = data["washer"][2]
            defaults.append("thickness_mm")


def merge(existing, changes):
    if not isinstance(changes, dict):
        raise CadError("parameters", "must be an object")
    merged = OrderedDict()
    for key, value in existing.items():
        merged[key] = value
    for key, value in changes.items():
        if value is not None:
            merged[key] = value
    return merged
