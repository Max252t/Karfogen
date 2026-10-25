import os
import unittest

import support
from AIAssistant import config
from AIAssistant.agent import knowledge
from AIAssistant.server import derived_events

PRINTER_MATERIALS = [
    "enduse_abs", "enduse_pa6", "enduse_pc", "enduse_petg", "enduse_pp", "enduse_sbs", "enduse_tpu_d70",
    "fiberpart_abs_g13", "fiberpart_pc_g20", "fiberpart_tpu_c5", "fiberpart_tpu_g30",
    "generic_abs_175", "generic_cpe_175", "generic_nylon_175", "generic_pc_175", "generic_petg_175",
    "generic_pla_175", "generic_tpu_175", "metalcast_316l", "proto_pla",
    "sealant_sebs", "sealant_tpe", "sealant_tpu", "sealant_tpu93", "sealant_tpu_A95", "sealant_tpv80",
]


class ElasticMaterialTest(unittest.TestCase):
    def setUp(self):
        config.set_value("language", "ru")

    def tearDown(self):
        config.set_value("language", "auto")

    def test_flexible_part_gets_soft_sealing_tpu(self):
        material = knowledge.resolve_material_id("TPU", PRINTER_MATERIALS, True, "flexible")
        self.assertEqual(material, "sealant_tpu93")

    def test_semi_flexible_part_gets_generic_tpu(self):
        self.assertEqual(knowledge.resolve_material_id("TPU", PRINTER_MATERIALS, True, "semi"), "generic_tpu_175")

    def test_hard_tpu_is_the_last_resort_for_flexible_parts(self):
        available = ["enduse_tpu_d70", "generic_pla_175"]
        self.assertEqual(knowledge.resolve_material_id("TPU", available, True, "flexible"), "enduse_tpu_d70")

    def test_without_flexibility_sealants_are_not_picked(self):
        self.assertEqual(knowledge.resolve_material_id("TPU", PRINTER_MATERIALS, True), "enduse_tpu_d70")
        self.assertEqual(knowledge.resolve_material_id("TPU", PRINTER_MATERIALS), "generic_tpu_175")

    def test_rigid_types_never_resolve_to_sealants(self):
        for material_type in knowledge.MATERIAL_TYPES:
            for flexibility in (None, "rigid", "semi", "flexible"):
                material = knowledge.resolve_material_id(material_type, PRINTER_MATERIALS, True, flexibility)
                if material_type != "TPU":
                    self.assertFalse((material or "").startswith("sealant_"), (material_type, material))

    def test_material_reason_explains_the_choice(self):
        self.assertIn("70D", knowledge.material_reason("TPU", "sealant_tpu93", "flexible"))
        self.assertIn("Шору D", knowledge.material_reason("TPU", "enduse_tpu_d70", "flexible"))
        self.assertEqual(knowledge.material_reason("PETG", "generic_petg_175", None), "")

    def test_warnings(self):
        self.assertIn("flexible parts", knowledge.material_warning("sealant_tpu93"))
        self.assertIn("special material", knowledge.material_warning("fiberpart_pc_g20"))
        self.assertIsNone(knowledge.material_warning("generic_petg_175"))


class ElasticSettingsTest(unittest.TestCase):
    def setUp(self):
        config.set_value("language", "ru")

    def tearDown(self):
        config.set_value("language", "auto")

    def test_flexible_part_disables_supports(self):
        _, settings, reasons = knowledge.recommend_settings(["flexible", "chemical"], "classic", 2.07)
        self.assertIs(settings["support_enable"], False)
        self.assertIn("спекаются", reasons["support_enable"])

    def test_thin_flexible_shell_keeps_infill_untouched(self):
        _, settings, reasons = knowledge.recommend_settings(["flexible", "airtight"], "classic", 2.07)
        self.assertNotIn("infill_sparse_density", settings)
        self.assertNotIn("infill_pattern", settings)
        self.assertEqual(settings["wall_line_count"], 4)
        self.assertIn("note_infill", reasons)

    def test_thick_flexible_part_keeps_infill(self):
        _, settings, _ = knowledge.recommend_settings(["flexible"], "classic", 12.0)
        self.assertEqual(settings["infill_sparse_density"], 15)
        self.assertEqual(settings["wall_line_count"], 3)

    def test_rigid_parts_are_not_affected_by_wall_estimate(self):
        _, settings, _ = knowledge.recommend_settings(["load_bearing"], "classic", 2.59)
        self.assertEqual(settings["infill_sparse_density"], 40)
        self.assertNotIn("support_enable", settings)

    def test_explicit_no_supports_reason_wins(self):
        _, _, reasons = knowledge.recommend_settings(["flexible", "no_supports"], "classic", 2.0)
        self.assertEqual(reasons["support_enable"], knowledge.reason("no_support"))

    def test_reasons_exist_in_both_languages(self):
        self.assertEqual(set(knowledge.REASONS["ru"]), set(knowledge.REASONS["en"]))


