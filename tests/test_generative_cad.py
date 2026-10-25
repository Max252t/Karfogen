import json
import math
import os
import random
import tempfile
import unittest
import zipfile

import support
from AIAssistant import config
from AIAssistant.agent import prompts
from AIAssistant.cad import meshbuild, parts, schema, service, threads, validation
from AIAssistant.cad.errors import CadError
from AIAssistant.cad.store import ModelStore, get_store
from AIAssistant.mcp import protocol
from AIAssistant.mcp.registry import ToolError, get_registry, run_guarded
from AIAssistant.server import projects
from AIAssistant.server.events import EventBus
from AIAssistant.tools import cad_tools
from AIAssistant.ui import view_state

BOLT = {"thread_size": "M8", "length_mm": 30, "head_type": "hex"}
PLATE = {"width_mm": 60, "depth_mm": 40, "thickness_mm": 4,
         "holes": [{"x_mm": -20, "y_mm": 0, "diameter_mm": 5}, {"x_mm": 20, "y_mm": 0, "diameter_mm": 5},
                   {"x_mm": 0, "y_mm": 10, "diameter_mm": 8}]}
BRACKET = {"length_mm": 40, "height_mm": 30, "width_mm": 20, "hole_diameter_mm": 4.5, "holes_per_leg": 2}
VALID = [("bolt", BOLT), ("nut", {"thread_size": "M8"}), ("washer", {"thread_size": "M8"}), ("plate", PLATE),
         ("bracket", BRACKET)]


class FakeScene(object):
    def __init__(self, volume=None):
        self.objects = {}
        self.counter = 0
        self.volume = volume or {"width": 300.0, "depth": 300.0, "height": 400.0}

    def add_model(self, path):
        with open(path, "rb") as handle:
            mesh = meshbuild.read_stl(handle.read())
        self.counter += 1
        object_id = "obj%d" % self.counter
        size = dict(zip("xyz", mesh.size()))
        self.objects[object_id] = size
        return {"object_id": object_id, "size_mm": size}

    def remove_model(self, object_id):
        del self.objects[object_id]

    def object_size(self, object_id):
        return self.objects.get(object_id)

    def build_volume(self):
        return self.volume


class CadTestCase(unittest.TestCase):
    def setUp(self):
        config.set_value("results_dir", tempfile.mkdtemp())
        config.set_value("language", "ru")
        self.store = ModelStore()
        self.scene = FakeScene()

    def create(self, part_type, params, scene=None):
        return service.create(part_type, params, scene or self.scene, self.store)

    def mesh_of(self, result):
        with open(result["geometry_path"], "rb") as handle:
            return meshbuild.read_stl(handle.read())


class ListPartsTest(CadTestCase):
    def test_all_parts_are_described(self):
        listing = service.list_parts()
        self.assertEqual(listing["units"], "mm")
        names = [p["part_type"] for p in listing["parts"]]
        self.assertEqual(names, ["bolt", "nut", "washer", "plate", "bracket"])
        for part in listing["parts"]:
            for param in part["parameters"]:
                self.assertIn("unit", param)
                self.assertIn("critical", param)
                self.assertIn("default", param)

    def test_bolt_schema_marks_critical_parameters(self):
        bolt = [p for p in service.list_parts()["parts"] if p["part_type"] == "bolt"][0]
        critical = sorted(p["name"] for p in bolt["parameters"] if p["critical"])
        self.assertEqual(critical, ["head_type", "length_mm", "thread_size"])
        by_name = dict((p["name"], p) for p in bolt["parameters"])
        self.assertEqual(by_name["length_mm"]["min"], 2.0)
        self.assertEqual(by_name["length_mm"]["max"], 200.0)
        self.assertEqual(by_name["clearance_mm"]["default"], 0.1)
        self.assertIn("M8", by_name["thread_size"]["enum"])
        sizes = dict((s["thread_size"], s["pitches_mm"]) for s in bolt["thread_sizes"])
        self.assertEqual(sizes["M8"], [1.25, 1.0])

    def test_tool_returns_the_same_listing(self):
        result = get_registry().call("list_generatable_parts", {})
        self.assertEqual([p["part_type"] for p in result["parts"]], schema.part_types())


