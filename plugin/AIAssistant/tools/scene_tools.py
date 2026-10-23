import math
import os
import time

import numpy

from ..mcp.registry import get_registry, ToolError
from . import geometry
from .main_thread import run_on_main, wait_until

registry = get_registry()

ALLOWED_EXTENSIONS = (".stl", ".obj", ".3mf")
AXIS_PLATE_TO_UM = {"x": (1.0, 0.0, 0.0), "y": (0.0, 0.0, -1.0), "z": (0.0, 1.0, 0.0)}
AXIS_UM_TO_PLATE = {"x": "x", "y": "z", "z": "y"}


def _app():
    from steslicer.SteSlicerApplication import SteSlicerApplication
    return SteSlicerApplication.getInstance()


def um_to_plate(vec):
    return [float(vec[0]), float(-vec[2]), float(vec[1])]


def plate_to_um(vec):
    return [float(vec[0]), float(vec[2]), float(-vec[1])]


def _r(value, digits=2):
    return round(float(value), digits)


def _scene_nodes():
    from UM.Scene.Iterator.DepthFirstIterator import DepthFirstIterator
    root = _app().getController().getScene().getRoot()
    nodes = []
    for node in DepthFirstIterator(root):
        if node is root:
            continue
        if not node.callDecoration("isSliceable") and not node.callDecoration("isGroup"):
            continue
        parent = node.getParent()
        if parent is not None and parent.callDecoration("isGroup"):
            continue
        if node.getMeshData() is None and not node.callDecoration("isGroup"):
            continue
        nodes.append(node)
    return nodes


_counter = [0]


def _node_id(node):
    oid = getattr(node, "_ai_object_id", None)
    if oid is None:
        _counter[0] += 1
        oid = "obj%d" % _counter[0]
        node._ai_object_id = oid
    return oid


def _find_node(object_id):
    nodes = _scene_nodes()
    if object_id is None:
        if len(nodes) == 1:
            return nodes[0]
        raise ToolError("object_id is required when the scene has %d objects. Call list_objects." % len(nodes))
    for node in nodes:
        if _node_id(node) == object_id:
            return node
    raise ToolError("Object '%s' not found. Call list_objects." % object_id)


def _node_info(node):
    box = node.getBoundingBox()
    info = {"object_id": _node_id(node), "name": node.getName()}
    if box is None:
        return info
    center = box.center
    info["center_mm"] = {"x": _r(center.x), "y": _r(-center.z), "z": _r(center.y)}
    info["size_mm"] = {"x": _r(box.width), "y": _r(box.depth), "z": _r(box.height)}
    info["bottom_z_mm"] = _r(box.bottom)
    scale = node.getScale()
    info["scale"] = {"x": _r(scale.x, 4), "y": _r(scale.z, 4), "z": _r(scale.y, 4)}
    return info


def _collect_triangles(node):
    from UM.Scene.Iterator.DepthFirstIterator import DepthFirstIterator
    chunks = []
    for leaf in DepthFirstIterator(node):
        mesh = leaf.getMeshData()
        if mesh is None or leaf.callDecoration("isGroup"):
            continue
        vertices = leaf.getMeshDataTransformedVertices()
        indices = mesh.getIndices() if mesh.hasIndices() else None
        chunks.append(geometry.triangles_from_mesh(vertices, indices))
    if not chunks:
        raise ToolError("Object has no mesh data")
    return numpy.concatenate(chunks, axis=0) if len(chunks) > 1 else chunks[0]


def _build_volume():
    from steslicer.SteSlicerApplication import SteSlicerApplication
    stack = SteSlicerApplication.getInstance().getGlobalContainerStack()
    if stack is None:
        return None
    return {
        "width": float(stack.getProperty("machine_width", "value")),
        "depth": float(stack.getProperty("machine_depth", "value")),
        "height": float(stack.getProperty("machine_height", "value")),
        "mode": stack.getProperty("printing_mode", "value"),
    }


def _fits(size):
    volume = _build_volume()
    if volume is None:
        return None
    ok = size["x"] <= volume["width"] and size["y"] <= volume["depth"] and size["z"] <= volume["height"]
    return {"fits": bool(ok), "build_volume_mm": volume}


