import glob
import os
import unittest

import support
from AIAssistant.agent import knowledge
from AIAssistant.tools import geometry

SAMPLES = os.environ.get("KARFOGEN_SAMPLE_PARTS", os.path.join(os.path.expanduser("~"), "Downloads", "Примеры деталей"))


def sym(axisymmetric, aspect, length=50.0):
    return {"axisymmetry": {"is_axisymmetric": axisymmetric, "aspect": aspect, "axis": "z", "length_mm": length},
            "mean_wall_mm": 5.0}


class ModeTest(unittest.TestCase):
    def test_thick_cylinder_with_precision_is_5d(self):
        mode, _ = knowledge.choose_mode(sym(True, 0.5), ["precision", "rotating"])
        self.assertEqual(mode, "cylindrical_full")

    def test_flat_disc_is_3d(self):
        mode, _ = knowledge.choose_mode(sym(True, 0.13), ["precision", "rotating"])
        self.assertEqual(mode, "classic")

    def test_thin_wall_is_3d(self):
        analysis = sym(True, 1.0)
        analysis["mean_wall_mm"] = 2.0
        self.assertEqual(knowledge.choose_mode(analysis, ["precision"])[0], "classic")

    def test_flexible_is_3d(self):
        self.assertEqual(knowledge.choose_mode(sym(True, 1.0), ["flexible"])[0], "classic")

    def test_too_long_for_5d(self):
        self.assertEqual(knowledge.choose_mode(sym(True, 1.0, 300), ["precision"])[0], "classic")

    def test_shaft_with_torque_is_5d(self):
        analysis = sym(False, 0.64)
        analysis["axisymmetry"]["lateral_area_ratio"] = 0.63
        tags = ["precision", "load_bearing", "rotating"]
        self.assertEqual(knowledge.choose_mode(analysis, tags)[0], "cylindrical_full")

    def test_loaded_precise_bracket_stays_3d(self):
        analysis = sym(False, 0.8)
        analysis["axisymmetry"]["lateral_area_ratio"] = 0.7
        tags = ["load_bearing", "precision", "no_supports"]
        self.assertEqual(knowledge.choose_mode(analysis, tags)[0], "classic")

    def test_rotating_part_without_prismatic_profile_stays_3d(self):
        analysis = sym(False, 0.8)
        analysis["axisymmetry"]["lateral_area_ratio"] = 0.2
        tags = ["load_bearing", "precision", "rotating"]
        self.assertEqual(knowledge.choose_mode(analysis, tags)[0], "classic")

    def test_no_requirements_is_3d(self):
        self.assertEqual(knowledge.choose_mode(sym(True, 0.5), [])[0], "classic")


class MaterialTest(unittest.TestCase):
    def top(self, tags, **kw):
        return knowledge.rank_materials(tags, **kw)[0]["type"]

    def test_flexible_is_tpu(self):
        self.assertEqual(self.top(["flexible", "chemical"], flexibility="flexible"), "TPU")

    def test_high_temp_excludes_pla_and_petg(self):
        ranked = knowledge.rank_materials(["load_bearing"], max_temp_c=85)
        order = [r["type"] for r in ranked]
        self.assertLess(order.index("PC"), order.index("PLA"))
        self.assertLess(order.index("PC"), order.index("PETG"))

    def test_wear_prefers_polyamide(self):
        self.assertEqual(self.top(["wear", "rotating"], max_temp_c=40), "PA")

    def test_decorative_prefers_easy_material(self):
        self.assertIn(self.top(["decorative"]), ("PLA", "TOUGH_PLA", "PETG"))

    def test_resolve_material_id(self):
        available = ["generic_pla", "generic_petg", "enduse_petg"]
        self.assertEqual(knowledge.resolve_material_id("PETG", available), "generic_petg")
        self.assertEqual(knowledge.resolve_material_id("PETG", available, prefer_enduse=True), "enduse_petg")
        self.assertIsNone(knowledge.resolve_material_id("PC", available))

    def test_generic_materials_exist_only_with_175_suffix(self):
        available = ["enduse_pc", "generic_pc_175", "generic_petg_175", "generic_tpu_175", "fiberpart_pc_g20"]
        self.assertEqual(knowledge.resolve_material_id("PETG", available), "generic_petg_175")
        self.assertEqual(knowledge.resolve_material_id("TPU", available), "generic_tpu_175")
        self.assertEqual(knowledge.resolve_material_id("PC", available), "generic_pc_175")
        self.assertEqual(knowledge.resolve_material_id("PC", available, prefer_enduse=True), "enduse_pc")

    def test_special_families_are_never_a_fallback(self):
        available = ["fiberpart_pc_g20", "sealant_tpu93", "contifiber_cpa", "generic_pla"]
        self.assertIsNone(knowledge.resolve_material_id("PC", available))
        self.assertIsNone(knowledge.resolve_material_id("TPU", available))
        self.assertTrue(knowledge.is_special_material("fiberpart_pc_g20"))
        self.assertFalse(knowledge.is_special_material("enduse_pc"))