class RejectionTest(CadTestCase):
    def reject(self, part_type, params, field):
        with self.assertRaises(CadError) as caught:
            self.create(part_type, params)
        self.assertEqual(caught.exception.field, field)
        self.assertEqual(self.scene.objects, {})
        return str(caught.exception)

    def test_unknown_type(self):
        self.reject("gear", {}, "part_type")

    def test_missing_critical_parameter(self):
        message = self.reject("bolt", {"thread_size": "M8", "head_type": "hex"}, "length_mm")
        self.assertIn("ask the user", message)
        self.reject("bolt", {"length_mm": 30, "head_type": "hex"}, "thread_size")
        self.reject("bracket", {"length_mm": 40, "height_mm": 30, "width_mm": 20}, "hole_diameter_mm")

    def test_string_instead_of_number(self):
        self.reject("bolt", dict(BOLT, length_mm="30"), "length_mm")
        self.reject("bolt", dict(BOLT, length_mm=True), "length_mm")

    def test_nan_and_infinity(self):
        self.reject("bolt", dict(BOLT, length_mm=float("nan")), "length_mm")
        self.reject("bolt", dict(BOLT, length_mm=float("inf")), "length_mm")
        self.reject("plate", dict(PLATE, thickness_mm=float("-inf")), "thickness_mm")

    def test_negative_and_out_of_range(self):
        self.reject("bolt", dict(BOLT, length_mm=-5), "length_mm")
        self.reject("bolt", dict(BOLT, length_mm=0), "length_mm")
        self.reject("bolt", dict(BOLT, length_mm=500), "length_mm")
        self.reject("bolt", dict(BOLT, clearance_mm=0.9), "clearance_mm")
        self.reject("plate", dict(PLATE, width_mm=1), "width_mm")

    def test_bad_enum_and_pitch(self):
        self.reject("bolt", dict(BOLT, head_type="round"), "head_type")
        self.reject("bolt", dict(BOLT, thread_size="M7"), "thread_size")
        self.reject("bolt", dict(BOLT, pitch_mm=1.5), "pitch_mm")
        self.reject("bolt", dict(BOLT, thread_mode="drawn"), "thread_mode")

    def test_unknown_parameter_is_rejected(self):
        self.reject("bolt", dict(BOLT, script="import os"), "parameters.script")
        self.reject("bolt", dict(BOLT, path="C:/Windows/x.stl"), "parameters.path")

    def test_parameters_must_be_an_object(self):
        self.reject("bolt", "M8", "parameters")
        self.reject("bolt", [1, 2], "parameters")

    def test_thread_length_cannot_exceed_length(self):
        self.reject("bolt", dict(BOLT, thread_length_mm=40), "thread_length_mm")

    def test_hole_checks(self):
        self.reject("plate", dict(PLATE, holes=[{"x_mm": 29, "y_mm": 0, "diameter_mm": 5}]), "holes[0]")
        self.reject("plate", dict(PLATE, holes=[{"x_mm": 0, "y_mm": 0, "diameter_mm": 5},
                                                {"x_mm": 4, "y_mm": 0, "diameter_mm": 5}]), "holes[1]")
        self.reject("plate", dict(PLATE, holes=[{"x_mm": 0, "y_mm": 0}]), "holes[0].diameter_mm")
        self.reject("plate", dict(PLATE, holes=[{"x_mm": 0, "y_mm": 0, "diameter_mm": "5"}]),
                    "holes[0].diameter_mm")
        self.reject("plate", dict(PLATE, holes=[{"x_mm": 0, "y_mm": 0, "diameter_mm": 5, "z": 1}]), "holes[0]")
        self.reject("plate", dict(PLATE, holes="many"), "holes")

    def test_too_many_triangles(self):
        self.reject("bolt", {"thread_size": "M3", "length_mm": 200, "head_type": "hex"}, "length_mm")

    def test_bracket_holes_must_fit(self):
        self.reject("bracket", dict(BRACKET, holes_per_leg=4, length_mm=20), "holes_per_leg")
        self.reject("bracket", dict(BRACKET, hole_diameter_mm=19), "hole_diameter_mm")


