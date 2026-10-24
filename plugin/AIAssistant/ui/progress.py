STAGES = (
    ("prepare", 0.00, 0.08),
    ("scene", 0.08, 0.20),
    ("geometry", 0.20, 0.38),
    ("recommend", 0.38, 0.55),
    ("settings", 0.55, 0.70),
    ("orientation", 0.70, 0.78),
    ("slicing", 0.78, 0.95),
    ("export", 0.95, 0.98),
    ("answer", 0.98, 1.00),
)

STAGE_ORDER = tuple(name for name, _, _ in STAGES)
STAGE_RANGES = dict((name, (low, high)) for name, low, high in STAGES)

TOOL_STAGES = {
    "get_changed_settings": "prepare",
    "reset_settings": "prepare",
    "get_machine": "prepare",
    "select_machine": "prepare",
    "load_model": "scene",
    "list_objects": "scene",
    "delete_object": "scene",
    "clear_scene": "scene",
    "analyze_mesh": "geometry",
    "get_object_bounds": "geometry",
    "recommend_setup": "recommend",
    "list_materials": "recommend",
    "set_material": "recommend",
    "list_quality_profiles": "recommend",
    "set_quality_profile": "recommend",
    "get_print_mode": "recommend",
    "set_print_mode": "recommend",
    "get_setting": "settings",
    "search_settings": "settings",
    "set_setting": "settings",
    "set_settings": "settings",
    "create_profile": "settings",
    "suggest_orientation": "orientation",
    "set_orientation": "orientation",
    "lay_flat": "orientation",
    "align_symmetry_axis": "orientation",
    "rotate_object": "orientation",
    "move_object": "orientation",
    "scale_object": "orientation",
    "arrange_all": "orientation",
    "slice": "slicing",
    "get_slice_status": "slicing",
    "get_slice_result": "slicing",
    "export_gcode": "export",
    "save_project_3mf": "export",
}

STEP_SHARE = 0.45
STAGE_CAP = 0.85
RUNNING_CAP = 0.99
SLICE_START = STAGE_RANGES["slicing"][0]
SLICE_SPAN = STAGE_RANGES["slicing"][1] - SLICE_START


def stage_for_tool(name):
    return TOOL_STAGES.get(name)


def _clamp(value):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, value))


class ProgressTracker(object):
    def __init__(self):
        self.reset()

    def reset(self):
        self.state = "idle"
        self.value = 0.0
        self.stage = None
        self._completed = {}

    @property
    def known(self):
        return self.stage is not None

    @property
    def indeterminate(self):
        return self.state == "running" and not self.known

    @property
    def percent(self):
        if self.state == "done":
            return 100
        return min(99, int(self.value * 100 + 1e-6))

    def start(self):
        self.reset()
        self.state = "running"

    def _raise(self, value):
        if self.state != "running":
            return
        self.value = max(self.value, min(RUNNING_CAP, value))

    def _enter(self, stage):
        if self.state != "running" or stage not in STAGE_RANGES:
            return
        self.stage = stage
        self._raise(STAGE_RANGES[stage][0])

    def tool_started(self, name):
        stage = stage_for_tool(name)
        if stage is not None:
            self._enter(stage)

    def tool_finished(self, name, ok=True):
        stage = stage_for_tool(name)
        if stage is None or self.state != "running":
            return
        self._enter(stage)
        count = self._completed.get(stage, 0) + (1 if ok else 0.5)
        self._completed[stage] = count
        low, high = STAGE_RANGES[stage]
        share = min(STAGE_CAP, 1.0 - (1.0 - STEP_SHARE) ** count)
        self._raise(low + (high - low) * share)

    def slice_progress(self, fraction):
        if self.state != "running":
            return
        self._enter("slicing")
        self._raise(SLICE_START + SLICE_SPAN * _clamp(fraction))

    def answer(self):
        self._enter("answer")

    def done(self):
        if self.state == "running":
            self.state = "done"
            self.value = 1.0

    def fail(self):
        if self.state in ("running", "idle"):
            self.state = "error"

    def cancel(self):
        if self.state in ("running", "idle"):
            self.state = "cancelled"

    def snapshot(self):
        return {"state": self.state, "value": self.value, "percent": self.percent, "stage": self.stage or "",
                "indeterminate": self.indeterminate}
