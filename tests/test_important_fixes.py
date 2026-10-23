import base64
import os
import tempfile
import threading
import unittest

import support
from AIAssistant import config
from AIAssistant.agent import agent as agent_module, llm_client
from AIAssistant.mcp.registry import get_registry, ToolError
from AIAssistant.server import projects, uploads
from AIAssistant.tools import settings_tools

PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==")


class ProjectRaceTest(unittest.TestCase):
    def setUp(self):
        config.set_value("results_dir", tempfile.mkdtemp())

    def test_rename_survives_concurrent_saves(self):
        meta = projects.create_project("old")
        stop = threading.Event()

        def saver():
            while not stop.is_set():
                projects.save_project(meta["id"], [], [])

        thread = threading.Thread(target=saver)
        thread.start()
        try:
            for index in range(30):
                projects.rename_project(meta["id"], "name %d" % index)
                self.assertEqual(projects.load_project(meta["id"])["name"], "name %d" % index)
        finally:
            stop.set()
            thread.join(5)


class SetSettingsValidationTest(unittest.TestCase):
    def call(self, changes):
        return get_registry().call("set_settings", {"changes": changes})

    def test_bad_extruder_is_a_tool_error(self):
        for extruder in ("all", 1.5, float("nan"), float("inf"), True):
            with self.assertRaises(ToolError):
                self.call([{"key": "wall_line_count", "value": 3, "extruder": extruder}])

    def test_non_string_key_and_container_value_rejected(self):
        with self.assertRaises(ToolError):
            self.call([{"key": 5, "value": 3}])
        with self.assertRaises(ToolError):
            self.call([{"key": "wall_line_count", "value": [3]}])

    def test_extruder_position_accepts_integers(self):
        self.assertEqual(settings_tools._extruder_position(2), 2)
        self.assertEqual(settings_tools._extruder_position(-1), -1)
        self.assertEqual(settings_tools._extruder_position("1"), 1)
        self.assertEqual(settings_tools._extruder_position(1.0), 1)


class ImageHandlingTest(unittest.TestCase):
    def setUp(self):
        config.set_value("results_dir", tempfile.mkdtemp())

    def test_images_count_towards_history_size(self):
        message = {"role": "user", "content": [{"type": "text", "text": "hi"},
                                               {"type": "image_url", "image_url": {"url": "data:x"}}]}
        self.assertEqual(agent_module._message_size(message) - agent_module._message_size({"content": "hi"}),
                         agent_module.IMAGE_COST_CHARS)

    def test_only_image_related_errors_drop_images(self):
        image_error = llm_client.LLMError("Ошибка LLM (HTTP 400): model does not support image input", 400)
        length_error = llm_client.LLMError("Ошибка LLM (HTTP 400): context length exceeded", 400)
        server_error = llm_client.LLMError("Ошибка LLM (HTTP 500): image", 500)
        self.assertTrue(agent_module.is_image_rejection(image_error))
        self.assertFalse(agent_module.is_image_rejection(length_error))
        self.assertFalse(agent_module.is_image_rejection(server_error))

    def test_small_image_is_passed_through(self):
        item = uploads.save_upload("pic.png", base64.b64encode(PNG).decode("ascii"))
        url = uploads.image_data_url(item)
        self.assertTrue(url.startswith("data:image/png;base64,"))

    def test_oversized_image_without_qt_is_skipped(self):
        item = uploads.save_upload("pic.png", base64.b64encode(PNG).decode("ascii"))
        original = uploads.MAX_RAW_IMAGE_BYTES
        uploads.MAX_RAW_IMAGE_BYTES = 10
        try:
            self.assertIsNone(uploads.image_data_url(item))
        finally:
            uploads.MAX_RAW_IMAGE_BYTES = original

    def test_agent_notes_skipped_image(self):
        item = uploads.save_upload("pic.png", base64.b64encode(PNG).decode("ascii"))
        original = uploads.MAX_RAW_IMAGE_BYTES
        uploads.MAX_RAW_IMAGE_BYTES = 10
        try:
            agent = agent_module.Agent(registry=get_registry(), llm=object())
            message = agent._build_user_message("hello", [item["id"]], None)
        finally:
            uploads.MAX_RAW_IMAGE_BYTES = original
        self.assertIsInstance(message["content"], str)
        self.assertIn("pic.png", message["content"])
        self.assertTrue(os.path.isfile(item["path"]))


if __name__ == "__main__":
    unittest.main()
