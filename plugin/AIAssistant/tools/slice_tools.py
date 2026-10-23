import io
import os
import threading
import time

from .. import config
from ..mcp.registry import get_registry, ToolError
from ..server.events import get_bus
from .main_thread import run_on_main

registry = get_registry()

SLICE_TIMEOUT = 240

STATE_NAMES = {1: "not_started", 2: "processing", 3: "done", 4: "error", 5: "disabled"}


def _app():
    from steslicer.SteSlicerApplication import SteSlicerApplication
    return SteSlicerApplication.getInstance()


class SliceMonitor(object):
    def __init__(self):
        self.state = 1
        self.result = None
        self.progress = 0.0
        self.finished = threading.Event()
        self.connected = set()
        self._wrappers = []
        self.lock = threading.Lock()

    def reset(self):
        with self.lock:
            self.state = 2
            self.result = None
            self.progress = 0.0
            self.finished.clear()

    def on_state(self, state):
        with self.lock:
            self.state = int(state)
            if self.state in (3, 4):
                self.result = self.state
                self.finished.set()
            elif self.state == 2 and self.finished.is_set():
                self.result = None
                self.finished.clear()
            elif self.state == 1 and self.result == 3:
                self.result = None
        get_bus().publish("status", {"text": "slice_state", "state": STATE_NAMES.get(int(state), str(state))})

    def on_progress(self, progress):
        with self.lock:
            self.progress = float(progress)
        get_bus().publish("slice_progress", {"state": "slicing", "progress": float(progress),
                                             "percent": int(round(float(progress) * 100))})

    def _guard(self, backend, handler):
        def wrapper(value):
            if _app().getBackend() is backend:
                handler(value)
        self._wrappers.append(wrapper)
        return wrapper

    def attach(self):
        backends = _app().getBackendManager().getBackends()
        for backend_id, backend in backends.items():
            if backend_id in self.connected:
                continue
            backend.backendStateChange.connect(self._guard(backend, self.on_state))
            backend.processingProgress.connect(self._guard(backend, self.on_progress))
            self.connected.add(backend_id)


_monitor = SliceMonitor()


def _print_info():
    info = _app().getPrintInformation()
    seconds = int(info.currentPrintTime)
    weights = [float(w) for w in info.materialWeights]
    lengths = [float(l) for l in info.materialLengths]
    names = [str(n) for n in info.materialNames]
    return {
        "print_time_s": seconds,
        "print_time": "%dh %02dm" % (seconds // 3600, (seconds % 3600) // 60),
        "material_g": round(sum(weights), 2),
        "material_m": round(sum(lengths), 2),
        "materials": names,
    }


def _start_slice():
    app = _app()
    if not [1 for _ in _objects()]:
        raise ToolError("Scene is empty. Load a model first.")
    mm = app.getMachineManager()
    if mm.stacksHaveErrors:
        raise ToolError("Current settings contain validation errors; fix them before slicing")
    _monitor.attach()
    _monitor.reset()
    backend = app.getBackend()
    backend.forceSlice()
    return True


def _objects():
    from UM.Scene.Iterator.DepthFirstIterator import DepthFirstIterator
    root = _app().getController().getScene().getRoot()
    for node in DepthFirstIterator(root):
        if node.callDecoration("isSliceable") and node.getMeshData() is not None:
            yield node


@registry.tool("slice",
               "Start slicing the scene and wait for completion (up to 4 minutes). Returns print time and material use. "
               "Call after the model is placed and all settings are applied.")
def slice_scene(args):
    run_on_main(_start_slice, _timeout=60)
    get_bus().publish("status", {"text": "slicing"})
    if not _monitor.finished.wait(SLICE_TIMEOUT):
        raise ToolError("Slicing did not finish within %d s (progress %d%%)" % (SLICE_TIMEOUT, int(_monitor.progress * 100)))
    if _monitor.result == 4:
        raise ToolError("Slicing failed. Check that the model fits the build volume and settings are valid; see the slicer log.")
    deadline = time.time() + 8
    result = run_on_main(_print_info)
    while result["print_time_s"] == 0 and time.time() < deadline:
        time.sleep(0.5)
        result = run_on_main(_print_info)
    get_bus().publish("slice_done", {"print_time": result["print_time"], "material_g": result["material_g"],
                                     "material_m": result["material_m"]})
    return result


@registry.tool("get_slice_status", "Return the slicing state (not_started, processing, done, error) and progress percent.")
def get_slice_status(args):
    return {"state": STATE_NAMES.get(_monitor.state, str(_monitor.state)), "percent": int(_monitor.progress * 100)}


@registry.tool("get_slice_result", "Return print time and material use of the last slicing.")
def get_slice_result(args):
    if _monitor.result != 3:
        raise ToolError("No finished slicing. Call slice first.")
    return run_on_main(_print_info)


def _default_model_name():
    names = [n.getName() for n in _objects()]
    if not names:
        return "model"
    return os.path.splitext(names[0])[0]


def _write_gcode(path):
    from UM.PluginRegistry import PluginRegistry
    app = _app()
    writer = app.getMeshFileHandler().getWriter("GCodeWriter")
    if writer is None:
        writer = PluginRegistry.getInstance().getPluginObject("GCodeWriter")
    if writer is None:
        raise ToolError("G-code writer is not available")
    stream = io.StringIO()
    if not writer.write(stream, None):
        raise ToolError("G-code export failed: %s" % writer.getInformation())
    text = stream.getvalue()
    with io.open(path, "w", encoding="utf-8", newline="") as handle:
        handle.write(text)
    return len(text)


@registry.tool("export_gcode",
               "Save the G-code of the last slicing to <results>/<model_name>/result.gcode. model_name defaults to the loaded file name.",
               {"model_name": {"type": "string"}})
def export_gcode(args):
    if _monitor.result != 3:
        raise ToolError("Slice the model first")

    def work():
        name = args.get("model_name") or _default_model_name()
        path = os.path.join(config.get_model_dir(name), "result.gcode")
        size = _write_gcode(path)
        return {"path": path, "bytes": size, "model_name": name}
    return run_on_main(work, _timeout=120)


def _write_project(path):
    app = _app()
    writer = app.getWorkspaceFileHandler().getWriter("3MFWriter")
    if writer is None:
        raise ToolError("3MF project writer is not available")
    root = app.getController().getScene().getRoot()
    stream = io.BytesIO()
    if not writer.write(stream, [root]):
        raise ToolError("Project export failed")
    data = stream.getvalue()
    with open(path, "wb") as handle:
        handle.write(data)
    return len(data)


@registry.tool("save_project_3mf",
               "Save the whole project (models with transforms, printer, material, profile and all setting changes) to <results>/<model_name>/project.3mf.",
               {"model_name": {"type": "string"}})
def save_project_3mf(args):
    def work():
        name = args.get("model_name") or _default_model_name()
        path = os.path.join(config.get_model_dir(name), "project.3mf")
        size = _write_project(path)
        return {"path": path, "bytes": size, "model_name": name}
    return run_on_main(work, _timeout=120)