def _vector(x, y, z):
    from UM.Math.Vector import Vector
    return Vector(x, y, z)


def _ground(node):
    from UM.Operations.TranslateOperation import TranslateOperation
    box = node.getBoundingBox()
    if box is None:
        return
    shift = -box.bottom
    if abs(shift) > 1e-4:
        TranslateOperation(node, _vector(0, shift, 0)).push()


def _rotate_world(node, quaternion):
    from UM.Operations.SetTransformOperation import SetTransformOperation
    SetTransformOperation(node, orientation=quaternion * node.getOrientation()).push()
    _ground(node)


def _quaternion(axis, angle_rad):
    from UM.Math.Quaternion import Quaternion
    return Quaternion.fromAngleAxis(angle_rad, _vector(axis[0], axis[1], axis[2]))


def _align_to(node, from_um, to_um):
    from UM.Math.Quaternion import Quaternion
    a = numpy.asarray(from_um, dtype=float)
    b = numpy.asarray(to_um, dtype=float)
    a = a / numpy.linalg.norm(a)
    b = b / numpy.linalg.norm(b)
    quaternion = Quaternion.rotationTo(_vector(*a), _vector(*b))
    _rotate_world(node, quaternion)


def _orient_down(node, down_um):
    _align_to(node, down_um, (0.0, -1.0, 0.0))


@registry.tool("load_model",
               "Load a 3D model (STL, OBJ or 3MF) from a local path into the scene and return its object_id and size. "
               "Use the path given in the user's attachment note.",
               {"path": {"type": "string"},
                "replace": {"type": "boolean", "description": "Remove existing objects first (default false)"}},
               ["path"])
def load_model(args):
    path = args["path"]
    if not os.path.isfile(path):
        raise ToolError("File not found: %s" % path)
    if os.path.splitext(path)[1].lower() not in ALLOWED_EXTENSIONS:
        raise ToolError("Unsupported file type. Allowed: STL, OBJ, 3MF")

    def start():
        from PyQt5.QtCore import QUrl
        app = _app()
        if args.get("replace"):
            _clear_scene()
        before = set(id(n) for n in _scene_nodes())
        app.readLocalFile(QUrl.fromLocalFile(os.path.abspath(path)), True)
        return before

    before = run_on_main(start, _timeout=60)

    def appeared():
        fresh = [n for n in _scene_nodes() if id(n) not in before]
        return fresh or None

    fresh = wait_until(appeared, 180)
    if not fresh:
        raise ToolError("Model was not loaded within the timeout. Check the file and the slicer log.")
    time.sleep(0.5)

    def info():
        return {"loaded": [_node_info(n) for n in fresh]}
    return run_on_main(info)


@registry.tool("list_objects", "List all printable objects in the scene with position, size and scale (mm, plate coordinates: x right, y back, z up).")
def list_objects(args):
    def work():
        return {"objects": [_node_info(n) for n in _scene_nodes()]}
    return run_on_main(work)


@registry.tool("get_object_bounds", "Return size and position of an object in mm and whether it fits the build volume.",
               {"object_id": {"type": "string"}})
def get_object_bounds(args):
    def work():
        info = _node_info(_find_node(args.get("object_id")))
        info.update(_fits(info["size_mm"]) or {})
        return info
    return run_on_main(work)


@registry.tool("analyze_mesh",
               "Analyze the geometry of an object in its current orientation: size, volume, mean wall thickness, share of overhangs above 45 degrees, "
               "base contact area and rotational symmetry (axis, diameter, length, aspect = length/diameter, bore). "
               "Use it to decide between 3D and 5D printing.",
               {"object_id": {"type": "string"}})
def analyze_mesh(args):
    def gather():
        node = _find_node(args.get("object_id"))
        return _node_id(node), _collect_triangles(node), _node_info(node)

    object_id, tris, info = run_on_main(gather, _timeout=60)
    result = geometry.analyze(tris)
    sym = result.get("axisymmetry")
    if sym:
        sym["axis"] = AXIS_UM_TO_PLATE[sym["axis"]]
        sym.pop("axis_index", None)
        sym.pop("center", None)
    result["object_id"] = object_id
    result["size_mm"] = dict(zip(("x", "y", "z"), [info["size_mm"]["x"], info["size_mm"]["y"], info["size_mm"]["z"]]))
    result["fit"] = run_on_main(lambda: _fits(result["size_mm"]))
    return result