class DecisionRowsTest(unittest.TestCase):
    def setUp(self):
        config.set_value("language", "ru")

    def tearDown(self):
        config.set_value("language", "auto")

    def test_material_reason_and_notes_reach_the_table(self):
        plan = {"mode_label": "3D", "mode_reasons": ["x"], "quality_type": "fast", "quality_reason": "q",
                "material": {"id": "sealant_tpu93", "type": "TPU", "reason": "мягкий", "alternatives": ["SBS"]},
                "settings": [], "orientation": "o", "notes": ["заполнение не влияет"]}
        rows = derived_events._decision_rows(plan)
        self.assertTrue(rows[1][2].startswith("мягкий; "))
        self.assertEqual(rows[-1], ["Примечание", "", "заполнение не влияет"])


@unittest.skipUnless(os.path.isdir(os.environ.get("KARFOGEN_SAMPLE_PARTS") or
                                   os.path.join(os.path.expanduser("~"), "Downloads", "Примеры деталей")),
                     "sample parts are not available")
class BootSampleTest(unittest.TestCase):
    def test_boot_is_a_thin_elastic_shell(self):
        import glob
        from stl_loader import load_stl
        from AIAssistant.tools import geometry
        root = os.environ.get("KARFOGEN_SAMPLE_PARTS") or os.path.join(os.path.expanduser("~"), "Downloads",
                                                                       "Примеры деталей")
        stls = [p for p in glob.glob(os.path.join(root, "3*", "*")) if p.lower().endswith(".stl")]
        if not stls:
            self.skipTest("boot sample is missing")
        analysis = geometry.analyze(load_stl(stls[0]))
        tags = ["flexible", "chemical", "airtight", "impact"]
        self.assertEqual(knowledge.choose_mode(analysis, tags)[0], "classic")
        _, settings, _ = knowledge.recommend_settings(tags, "classic", analysis["mean_wall_mm"])
        self.assertNotIn("infill_sparse_density", settings)
        self.assertIs(settings["support_enable"], False)


if __name__ == "__main__":
    unittest.main()


class MaterialSubstitutionTest(unittest.TestCase):
    def setUp(self):
        config.set_value("language", "ru")

    def tearDown(self):
        config.set_value("language", "auto")

    def test_missing_material_is_not_replaced_by_a_weaker_one(self):
        self.assertIsNone(knowledge.resolve_material_id("CPE_PLUS", PRINTER_MATERIALS, True))
        self.assertIsNone(knowledge.resolve_material_id("TOUGH_PLA", PRINTER_MATERIALS, True))
        self.assertEqual(knowledge.resolve_material_id("CPE", PRINTER_MATERIALS, True), "generic_cpe_175")

    def test_heat_resistance_follows_slicer_descriptions(self):
        self.assertEqual(knowledge.MATERIAL_TYPES["CPE"]["heat"], 70)
        self.assertEqual(knowledge.MATERIAL_TYPES["ABS"]["heat"], 85)
        self.assertEqual(knowledge.MATERIAL_TYPES["PC"]["heat"], 110)

    def test_gear_requirements_end_with_a_material_that_withstands_the_heat(self):
        tags = ["load_bearing", "precision", "rotating", "humidity", "uv", "stiff"]
        for max_temp in (70, 90):
            ranked = knowledge.rank_materials(tags, max_temp)
            chosen = None
            for candidate in ranked:
                chosen = knowledge.resolve_material_id(candidate["type"], PRINTER_MATERIALS, True)
                if chosen:
                    chosen_type = candidate["type"]
                    break
            self.assertGreaterEqual(knowledge.MATERIAL_TYPES[chosen_type]["heat"], max_temp + 10, (max_temp, chosen))

    def test_profile_lists_the_properties_that_matter(self):
        text = "; ".join(knowledge.material_profile("PC", ["uv", "humidity"]))
        self.assertIn("110", text)
        self.assertIn("УФ", text)
        self.assertIn("влаге", text)

    def test_decision_row_mentions_skipped_types_and_properties(self):
        plan = {"mode_label": "3D", "mode_reasons": ["x"], "quality_type": "normal", "quality_reason": "q",
                "material": {"id": "enduse_pc", "type": "PC", "reason": "", "alternatives": ["ABS"],
                             "properties": ["теплостойкость 110 °C"], "skipped": ["CPE_PLUS"]},
                "settings": [], "orientation": "o"}
        note = derived_events._decision_rows(plan)[1][2]
        self.assertIn("110", note)
        self.assertIn("CPE_PLUS", note)
