import copy
import hashlib
import json
import os
import tempfile
import time
import uuid

from .. import config
from . import meshbuild, parts, schema, validation
from .errors import CadError
from .store import SCENE_SESSION_ID, get_store

GENERATED_DIR = "_generated"
EXPORT_FORMATS = ("stl", "3mf")


class NullScene(object):
    def add_model(self, path):
        return {"object_id": None, "size_mm": None}

    def remove_model(self, object_id):
        return None

    def object_size(self, object_id):
        return None

    def build_volume(self):
        return None


def results_root():
    root = os.path.join(config.get_results_dir(), GENERATED_DIR)
    if not os.path.isdir(root):
        os.makedirs(root)
    return root


def inside(root, path):
    root = os.path.realpath(root)
    path = os.path.realpath(path)
    return path == root or path.startswith(root + os.sep)


def atomic_write(path, data):
    descriptor, temporary = tempfile.mkstemp(prefix=".cad-", dir=os.path.dirname(path))
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.remove(temporary)


def geometry_path(label, part_type, values):
    digest = hashlib.sha1(json.dumps([part_type, values], sort_keys=True).encode("utf-8")).hexdigest()[:8]
    name = "%s_%s.stl" % (config.safe_name(label), digest)
    root = results_root()
    path = os.path.join(root, name)
    if not inside(root, path):
        raise CadError("", "the output path is outside the results folder")
    return path


def list_parts():
    return {"units": "mm", "parts": schema.describe(), "schema_version": schema.SCHEMA_VERSION}


def _public_warnings(items):
    return [dict(code=w["code"], message=w["message"]) for w in items]


def _build_and_check(part_type, requested, scene):
    values, defaults = schema.normalize(part_type, requested)
    mesh, info = parts.build(part_type, values)
    report = validation.check(mesh, info["expected_size_mm"], info["min_wall_mm"], scene.build_volume())
    if not report["valid"]:
        blocking = [e for e in report["errors"] if e["code"] != "exceeds_build_volume"]
        if blocking:
            raise CadError("", "the generated mesh failed validation: %s"
                           % "; ".join(e["message"] for e in blocking))
    return values, defaults, mesh, info, report


def _spec(part_type, requested, values, defaults, info, path, report, previous=None):
    now = time.time()
    spec = {
        "schema_version": schema.SCHEMA_VERSION,
        "scene_session_id": SCENE_SESSION_ID,
        "model_id": previous["model_id"] if previous else uuid.uuid4().hex[:8],
        "part_type": part_type,
        "units": "mm",
        "requested": copy.deepcopy(dict(requested)),
        "parameters": copy.deepcopy(dict(values)),
        "defaults_applied": list(defaults),
        "label": info["label"],
        "title": info["title"],
        "path": path,
        "object_id": previous.get("object_id") if previous else None,
        "revision": (previous.get("revision", 0) + 1) if previous else 1,
        "created": previous["created"] if previous else now,
        "updated": now,
        "expected_size_mm": list(info["expected_size_mm"]),
        "min_wall_mm": info["min_wall_mm"],
        "size_mm": report["size_mm"],
        "warnings": _public_warnings(info["warnings"]),
        "compensation": info["compensation"],
        "nominal": info["nominal"],
        "printable_thread": info.get("printable_thread"),
        "validation": summary(report),
    }
    return spec


def summary(report):
    return {"status": report["status"], "errors": report["errors"], "warnings": report["warnings"],
            "triangles": report["triangles"]}


def public(spec, extra=None):
    result = {
        "model_id": spec["model_id"],
        "object_id": spec.get("object_id"),
        "part_type": spec["part_type"],
        "title": spec["title"],
        "revision": spec["revision"],
        "parameters": spec["parameters"],
        "defaults_applied": spec["defaults_applied"],
        "compensation": spec["compensation"],
        "nominal": spec["nominal"],
        "size_mm": spec["size_mm"],
        "geometry_path": spec["path"],
        "warnings": spec["warnings"],
        "validation": spec["validation"],
        "printable_thread": spec["printable_thread"],
        "units": "mm",
    }
    if extra:
        result.update(extra)
    return result


def _publish(spec, report, scene, previous_object=None):
    scene_info = {}
    result = scene.add_model(spec["path"])
    spec["object_id"] = result.get("object_id")
    if result.get("size_mm"):
        scene_info["scene_size_mm"] = result["size_mm"]
        spec["scene_size_mm"] = result["size_mm"]
    if previous_object and previous_object != spec["object_id"]:
        try:
            scene.remove_model(previous_object)
            scene_info["replaced_object_id"] = previous_object
        except Exception:
            scene_info["replaced_object_id"] = None
    return scene_info