@registry.tool("suggest_orientation",
               "Evaluate candidate orientations (6 axis directions and the largest flat faces) and return the top 3 with height, base area and overhang share. "
               "goal: no_supports (min overhangs), stability (max base area), fast (min height), balanced. "
               "With apply=true the best one is applied and the object is placed on the plate.",
               {"object_id": {"type": "string"},
                "goal": {"type": "string", "enum": ["no_supports", "stability", "fast", "balanced"]},
                "apply": {"type": "boolean"}})
def suggest_orientation(args):
    goal = args.get("goal") or "balanced"

    def gather():
        node = _find_node(args.get("object_id"))
        return _node_id(node), _collect_triangles(node)

    object_id, tris = run_on_main(gather, _timeout=60)
    top = geometry.suggest_orientations(tris, goal)
    out = []
    for item in top:
        vec_um = item.pop("down_vector")
        item["down_vector_plate"] = [_r(v, 4) for v in um_to_plate(vec_um)]
        item["_um"] = vec_um
        out.append(item)
    applied = False
    if args.get("apply") and out:
        best = out[0]["_um"]

        def work():
            node = _find_node(object_id)
            _orient_down(node, best)
            return _node_info(node)
        info = run_on_main(work)
        applied = True
        for item in out:
            item.pop("_um", None)
        return {"object_id": object_id, "goal": goal, "candidates": out, "applied": applied, "result": info}
    for item in out:
        item.pop("_um", None)
    return {"object_id": object_id, "goal": goal, "candidates": out, "applied": applied}


@registry.tool("set_orientation",
               "Orient the object so that the given direction (in current plate coordinates) faces the build plate. "
               "down_vector is [x, y, z]; z is up. Example: [0,0,-1] keeps it unchanged, [0,0,1] flips it upside down.",
               {"object_id": {"type": "string"},
                "down_vector": {"type": "array", "items": {"type": "number"}}}, ["down_vector"])
def set_orientation(args):
    vec = args["down_vector"]
    if len(vec) != 3 or not any(abs(v) > 1e-9 for v in vec):
        raise ToolError("down_vector must be three numbers, not all zero")
    down_um = plate_to_um(vec)

    def work():
        node = _find_node(args.get("object_id"))
        _align_to(node, down_um, (0.0, -1.0, 0.0))
        return _node_info(node)
    return run_on_main(work)


@registry.tool("lay_flat", "Lay the object on its largest flat face (maximum base area).", {"object_id": {"type": "string"}})
def lay_flat(args):
    def gather():
        node = _find_node(args.get("object_id"))
        return _node_id(node), _collect_triangles(node)

    object_id, tris = run_on_main(gather, _timeout=60)
    best = geometry.suggest_orientations(tris, "stability", top=1)[0]
    vec = best["down_vector"]

    def work():
        node = _find_node(object_id)
        _orient_down(node, vec)
        return _node_info(node)
    result = run_on_main(work)
    result["base_area_mm2"] = best["base_area_mm2"]
    return result


@registry.tool("align_symmetry_axis",
               "For 5D printing: rotate the object so that its axis of rotational symmetry is vertical (z) and put it on the plate.",
               {"object_id": {"type": "string"}})
def align_symmetry_axis(args):
    def gather():
        node = _find_node(args.get("object_id"))
        return _node_id(node), _collect_triangles(node)

    object_id, tris = run_on_main(gather, _timeout=60)
    sym = geometry.axisymmetry(tris)
    if not sym:
        raise ToolError("Cannot determine symmetry axis")
    axis_vec = [0.0, 0.0, 0.0]
    axis_vec[sym["axis_index"]] = 1.0

    def work():
        node = _find_node(object_id)
        _align_to(node, axis_vec, (0.0, 1.0, 0.0))
        return _node_info(node)
    result = run_on_main(work)
    result["symmetry"] = {"axis_before": AXIS_UM_TO_PLATE["xyz"[sym["axis_index"]]],
                          "symmetry_error": sym["symmetry_error"], "is_axisymmetric": sym["is_axisymmetric"]}
    return result