class MeshQualityTest(CadTestCase):
    def assert_valid_mesh(self, mesh):
        report = validation.check(mesh.welded())
        self.assertEqual(report["errors"], [])
        self.assertTrue(report["checks"]["closed"])
        self.assertTrue(report["checks"]["consistent_normals"])
        self.assertEqual(report["checks"]["degenerate_triangles"], 0)
        self.assertGreater(report["checks"]["volume_mm3"], 0)

    def test_every_part_creates_a_valid_object(self):
        for part_type, params in VALID:
            result = self.create(part_type, params)
            self.assertEqual(result["part_type"], part_type)
            self.assertTrue(result["object_id"])
            self.assertEqual(result["validation"]["status"], "ok", part_type)
            self.assertTrue(os.path.isfile(result["geometry_path"]))
            self.assertEqual(result["units"], "mm")
            self.assert_valid_mesh(self.mesh_of(result))
        self.assertEqual(len(self.scene.objects), 5)

    def test_metric_bolt_dimensions(self):
        result = self.create("bolt", BOLT)
        size = result["size_mm"]
        self.assertAlmostEqual(size["x"], 13.0, places=2)
        self.assertAlmostEqual(size["y"], 13.0 * 2 / math.sqrt(3), places=2)
        self.assertAlmostEqual(size["z"], 5.3 + 30.0, places=2)
        self.assertEqual(result["parameters"]["pitch_mm"], 1.25)
        self.assertIn("pitch_mm", result["defaults_applied"])
        self.assertGreater(result["validation"]["triangles"], 30000)
        self.assert_valid_mesh(self.mesh_of(result))

    def test_bolt_thread_diameter_follows_nominal_and_clearance(self):
        mesh = self.mesh_of(self.create("bolt", dict(BOLT, clearance_mm=0.2)))
        shaft = [v for v in mesh.vertices if v[2] > 10.0]
        radius = max(math.hypot(v[0], v[1]) for v in shaft)
        self.assertAlmostEqual(radius, 4.0 - 0.2, places=2)
        low = min(math.hypot(v[0], v[1]) for v in shaft if v[2] < 33.0)
        self.assertAlmostEqual(low, 4.0 - 0.2 - threads.thread_depth(1.25), places=2)

    def test_head_types(self):
        for head in ("hex", "cylindrical", "countersunk"):
            result = self.create("bolt", dict(BOLT, length_mm=16, head_type=head))
            self.assertEqual(result["validation"]["status"], head and "ok")
            self.assert_valid_mesh(self.mesh_of(result))

    def test_partial_thread_and_fine_pitch(self):
        result = self.create("bolt", dict(BOLT, thread_length_mm=12, pitch_mm=1.0))
        self.assertEqual(result["parameters"]["pitch_mm"], 1.0)
        self.assert_valid_mesh(self.mesh_of(result))

    def test_cosmetic_thread_is_replaced_with_a_warning(self):
        result = self.create("bolt", dict(BOLT, thread_mode="cosmetic"))
        self.assertFalse(result["printable_thread"])
        self.assertIn("cosmetic_thread_replaced", [w["code"] for w in result["warnings"]])
        self.assertLess(result["validation"]["triangles"], 2000)
        self.assert_valid_mesh(self.mesh_of(result))
        nut = self.create("nut", {"thread_size": "M8", "thread_mode": "cosmetic"})
        self.assertIn("cosmetic_thread_replaced", [w["code"] for w in nut["warnings"]])
        self.assert_valid_mesh(self.mesh_of(nut))

    def test_nut_matches_bolt_with_separate_clearance(self):
        bolt = self.create("bolt", dict(BOLT, clearance_mm=0.1))
        nut = self.create("nut", {"thread_size": "M8", "clearance_mm": 0.25})
        self.assertEqual(bolt["parameters"]["pitch_mm"], nut["parameters"]["pitch_mm"])
        self.assertEqual(bolt["nominal"]["diameter_mm"], nut["nominal"]["diameter_mm"])
        self.assertEqual(bolt["compensation"]["clearance_mm"], 0.1)
        self.assertEqual(nut["compensation"]["clearance_mm"], 0.25)
        for phase in (0.0, 0.1, 0.3, 0.55, 0.8):
            outer = threads.thread_radius(phase, 4.0, 1.25) + 0.25
            inner = threads.thread_radius(phase, 4.0, 1.25) - 0.1
            self.assertAlmostEqual(outer - inner, 0.35, places=9)
        mesh = self.mesh_of(nut)
        bore = [math.hypot(v[0], v[1]) for v in mesh.vertices if math.hypot(v[0], v[1]) < 5.0]
        self.assertAlmostEqual(max(bore), 4.0 + 0.25 + 0.4, places=1)
        self.assertGreater(min(bore), 4.0 - threads.thread_depth(1.25))
        self.assertAlmostEqual(nut["size_mm"]["z"], 6.8, places=2)
        self.assert_valid_mesh(mesh)

    def test_threads_are_right_handed(self):
        for phase in (0.0, 0.05, 0.4, 0.7):
            self.assertAlmostEqual(threads.profile(phase), threads.profile(phase + 3), places=9)
        mesh = self.mesh_of(self.create("bolt", dict(BOLT, length_mm=20)))
        crest = [v for v in mesh.vertices if v[2] > 10 and abs(math.hypot(v[0], v[1]) - 3.9) < 1e-3]
        by_angle = {}
        for x, y, z in crest:
            angle = round(math.degrees(math.atan2(y, x))) % 360
            by_angle.setdefault(angle, []).append(z)
        low = min(by_angle[0])
        height_at = {}
        for angle in (0, 90, 180, 270):
            zs = [z for z in by_angle.get(angle, []) if z > 12]
            height_at[angle] = min(zs) % 1.25
        step = (height_at[90] - height_at[0]) % 1.25
        self.assertAlmostEqual(step, 1.25 / 4.0, places=1)
        self.assertGreaterEqual(low, 0)

    def test_washer_plate_and_bracket_sizes(self):
        washer = self.create("washer", {"thread_size": "M8"})
        self.assertEqual([round(washer["size_mm"][k], 2) for k in "xyz"], [16.0, 16.0, 1.6])
        plate = self.create("plate", PLATE)
        self.assertEqual([round(plate["size_mm"][k], 2) for k in "xyz"], [60.0, 40.0, 4.0])
        bracket = self.create("bracket", BRACKET)
        self.assertEqual([round(bracket["size_mm"][k], 2) for k in "xyz"], [40.0, 20.0, 30.0])

    def test_plate_hole_volume(self):
        result = self.create("plate", PLATE)
        volume = result["validation"]
        mesh = self.mesh_of(result)
        stats = validation.analyze(mesh.welded())
        holes = sum(math.pi * (d + 0.2) ** 2 / 4.0 for d in (5, 5, 8)) * 4.0
        self.assertAlmostEqual(stats["volume"], 60 * 40 * 4 - holes, delta=60)
        self.assertEqual(volume["status"], "ok")

    def test_bracket_volume_without_holes_is_exact(self):
        result = self.create("bracket", dict(BRACKET, hole_diameter_mm=0))
        stats = validation.analyze(self.mesh_of(result).welded())
        self.assertAlmostEqual(stats["volume"], 36 * 20 * 4 + 20 * 26 * 4 + 4 * 20 * 4, places=1)

    def test_triangulation_of_random_holes(self):
        rng = random.Random(7)
        for trial in range(25):
            holes = []
            for _ in range(rng.randint(1, 8)):
                x = rng.uniform(-45, 45)
                y = rng.uniform(-25, 25)
                r = rng.uniform(1.0, 4.0)
                if all(math.hypot(x - hx, y - hy) > r + hr + 1.5 for hx, hy, hr in holes):
                    holes.append((x, y, r))
            outer = meshbuild.rectangle(-50, -30, 50, 30)
            polygons = [meshbuild.circle_polygon(x, y, r) for x, y, r in holes]
            mesh = meshbuild.prism(outer, polygons, 0.0, 3.0, lambda u, v, w: (u, v, w)).welded()
            report = validation.check(mesh)
            self.assertEqual(report["errors"], [], "trial %d" % trial)

    def test_aligned_holes_triangulate(self):
        holes = [(x, y, 2.0) for x in (-30, -10, 10, 30) for y in (-15, 0, 15)]
        outer = meshbuild.rectangle(-50, -30, 50, 30)
        polygons = [meshbuild.circle_polygon(x, y, r) for x, y, r in holes]
        mesh = meshbuild.prism(outer, polygons, 0.0, 3.0, lambda u, v, w: (u, v, w)).welded()
        self.assertEqual(validation.check(mesh)["errors"], [])

    def test_generation_is_deterministic(self):
        first = self.create("bolt", BOLT)
        with open(first["geometry_path"], "rb") as handle:
            first_bytes = handle.read()
        second = self.create("bolt", BOLT)
        self.assertEqual(first["geometry_path"], second["geometry_path"])
        with open(second["geometry_path"], "rb") as handle:
            self.assertEqual(handle.read(), first_bytes)

    def test_fastener_warnings_are_always_returned(self):
        for part_type, params in (("bolt", BOLT), ("nut", {"thread_size": "M8"})):
            codes = [w["code"] for w in self.create(part_type, params)["warnings"]]
            self.assertIn("structural_fastener", codes)
            self.assertIn("printer_calibration", codes)
        bolt = self.create("bolt", dict(BOLT, load_bearing=True))
        self.assertIn("load_bearing_plastic", [w["code"] for w in bolt["warnings"]])


