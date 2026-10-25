from ..cad import schema, service
from ..cad.errors import CadError
from ..cad.store import get_store
from ..mcp.registry import get_registry, ToolError
from . import scene_tools
from .main_thread import run_on_main

registry = get_registry()


class SlicerScene(object):
    def add_model(self, path):
        loaded = scene_tools.load_model({"path": path}).get("loaded") or []
        if not loaded:
            raise ToolError("The generated model was not loaded into the scene")
        return {"object_id": loaded[0].get("object_id"), "size_mm": loaded[0].get("size_mm")}

    def remove_model(self, object_id):
        scene_tools.delete_object({"object_id": object_id})

    def object_size(self, object_id):
        def work():
            return scene_tools._node_info(scene_tools._find_node(object_id)).get("size_mm")
        try:
            return run_on_main(work)
        except ToolError:
            return None

    def build_volume(self):
        try:
            return run_on_main(scene_tools._build_volume)
        except Exception:
            return None

    def present_objects(self):
        return [item.get("object_id") for item in scene_tools.list_objects({}).get("objects", [])]


def _scene():
    return SlicerScene()


def _guard(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except CadError as e:
        raise ToolError(str(e))


@registry.tool("list_generatable_parts",
               "List the parts that can be generated from parameters: types, parameters with units (mm), allowed "
               "ranges, defaults and which parameters are critical (must be asked from the user, never guessed). "
               "Call it before asking the user about a part when the schema is not known yet.")
def list_generatable_parts(args):
    return service.list_parts()


@registry.tool("create_parametric_model",
               "Generate a printable model from typed parameters (no code, no paths), save its specification and "
               "load it into the scene. Returns object_id, effective parameters, defaults_applied, size_mm, "
               "geometry_path and warnings. Call validate_generated_model afterwards.",
               {"part_type": {"type": "string", "enum": schema.part_types()},
                "parameters": {"type": "object", "description": "Parameters of the part in mm, see list_generatable_parts"}},
               ["part_type", "parameters"])
def create_parametric_model(args):
    return _guard(service.create, args["part_type"], args["parameters"], _scene())


@registry.tool("update_parametric_model",
               "Change only the passed parameters of a previously generated model, rebuild it from the stored "
               "specification and replace the object in the scene (no duplicates). Also rebuilds a model whose "
               "scene object is gone, for example after reopening the project. model_id or object_id may be "
               "omitted when exactly one generated model exists.",
               {"parameters": {"type": "object", "description": "Only the parameters to change"},
                "model_id": {"type": "string", "description": "model_id or object_id of the generated model"}},
               ["parameters"])
def update_parametric_model(args):
    return _guard(service.update, args.get("model_id"), args["parameters"], _scene())


@registry.tool("validate_generated_model",
               "Check a generated model: closed manifold mesh, consistent outward normals, degenerate triangles, "
               "minimum wall thickness, size against the specification and the build volume. Errors block "
               "printing; warnings do not. Do not slice while valid is false.",
               {"model_id": {"type": "string", "description": "model_id or object_id; may be omitted for one model"}})
def validate_generated_model(args):
    return _guard(service.validate, args.get("model_id"), _scene())


@registry.tool("export_generated_model",
               "Save the geometry of a generated model alone as STL or 3MF into <results>/<model_name>/. "
               "Slicing output is saved by export_gcode and save_project_3mf.",
               {"format": {"type": "string", "enum": list(service.EXPORT_FORMATS)},
                "model_id": {"type": "string"}, "model_name": {"type": "string"}},
               ["format"])
def export_generated_model(args):
    return _guard(service.export, args.get("model_id"), args["format"], args.get("model_name"))


@registry.tool("list_generated_models",
               "List generated models stored in the project with their parameters and whether their object is "
               "still in the scene. A model that is not in the scene can be rebuilt with update_parametric_model.")
def list_generated_models(args):
    try:
        present = _scene().present_objects()
    except Exception:
        present = None
    return service.listing(present)
