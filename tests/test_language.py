import unittest
from unittest import mock

import support
from AIAssistant import config
from AIAssistant.agent import prompts


class LanguageTest(unittest.TestCase):
    def tearDown(self):
        config.set_value("language", "auto")
        config.set_value("auto_export", True)
        config.set_value("explain", True)

    def test_explicit_language_wins(self):
        config.set_value("language", "en")
        self.assertEqual(config.effective_language(), "en")

    def test_auto_without_slicer_uses_the_system_language(self):
        config.set_value("language", "auto")
        with mock.patch.object(config, "slicer_language", return_value=""), \
                mock.patch.object(config, "system_language", return_value="ru_RU"):
            self.assertEqual(config.effective_language(), "ru")

    def test_prompt_follows_language(self):
        config.set_value("language", "ru")
        self.assertTrue(prompts.system_prompt().endswith(prompts.LANGUAGE_CONTRACTS["ru"]))
        config.set_value("language", "en")
        self.assertTrue(prompts.system_prompt().endswith(prompts.LANGUAGE_CONTRACTS["en"]))
        config.set_value("language", "de")
        self.assertEqual(config.language_mode(), "auto")
        with mock.patch.object(config, "slicer_language", return_value=""), \
                mock.patch.object(config, "system_language", return_value="en_US"):
            self.assertTrue(prompts.system_prompt().endswith(prompts.LANGUAGE_CONTRACTS["en"]))

    def test_manual_export_changes_prompt(self):
        config.set_value("auto_export", False)
        text = prompts.system_prompt()
        self.assertIn("кнопками", text)
        self.assertNotIn("@@", text)
        config.set_value("auto_export", True)
        self.assertIn("save_project_3mf с model_name", prompts.system_prompt())

    def test_public_settings_expose_new_fields(self):
        data = config.public_settings()
        for key in ("auto_export", "language", "language_effective", "slicer_language", "results_dir"):
            self.assertIn(key, data)


if __name__ == "__main__":
    unittest.main()