class ValidationTest(CadTestCase):
    def test_validation_reports_ready_model(self):
        created = self.create("nut", {"thread_size": "M6"})
        result = service.validate(created["model_id"], self.scene, self.store)
        self.assertTrue(result["ready_for_slicing"])
        self.assertTrue(result["report"]["fits_build_volume"])
        self.assertEqual(result["report"]["errors"], [])

    def test_open_mesh_is_an_error(self):
        mesh = meshbuild.revolve([meshbuild.Apex(0.0), meshbuild.Ring(0.0, meshbuild.circle_radii(5.0)),
                                  meshbuild.Ring(5.0, meshbuild.circle_radii(5.0))], False)
        report = validation.check(mesh)
        self.assertFalse(report["valid"])
        self.assertIn("not_closed", [e["code"] for e in report["errors"]])

    def test_inverted_mesh_is_an_error(self):
        mesh = meshbuild.prism(meshbuild.rectangle(0, 0, 10, 10), [], 0.0, 5.0, lambda u, v, w: (u, v, w))
        self.assertTrue(validation.check(mesh.welded())["valid"])
        report = validation.check(mesh.flipped().welded())
        self.assertIn("inward_normals", [e["code"] for e in report["errors"]])

    def test_degenerate_and_non_manifold(self):
        mesh = meshbuild.prism(meshbuild.rectangle(0, 0, 10, 10), [], 0.0, 5.0, lambda u, v, w: (u, v, w)).welded()
        extra = mesh.vertex(5.0, 5.0, 2.0)
        mesh.triangles.append((0, 1, extra))
        mesh.triangles.append((0, 1, extra))
        mesh.triangles.append((0, 0, 1))
        codes = [e["code"] for e in validation.check(mesh)["errors"]]
        self.assertIn("non_manifold", codes)
        sliver = meshbuild.Mesh()
        a = sliver.vertex(0, 0, 0)
        b = sliver.vertex(1, 0, 0)
        c = sliver.vertex(2, 0, 0)
        sliver.triangles.append((a, b, c))
        self.assertIn("degenerate_triangles", [e["code"] for e in validation.check(sliver)["errors"]])

    def test_build_volume_error_and_warning_levels(self):
        scene = FakeScene({"width": 10.0, "depth": 10.0, "height": 10.0})
        created = self.create("plate", PLATE, scene)
        result = service.validate(created["model_id"], scene, self.store)
        self.assertFalse(result["ready_for_slicing"])
        self.assertIn("exceeds_build_volume", [e["code"] for e in result["report"]["errors"]])

    def test_thin_wall_levels(self):
        thin = self.create("plate", {"width_mm": 30, "depth_mm": 30, "thickness_mm": 1.0})
        self.assertIn("thin_wall", [w["code"] for w in thin["warnings"]])
        self.assertEqual(thin["validation"]["status"], "ok")
        broken = validation.check(meshbuild.prism(meshbuild.rectangle(0, 0, 10, 10), [], 0.0, 5.0,
                                                  lambda u, v, w: (u, v, w)).welded(), min_wall=0.2)
        self.assertIn("wall_too_thin", [e["code"] for e in broken["errors"]])

    def test_size_mismatch_is_an_error(self):
        mesh = meshbuild.prism(meshbuild.rectangle(0, 0, 10, 10), [], 0.0, 5.0, lambda u, v, w: (u, v, w)).welded()
        report = validation.check(mesh, expected_size=(10.0, 10.0, 8.0))
        self.assertIn("size_mismatch", [e["code"] for e in report["errors"]])

    def test_unreadable_file(self):
        path = os.path.join(tempfile.mkdtemp(), "bad.stl")
        with open(path, "wb") as handle:
            handle.write(b"solid x")
        report = validation.check_file(path)
        self.assertFalse(report["valid"])

    def test_missing_geometry_file_is_rebuilt(self):
        created = self.create("washer", {"thread_size": "M5"})
        os.remove(created["geometry_path"])
        result = service.validate(created["model_id"], self.scene, self.store)
        self.assertTrue(result["ready_for_slicing"])
        self.assertTrue(os.path.isfile(created["geometry_path"]))