def create(part_type, parameters, scene=None, store=None):
    scene = scene or NullScene()
    store = store or get_store()
    values, defaults, mesh, info, report = _build_and_check(part_type, parameters, scene)
    path = geometry_path(info["label"], part_type, values)
    atomic_write(path, meshbuild.stl_bytes(mesh))
    spec = _spec(part_type, parameters, values, defaults, info, path, report)
    extra = _publish(spec, report, scene)
    store.put(spec)
    return public(spec, extra)


def update(identifier, changes, scene=None, store=None):
    scene = scene or NullScene()
    store = store or get_store()
    previous = store.find(identifier)
    if previous is None:
        raise CadError("model_id", "no generated model found for '%s'. Call list_generated_models." % identifier
                       if identifier else "model_id is required when several generated models exist")
    if not isinstance(changes, dict):
        raise CadError("parameters", "must be an object")
    requested = schema.merge(previous["requested"], changes)
    part_type = previous["part_type"]
    values, defaults, mesh, info, report = _build_and_check(part_type, requested, scene)
    path = geometry_path(info["label"], part_type, values)
    atomic_write(path, meshbuild.stl_bytes(mesh))
    spec = _spec(part_type, requested, values, defaults, info, path, report, previous)
    old_object = previous.get("object_id")
    extra = _publish(spec, report, scene, old_object)
    extra["changed"] = sorted(changes.keys())
    store.put(spec)
    return public(spec, extra)


def validate(identifier, scene=None, store=None):
    scene = scene or NullScene()
    store = store or get_store()
    spec = store.find(identifier)
    if spec is None:
        raise CadError("model_id", "no generated model found. Call create_parametric_model first.")
    if not os.path.isfile(spec["path"]):
        mesh, info = parts.build(spec["part_type"], spec["parameters"])
        atomic_write(spec["path"], meshbuild.stl_bytes(mesh))
    scene_size = scene.object_size(spec.get("object_id")) if spec.get("object_id") else None
    report = validation.check_file(spec["path"], expected_size=spec["expected_size_mm"],
                                   min_wall=spec["min_wall_mm"], build_volume=scene.build_volume(),
                                   scene_size=scene_size)
    spec["validation"] = summary(report)
    spec["updated"] = time.time()
    result = public(spec)
    result["report"] = report
    result["ready_for_slicing"] = bool(report["valid"])
    return result


def export(identifier, file_format, model_name=None, store=None):
    store = store or get_store()
    if file_format not in EXPORT_FORMATS:
        raise CadError("format", "must be one of: %s" % ", ".join(EXPORT_FORMATS))
    spec = store.find(identifier)
    if spec is None:
        raise CadError("model_id", "no generated model found. Call create_parametric_model first.")
    mesh, info = parts.build(spec["part_type"], spec["parameters"])
    name = config.safe_name(model_name or spec["label"])
    folder = config.get_model_dir(name)
    path = os.path.join(folder, "%s.%s" % (config.safe_name(spec["label"]), file_format))
    if not inside(config.get_results_dir(), path):
        raise CadError("model_name", "the output path is outside the results folder")
    data = meshbuild.stl_bytes(mesh) if file_format == "stl" else meshbuild.threemf_bytes(mesh, spec["title"])
    atomic_write(path, data)
    return {"model_id": spec["model_id"], "path": path, "format": file_format, "bytes": len(data),
            "units": "mm", "triangles": len(mesh.triangles)}


def context_notes(store=None):
    store = store or get_store()
    notes = []
    for spec in store.all():
        notes.append("Сгенерированная модель проекта: model_id=%s, %s, object_id=%s. Для изменения используй "
                     "update_parametric_model; если объекта нет в сцене, предложи перестроить её из сохранённой "
                     "спецификации." % (spec["model_id"], spec["title"], spec.get("object_id") or "нет"))
    return notes


def listing(scene_objects=None, store=None):
    store = store or get_store()
    present = None if scene_objects is None else set(scene_objects)
    items = []
    for spec in store.all():
        item = public(spec)
        item["in_scene"] = None if present is None else (spec.get("object_id") in present)
        items.append(item)
    return {"models": items}
