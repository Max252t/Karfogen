import os
import sys
import time
import unittest

import support

sys.path.insert(0, os.path.join(support.ROOT, "scripts"))
import check_qml

try:
    import qml_harness
    HAVE_QT = True
except ImportError:
    HAVE_QT = False

import ui_fakes


class StaticQmlTest(unittest.TestCase):
    def test_static_rules(self):
        problems = check_qml.check_qmldir()
        for name in os.listdir(check_qml.QML_DIR):
            if name.endswith(".qml"):
                problems.extend(check_qml.check_file(os.path.join(check_qml.QML_DIR, name)))
        self.assertEqual(problems, [])

    def test_checker_catches_new_qt_features(self):
        path = os.path.join(support.ROOT, "tests", "qml_stub", "_bad.qml")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write('import QtQuick 2.9\nimport QtQuick.Controls 2.0\nItem { leftPadding: 2; '
                         'Component.onCompleted: { var x = XMLHttpRequest } }\n')
        try:
            problems = check_qml.check_file(path)
        finally:
            os.remove(path)
        self.assertEqual(len(problems), 4)


@unittest.skipUnless(HAVE_QT, "PyQt5 is required to load the QML")
class LoadQmlTest(unittest.TestCase):
    def pump(self, app, seconds=0.3):
        deadline = time.time() + seconds
        while time.time() < deadline:
            app.processEvents()
            time.sleep(0.01)

    def test_window_loads_and_renders_every_state_without_qml_errors(self):
        app = qml_harness.app()
        del qml_harness.MESSAGES[:]
        objects = [ui_fakes.scene_object("obj1", "bracket.stl", 62, 40, 35),
                   ui_fakes.scene_object("obj2", "cover.stl", 120, 80, 3)]
        controller, agent, bus, registry, manager = ui_fakes.fresh_environment(objects=objects)
        controller.refreshScene()
        engine, context, component, window, errors = qml_harness.create(controller)
        self.assertEqual(errors, [])
        self.assertIsNotNone(window)
        controller.setWindow(window)
        try:
            window.show()
            self.pump(app)
            controller.setUseScene(True)
            controller.send("Кронштейн")
            ui_fakes.publish(bus, ui_fakes.CONVERSATION)
            controller.tick()
            self.pump(app)
            ui_fakes.publish(bus, ui_fakes.FINISH)
            bus.publish("error", {"message": "x", "code": "auth"})
            agent.running = False
            controller.tick()
            self.pump(app)
            for tab in ("result", "projects", "chat"):
                controller.showTab.emit(tab)
                self.pump(app)
            controller.openSettingsRequested.emit()
            self.pump(app)
            window.setWidth(window.minimumWidth())
            self.pump(app)
            self.assertEqual(window.property("currentTab"), "chat")
            self.assertGreaterEqual(window.minimumWidth(), 380)
            self.assertGreater(controller.messageModel.count, 5)
            before = controller.messageModel.items()
            window.close()
            self.pump(app)
            window.show()
            self.pump(app)
            self.assertEqual(controller.messageModel.items(), before)
            screenshot = controller.saveScreenshot()
            self.assertTrue(os.path.isfile(screenshot))
            with open(screenshot, "rb") as handle:
                self.assertEqual(handle.read(8), b"\x89PNG\r\n\x1a\n")
        finally:
            for item in app.topLevelWindows():
                item.close()
            window.deleteLater()
            self.pump(app, 0.2)
            controller.stop()
        self.assertEqual(qml_harness.problems(), [])


if __name__ == "__main__":
    unittest.main()