class UpdateTest(CadTestCase):
    def test_update_length_keeps_other_parameters_without_duplicates(self):
        created = self.create("bolt", dict(BOLT, clearance_mm=0.15, head_type="cylindrical"))
        updated = service.update(created["model_id"], {"length_mm": 40}, self.scene, self.store)
        self.assertEqual(updated["model_id"], created["model_id"])
        self.assertEqual(updated["revision"], 2)
        self.assertEqual(updated["parameters"]["length_mm"], 40.0)
        self.assertEqual(updated["parameters"]["clearance_mm"], 0.15)
        self.assertEqual(updated["parameters"]["head_type"], "cylindrical")
        self.assertEqual(updated["parameters"]["thread_length_mm"], 40.0)
        self.assertAlmostEqual(updated["size_mm"]["z"], 8.0 + 40.0, places=2)
        self.assertEqual(list(self.scene.objects.keys()), [updated["object_id"]])
        self.assertEqual(updated["replaced_object_id"], created["object_id"])
        self.assertEqual(updated["changed"], ["length_mm"])
        self.assertEqual(len(self.store.all()), 1)

    def test_update_head_type_and_object_id_lookup(self):
        created = self.create("bolt", BOLT)
        updated = service.update(created["object_id"], {"head_type": "countersunk"}, self.scene, self.store)
        self.assertEqual(updated["parameters"]["head_type"], "countersunk")
        self.assertEqual(updated["parameters"]["length_mm"], 30.0)
        self.assertEqual(len(self.scene.objects), 1)

    def test_update_without_identifier_uses_the_only_model(self):
        self.create("washer", {"thread_size": "M8"})
        updated = service.update(None, {"thickness_mm": 2.0}, self.scene, self.store)
        self.assertEqual(updated["parameters"]["thickness_mm"], 2.0)

    def test_update_is_ambiguous_with_two_models(self):
        self.create("washer", {"thread_size": "M8"})
        self.create("washer", {"thread_size": "M6"})
        with self.assertRaises(CadError):
            service.update(None, {"thickness_mm": 2.0}, self.scene, self.store)

    def test_update_validates_and_keeps_old_model_on_error(self):
        created = self.create("bolt", BOLT)
        with self.assertRaises(CadError):
            service.update(created["model_id"], {"length_mm": -1}, self.scene, self.store)
        with self.assertRaises(CadError):
            service.update("nothing", {"length_mm": 10}, self.scene, self.store)
        self.assertEqual(list(self.scene.objects.keys()), [created["object_id"]])
        self.assertEqual(self.store.find(created["model_id"])["parameters"]["length_mm"], 30.0)

    def test_update_changes_size_and_recomputes_defaults(self):
        created = self.create("bolt", BOLT)
        updated = service.update(created["model_id"], {"thread_size": "M6"}, self.scene, self.store)
        self.assertEqual(updated["parameters"]["pitch_mm"], 1.0)
        updated = service.update(created["model_id"], {"pitch_mm": 0.75}, self.scene, self.store)
        self.assertEqual(updated["parameters"]["pitch_mm"], 0.75)

    def test_update_rebuilds_a_model_missing_from_the_scene(self):
        created = self.create("nut", {"thread_size": "M8"})
        fresh = FakeScene()
        fresh.counter = 10
        rebuilt = service.update(created["model_id"], {}, fresh, self.store)
        self.assertEqual(len(fresh.objects), 1)
        self.assertEqual(rebuilt["parameters"], created["parameters"])
        self.assertIsNone(rebuilt["replaced_object_id"])