@registry.tool("rotate_object", "Rotate the object around a plate axis (x, y or z=vertical) by angle in degrees, then put it on the plate.",
               {"object_id": {"type": "string"}, "axis": {"type": "string", "enum": ["x", "y", "z"]},
                "angle_deg": {"type": "number"}}, ["axis", "angle_deg"])
def rotate_object(args):
    axis = AXIS_PLATE_TO_UM[args["axis"]]
    angle = math.radians(float(args["angle_deg"]))

    def work():
        node = _find_node(args.get("object_id"))
        _rotate_world(node, _quaternion(axis, angle))
        return _node_info(node)
    return run_on_main(work)


@registry.tool("move_object",
               "Move the object so that its bounding box center is at x, y (mm on the plate, origin at the plate center). "
               "z is the height of the bottom above the plate (default 0). Omitted coordinates stay unchanged.",
               {"object_id": {"type": "string"}, "x": {"type": "number"}, "y": {"type": "number"}, "z": {"type": "number"}})
def move_object(args):
    def work():
        from UM.Operations.TranslateOperation import TranslateOperation
        node = _find_node(args.get("object_id"))
        box = node.getBoundingBox()
        dx = (args["x"] - box.center.x) if "x" in args else 0.0
        dz = (-args["y"] - box.center.z) if "y" in args else 0.0
        target_bottom = args.get("z", 0.0)
        dy = target_bottom - box.bottom
        TranslateOperation(node, _vector(dx, dy, dz)).push()
        return _node_info(node)
    return run_on_main(work)


@registry.tool("scale_object",
               "Scale the object: factor multiplies all dimensions, or give x, y, z factors separately. Result is put on the plate.",
               {"object_id": {"type": "string"}, "factor": {"type": "number"},
                "x": {"type": "number"}, "y": {"type": "number"}, "z": {"type": "number"}})
def scale_object(args):
    fx = args.get("x", args.get("factor", 1.0))
    fy = args.get("y", args.get("factor", 1.0))
    fz = args.get("z", args.get("factor", 1.0))
    for f in (fx, fy, fz):
        if f <= 0:
            raise ToolError("Scale factors must be positive")

    def work():
        from UM.Operations.SetTransformOperation import SetTransformOperation
        node = _find_node(args.get("object_id"))
        cur = node.getScale()
        SetTransformOperation(node, scale=_vector(cur.x * fx, cur.y * fz, cur.z * fy)).push()
        _ground(node)
        info = _node_info(node)
        info.update(_fits(info["size_mm"]) or {})
        return info
    return run_on_main(work)


@registry.tool("arrange_all", "Automatically arrange all objects on the build plate (use for several objects in 3D mode).")
def arrange_all(args):
    def start():
        _app().arrangeAll()
        return [n.getBoundingBox().center.x for n in _scene_nodes()]

    previous = run_on_main(start)
    for _ in range(20):
        time.sleep(0.4)
        current = run_on_main(lambda: [n.getBoundingBox().center.x for n in _scene_nodes()])
        if current == previous:
            break
        previous = current
    return {"objects": run_on_main(lambda: [_node_info(n) for n in _scene_nodes()])}


def _clear_scene():
    from UM.Operations.GroupedOperation import GroupedOperation
    from UM.Operations.RemoveSceneNodeOperation import RemoveSceneNodeOperation
    op = GroupedOperation()
    nodes = _scene_nodes()
    for node in nodes:
        op.addOperation(RemoveSceneNodeOperation(node))
    op.push()
    return len(nodes)


@registry.tool("delete_object", "Remove one object from the scene.", {"object_id": {"type": "string"}}, ["object_id"])
def delete_object(args):
    def work():
        from UM.Operations.RemoveSceneNodeOperation import RemoveSceneNodeOperation
        node = _find_node(args["object_id"])
        RemoveSceneNodeOperation(node).push()
        return {"removed": args["object_id"]}
    return run_on_main(work)


@registry.tool("clear_scene", "Remove all objects from the scene.")
def clear_scene(args):
    return {"removed": run_on_main(_clear_scene)}