class SettingsTest(unittest.TestCase):
    def test_load_bearing(self):
        quality, settings, _ = knowledge.recommend_settings(["load_bearing"], "classic")
        self.assertEqual(settings["wall_line_count"], 4)
        self.assertEqual(settings["infill_sparse_density"], 40)
        self.assertEqual(quality, "fast")

    def test_no_supports(self):
        _, settings, _ = knowledge.recommend_settings(["no_supports"], "classic")
        self.assertFalse(settings["support_enable"])

    def test_fast_proto(self):
        quality, settings, _ = knowledge.recommend_settings(["fast_proto"], "classic")
        self.assertEqual(quality, "draft")
        self.assertEqual(settings["infill_sparse_density"], 10)

    def test_precision_uses_fine_layer(self):
        quality, _, _ = knowledge.recommend_settings(["precision"], "classic")
        self.assertEqual(quality, "normal")


class ReasonsTest(unittest.TestCase):
    def tearDown(self):
        from AIAssistant import config
        config.set_value("language", "auto")

    def test_reasons_follow_language(self):
        from AIAssistant import config
        config.set_value("language", "en")
        english = knowledge.choose_mode(sym(True, 0.13), ["precision"])[1][0]
        config.set_value("language", "ru")
        russian = knowledge.choose_mode(sym(True, 0.13), ["precision"])[1][0]
        self.assertNotEqual(english, russian)
        self.assertIn("disc", english)
        self.assertIn("диск", russian)

    def test_every_reason_exists_in_both_languages(self):
        self.assertEqual(set(knowledge.REASONS["ru"]), set(knowledge.REASONS["en"]))

    def test_tight_temperature_margin_is_penalized(self):
        ranked = dict((r["type"], r) for r in knowledge.rank_materials(["load_bearing"], max_temp_c=70))
        self.assertTrue(any("10" in note for note in ranked["SBS"]["notes"]))
        self.assertLess(ranked["SBS"]["score"], ranked["PC"]["score"])

    def test_special_material_is_not_a_candidate(self):
        for ids in knowledge.MATERIAL_IDS.values():
            for material_id in ids:
                self.assertFalse(knowledge.is_special_material(material_id), material_id)


@unittest.skipUnless(os.path.isdir(SAMPLES), "sample parts are not available")
class SamplePartsTest(unittest.TestCase):
    EXPECTED = {
        "1": ("classic", ["load_bearing", "precision", "rotating", "humidity", "uv"]),
        "2": ("cylindrical_full", ["precision", "rotating", "wear", "load_bearing", "chemical"]),
        "3": ("classic", ["flexible", "chemical", "impact"]),
        "4": ("classic", ["decorative", "thin_features", "uv"]),
        "5": ("cylindrical_full", ["precision", "rotating", "load_bearing", "chemical", "humidity", "high_temp"]),
        "6": ("classic", ["rotating", "lightweight", "impact", "high_temp"]),
        "7": ("cylindrical_full", ["precision", "rotating", "wear", "load_bearing", "chemical"]),
    }

    def test_modes(self):
        from stl_loader import load_stl
        for folder in sorted(glob.glob(os.path.join(SAMPLES, "*"))):
            number = os.path.basename(folder)[0]
            stls = [f for f in glob.glob(os.path.join(folder, "*")) if f.lower().endswith(".stl")]
            tris = load_stl(stls[0])
            analysis = geometry.analyze(tris)
            expected, tags = self.EXPECTED[number]
            mode, _ = knowledge.choose_mode(analysis, tags)
            self.assertEqual(mode, expected, "part %s: %s" % (number, analysis["axisymmetry"]))


if __name__ == "__main__":
    unittest.main()