class PersistenceTest(CadTestCase):
    def test_specification_survives_json_and_load(self):
        created = self.create("bolt", BOLT)
        data = json.loads(json.dumps(self.store.snapshot()))
        restored = ModelStore()
        restored.load(data)
        spec = restored.find(created["model_id"])
        self.assertEqual(spec["schema_version"], schema.SCHEMA_VERSION)
        self.assertEqual(spec["part_type"], "bolt")
        self.assertEqual(spec["units"], "mm")
        self.assertEqual(spec["object_id"], created["object_id"])
        self.assertEqual(spec["path"], created["geometry_path"])
        self.assertIn("created", spec)
        self.assertEqual(spec["parameters"]["thread_size"], "M8")
        rebuilt = service.update(created["model_id"], {"length_mm": 35}, FakeScene(), restored)
        self.assertEqual(rebuilt["parameters"]["head_type"], "hex")

    def test_object_id_from_another_slicer_session_is_discarded(self):
        created = self.create("bolt", BOLT)
        saved = self.store.snapshot()
        saved[0]["scene_session_id"] = "previous-slicer-session"
        restored = ModelStore()
        restored.load(saved)
        self.assertIsNone(restored.find(created["model_id"])["object_id"])
        scene = FakeScene()
        scene.objects[created["object_id"]] = {"x": 1.0, "y": 1.0, "z": 1.0}
        scene.counter = 10
        rebuilt = service.update(created["model_id"], {"length_mm": 35}, scene, restored)
        self.assertEqual(len(scene.objects), 2)
        self.assertIn(created["object_id"], scene.objects)
        self.assertNotEqual(rebuilt["object_id"], created["object_id"])

    def test_store_ignores_broken_records(self):
        store = ModelStore()
        store.load([None, 5, {"part_type": "gear"}, {"model_id": "a", "part_type": "bolt"}])
        self.assertEqual(store.all(), [])
        store.load(None)
        self.assertEqual(store.all(), [])

    def test_project_saves_and_restores_specifications(self):
        manager = fresh_manager()
        project = manager.ensure_current()
        store = get_store()
        store.clear()
        created = service.create("bolt", BOLT, self.scene, store)
        manager.save_current()
        raw = projects.load_project(project)
        self.assertEqual(raw["generated_models"][0]["model_id"], created["model_id"])
        other = manager.create(prepare=False)
        self.assertEqual(store.all(), [])
        manager.open(project)
        self.assertEqual([s["model_id"] for s in store.all()], [created["model_id"]])
        manager.open(other["id"])
        self.assertEqual(store.all(), [])
        store.clear()

    def test_old_project_without_section_opens(self):
        manager = fresh_manager()
        old = projects.create_project("Старый")
        raw = projects.load_project(old["id"])
        self.assertNotIn("generated_models", raw)
        get_store().load([{"model_id": "x", "part_type": "bolt", "requested": {}, "parameters": {}}])
        manager.open(old["id"])
        self.assertEqual(get_store().all(), [])

    def test_saving_keeps_existing_section_when_not_passed(self):
        project = projects.create_project("P")
        projects.save_project(project["id"], [], [], None, [{"model_id": "m"}])
        projects.save_project(project["id"], [], [], None)
        self.assertEqual(projects.load_project(project["id"])["generated_models"], [{"model_id": "m"}])

    def test_context_notes_mention_stored_models(self):
        created = self.create("bolt", BOLT)
        notes = service.context_notes(self.store)
        self.assertEqual(len(notes), 1)
        self.assertIn(created["model_id"], notes[0])
        self.assertIn("update_parametric_model", notes[0])
        self.assertEqual(service.context_notes(ModelStore()), [])

    def test_listing_marks_missing_scene_objects(self):
        created = self.create("bolt", BOLT)
        shown = service.listing([created["object_id"]], self.store)["models"][0]
        self.assertTrue(shown["in_scene"])
        shown = service.listing([], self.store)["models"][0]
        self.assertFalse(shown["in_scene"])


def fresh_manager():
    from test_projects import fresh_manager as build
    return build()


class ExportTest(CadTestCase):
    def test_stl_export_is_binary_and_inside_results(self):
        created = self.create("washer", {"thread_size": "M8"})
        result = service.export(created["model_id"], "stl", "my washer", self.store)
        self.assertTrue(result["path"].endswith(".stl"))
        self.assertTrue(service.inside(config.get_results_dir(), result["path"]))
        with open(result["path"], "rb") as handle:
            mesh = meshbuild.read_stl(handle.read())
        self.assertEqual(len(mesh.triangles), result["triangles"])

    def test_3mf_export_is_a_valid_package(self):
        created = self.create("plate", PLATE)
        result = service.export(created["model_id"], "3mf", None, self.store)
        with zipfile.ZipFile(result["path"]) as archive:
            names = archive.namelist()
            self.assertIn("3D/3dmodel.model", names)
            self.assertIn("[Content_Types].xml", names)
            self.assertIn("_rels/.rels", names)
            import xml.etree.ElementTree as ET
            root = ET.fromstring(archive.read("3D/3dmodel.model"))
        ns = "{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}"
        self.assertEqual(root.get("unit"), "millimeter")
        triangles = root.findall(".//%striangle" % ns)
        vertices = root.findall(".//%svertex" % ns)
        self.assertEqual(len(triangles), result["triangles"])
        self.assertTrue(vertices)

    def test_export_rejects_unknown_format_and_sanitizes_names(self):
        created = self.create("washer", {"thread_size": "M8"})
        with self.assertRaises(CadError):
            service.export(created["model_id"], "obj", None, self.store)
        result = service.export(created["model_id"], "stl", "../../evil/..\\x", self.store)
        self.assertTrue(service.inside(config.get_results_dir(), result["path"]))
        with self.assertRaises(CadError):
            service.export("missing", "stl", None, self.store)

    def test_generated_geometry_stays_in_the_results_folder(self):
        created = self.create("bolt", BOLT)
        self.assertTrue(service.inside(os.path.join(config.get_results_dir(), "_generated"),
                                       created["geometry_path"]))


class ToolProtocolTest(CadTestCase):
    def setUp(self):
        super(ToolProtocolTest, self).setUp()
        self.registry = get_registry()
        self.original_scene = cad_tools._scene
        cad_tools._scene = lambda: self.scene
        self.list_tool = self.registry.get("list_objects")
        self.original_list = self.list_tool.handler
        self.list_tool.handler = lambda args: {"objects": [{"name": "m.stl", "size_mm": {"x": 1.0, "y": 2.0, "z": 3.0}}]}
        self.store_backup = get_store().snapshot()
        get_store().clear()
        self.bus = EventBus()

    def tearDown(self):
        cad_tools._scene = self.original_scene
        self.list_tool.handler = self.original_list
        get_store().load(self.store_backup)

    def call(self, name, arguments):
        result = protocol.call_tool(name, arguments, self.registry, self.bus)
        text = result["content"][0]["text"]
        return result["isError"], (text if result["isError"] else json.loads(text))

    def events(self, kind):
        return [e["data"] for e in self.bus.get_since(0)["events"] if e["type"] == kind]

    def test_tools_are_registered_for_openai_and_mcp(self):
        names = ["list_generatable_parts", "create_parametric_model", "update_parametric_model",
                 "validate_generated_model", "export_generated_model", "list_generated_models"]
        openai = dict((t["function"]["name"], t["function"]) for t in self.registry.list_openai())
        mcp = dict((t["name"], t) for t in self.registry.list_mcp())
        for name in names:
            self.assertIn(name, openai)
            self.assertIn(name, mcp)
            self.assertEqual(mcp[name]["inputSchema"], openai[name]["parameters"])
        schema_ = mcp["create_parametric_model"]["inputSchema"]
        self.assertEqual(sorted(schema_["required"]), ["parameters", "part_type"])
        self.assertEqual(schema_["properties"]["part_type"]["enum"], schema.part_types())

    def test_create_validate_update_flow_and_events(self):
        error, created = self.call("create_parametric_model", {"part_type": "bolt", "parameters": BOLT})
        self.assertFalse(error)
        error, checked = self.call("validate_generated_model", {"model_id": created["model_id"]})
        self.assertFalse(error)
        self.assertTrue(checked["ready_for_slicing"])
        error, changed = self.call("update_parametric_model",
                                   {"model_id": created["object_id"], "parameters": {"length_mm": 40}})
        self.assertFalse(error)
        self.assertEqual(len(self.scene.objects), 1)
        cards = self.events("generated_model")
        self.assertEqual(len(cards), 3)
        card = cards[0]
        for key in ("part_type", "parameters", "size_mm", "validation", "warnings", "object_id", "model_id"):
            self.assertIn(key, card)
        self.assertEqual(card["part_type"], "bolt")
        self.assertEqual(card["validation"]["status"], "ok")
        self.assertEqual(cards[2]["revision"], 2)
        scenes = self.events("scene")
        self.assertTrue(scenes)

    def test_errors_name_the_field(self):
        error, text = self.call("create_parametric_model", {"part_type": "bolt", "parameters": {"thread_size": "M8"}})
        self.assertTrue(error)
        self.assertIn("length_mm", text)
        error, text = self.call("create_parametric_model", {"part_type": "bolt", "parameters": {"length_mm": "x"}})
        self.assertIn("thread_size", text)
        self.assertEqual(self.events("generated_model"), [])

    def test_arbitrary_input_is_not_accepted(self):
        ok, payload, _ = run_guarded(self.registry, "create_parametric_model",
                                     {"part_type": "../../etc/passwd", "parameters": {}})
        self.assertFalse(ok)
        ok, payload, _ = run_guarded(self.registry, "create_parametric_model",
                                     {"part_type": "bolt", "parameters": "__import__('os')"})
        self.assertFalse(ok)
        ok, payload, _ = run_guarded(self.registry, "create_parametric_model",
                                     {"part_type": "bolt", "parameters": dict(BOLT, file_path="C:/x.stl")})
        self.assertFalse(ok)
        self.assertIn("parameters.file_path", payload)
        ok, payload, _ = run_guarded(self.registry, "export_generated_model", {"format": "step"})
        self.assertFalse(ok)

    def test_export_tool(self):
        self.call("create_parametric_model", {"part_type": "washer", "parameters": {"thread_size": "M8"}})
        error, result = self.call("export_generated_model", {"format": "3mf", "model_name": "../escape"})
        self.assertFalse(error)
        self.assertTrue(service.inside(config.get_results_dir(), result["path"]))

    def test_list_generated_models_tool(self):
        self.call("create_parametric_model", {"part_type": "washer", "parameters": {"thread_size": "M8"}})
        cad_tools.SlicerScene.present_objects = lambda self_: []
        try:
            error, listing = self.call("list_generated_models", {})
        finally:
            del cad_tools.SlicerScene.present_objects
        self.assertFalse(error)
        self.assertEqual(len(listing["models"]), 1)

    def test_new_generator_needs_no_protocol_change(self):
        def build_pin(params):
            mesh = meshbuild.prism(meshbuild.rectangle(0, 0, params["size_mm"], params["size_mm"]), [], 0.0,
                                   params["size_mm"], lambda u, v, w: (u, v, w))
            return mesh, {"label": "cube", "title": "Cube", "expected_size_mm": (params["size_mm"],) * 3,
                          "min_wall_mm": params["size_mm"], "warnings": [], "compensation": {},
                          "nominal": {}, "printable_thread": None}
        schema.PARTS["cube"] = {"title": "Cube", "description": "", "standards": [],
                                "parameters": {"size_mm": schema.number("mm", 1.0, 50.0, critical=True)}}
        parts.BUILDERS["cube"] = build_pin
        try:
            error, result = self.call("create_parametric_model", {"part_type": "cube", "parameters": {"size_mm": 10}})
            self.assertTrue(error, "the tool enum is fixed at registration")
            created = service.create("cube", {"size_mm": 10}, self.scene, self.store)
            self.assertEqual(created["size_mm"], {"x": 10.0, "y": 10.0, "z": 10.0})
        finally:
            del schema.PARTS["cube"]
            del parts.BUILDERS["cube"]


class PromptAndUiTest(CadTestCase):
    def test_prompt_contains_generation_rules(self):
        for language in ("ru", "en"):
            text = prompts.system_prompt(language)
            for name in ("list_generatable_parts", "create_parametric_model", "validate_generated_model",
                         "update_parametric_model", "critical=true", "list_generated_models"):
                self.assertIn(name, text)
        self.assertIn("ЯЗЫКОВОЙ КОНТРАКТ", prompts.system_prompt("ru"))
        self.assertIn("The user's language is English", prompts.system_prompt("en"))
        self.assertIn("Язык ответа: русский", prompts.turn_language_note("ru"))
        self.assertIn("Reply language: English", prompts.turn_language_note("en"))

    def test_prompt_keeps_the_attached_model_flow(self):
        text = prompts.system_prompt("ru")
        self.assertIn("load_model", text)
        self.assertIn("analyze_mesh", text)
        self.assertIn("recommend_setup", text)

    def card_events(self, language):
        created = self.create("bolt", dict(BOLT, load_bearing=True))
        from AIAssistant.server.derived_events import generated_model_event
        state = view_state.ChatViewState(language)
        state.apply({"type": "user_message", "data": {"text": "x"}})
        state.apply({"type": "tool_call", "data": {"call_id": "1", "name": "create_parametric_model",
                                                   "arguments": {}}})
        state.apply({"type": "generated_model", "data": generated_model_event(created)})
        state.apply({"type": "tool_result", "data": {"call_id": "1", "name": "create_parametric_model", "ok": True,
                                                     "result": created}})
        return state

    def test_card_is_shown_in_both_languages(self):
        for language, part, check in (("ru", "Болт", "пройдена"), ("en", "Bolt", "passed")):
            state = self.card_events(language)
            stage = state.items[1]["stages"][0]
            self.assertEqual(stage["group"], "generate")
            facts = dict((f["label"], f["value"]) for f in stage["facts"])
            values = " ".join(facts.values())
            self.assertIn(part, facts.values())
            self.assertIn(check, values)
            self.assertTrue(any("M8" in v for v in facts.values()))

    def test_generation_tools_have_titles_and_progress(self):
        from AIAssistant.ui import progress
        for name in ("create_parametric_model", "update_parametric_model", "validate_generated_model",
                     "export_generated_model"):
            self.assertIn(progress.stage_for_tool(name), progress.STAGE_ORDER)
            for language in ("ru", "en"):
                self.assertTrue(view_state.tool_title(language, name))
                self.assertTrue(view_state.tool_running_title(language, name))


if __name__ == "__main__":
    unittest.main()
