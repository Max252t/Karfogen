import time
import unittest

import support
from AIAssistant.ui import dock_layout

try:
    import qml_harness
    from PyQt5.QtCore import QRect, Qt
    from PyQt5.QtGui import QGuiApplication, QWindow
    from AIAssistant.ui.dock import DockManager
    HAVE_QT = True
except ImportError:
    HAVE_QT = False


def right(rect):
    return rect[0] + rect[2]


class DockLayoutTest(unittest.TestCase):
    def check(self, available, layout):
        main, panel = layout["main_frame"], layout["panel_frame"]
        self.assertFalse(dock_layout.overlaps(main, panel))
        self.assertEqual(main[0], available[0])
        self.assertEqual(right(panel), right(available))
        self.assertEqual(right(main), panel[0])
        self.assertEqual((main[1], main[3]), (available[1], available[3]))
        self.assertEqual((panel[1], panel[3]), (available[1], available[3]))

    def test_first_open_takes_a_quarter_on_the_right(self):
        available = (0, 0, 1920, 1040)
        layout = dock_layout.dock_layout(available, dock_layout.DEFAULT_SHARE, 380, 0)
        self.check(available, layout)
        self.assertEqual(layout["panel_frame"][2], 480)
        self.assertAlmostEqual(layout["share"], 0.25)

    def test_client_rects_exclude_the_visible_frame(self):
        layout = dock_layout.dock_layout((0, 0, 2000, 1000), 0.25, 0, 0, (2, 45, 2, 2), (2, 30, 2, 2))
        self.assertEqual(layout["main"], (2, 45, 1496, 953))
        self.assertEqual(layout["panel"], (1502, 30, 496, 968))

    def test_scaling_keeps_the_minimum_panel_width(self):
        for scale, width in ((1.0, 1920), (1.25, 1920), (1.5, 2560), (2.0, 3840), (1.5, 1366)):
            available = (0, 0, width, 1000)
            panel_min = int(380 * scale)
            layout = dock_layout.dock_layout(available, 0.25, panel_min, 0)
            self.check(available, layout)
            self.assertGreaterEqual(layout["panel_frame"][2], min(panel_min, width // 2))
            self.assertGreaterEqual(layout["main_frame"][2], width // 2)

    def test_small_screen_never_gives_the_whole_screen_to_the_panel(self):
        for width in (1024, 800, 640):
            layout = dock_layout.dock_layout((0, 0, width, 700), 0.25, 400, 0)
            self.assertLessEqual(layout["panel_frame"][2], width // 2)
            self.assertGreater(layout["main_frame"][2], 0)

    def test_secondary_monitor_with_negative_coordinates(self):
        available = (-1920, -200, 1920, 1040)
        layout = dock_layout.dock_layout(available, 0.3, 380, 0)
        self.check(available, layout)
        self.assertEqual(layout["panel_frame"][0], -1920 + 1920 - 576)

    def test_share_is_clamped(self):
        self.assertEqual(dock_layout.clamp_share(0.99), dock_layout.MAX_SHARE)
        self.assertEqual(dock_layout.clamp_share(0.01), dock_layout.MIN_SHARE)
        self.assertEqual(dock_layout.clamp_share("bad"), dock_layout.DEFAULT_SHARE)
        self.assertEqual(dock_layout.clamp_share(float("nan")), dock_layout.DEFAULT_SHARE)

    def test_legacy_fullscreen_geometry_is_not_reused(self):
        self.assertIsNone(dock_layout.share_from_legacy("0,0,1900,1000", 1920))
        self.assertIsNone(dock_layout.share_from_legacy("garbage", 1920))
        self.assertAlmostEqual(dock_layout.share_from_legacy("1230,46,599,903", 1920), 599 / 1920.0)

    def test_user_resize_changes_the_share(self):
        available = (0, 0, 2000, 1000)
        expected = dock_layout.dock_layout(available, 0.25)
        wider = (1400, 0, 600, 1000)
        self.assertAlmostEqual(dock_layout.user_share(available, {"panel"}, expected["main_frame"], wider, expected), 0.3)
        narrower_main = (0, 0, 1300, 1000)
        self.assertAlmostEqual(dock_layout.user_share(available, {"main"}, narrower_main, expected["panel_frame"],
                                                      expected), 0.35)
        moved = (300, 0, 500, 1000)
        self.assertIsNone(dock_layout.user_share(available, {"panel"}, expected["main_frame"], moved, expected))


class FakePrefs(object):
    def __init__(self, values):
        self.values = dict(values)

    def getValue(self, key):
        return self.values.get(key)

    def setValue(self, key, value):
        self.values[key] = value


class FakeSettings(object):
    def __init__(self, **values):
        self.values = {"panel_share": "", "window_geometry": ""}
        self.values.update(values)

    def get(self, key):
        return self.values.get(key, "")

    def set_value(self, key, value):
        self.values[key] = value

    def persist(self):
        return True


@unittest.skipUnless(HAVE_QT, "PyQt5 is required for the dock tests")
class DockManagerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = qml_harness.app()

    def setUp(self):
        screen = QGuiApplication.primaryScreen().availableGeometry()
        self.available = (screen.x(), screen.y(), screen.width(), screen.height())
        self.main = QWindow()
        self.main.setGeometry(self.available[0] + 80, self.available[1] + 80, 700, 500)
        self.main.show()
        self.panel = QWindow()
        self.panel.setMinimumWidth(380)
        self.panel.setMinimumHeight(300)
        self.panel.setTransientParent(self.main)
        self.original = self.main.geometry()
        self.prefs = FakePrefs({"general/window_left": 80, "general/window_top": 80, "general/window_width": 700,
                                "general/window_height": 500})
        self.settings = FakeSettings()
        self.manager = DockManager(self.main, self.panel, self.prefs, self.settings)
        self.pump()

    def tearDown(self):
        self.manager.release()
        self.panel.destroy()
        self.main.destroy()
        self.pump(0.1)

    def pump(self, seconds=0.5):
        deadline = time.time() + seconds
        while time.time() < deadline:
            self.app.processEvents()
            time.sleep(0.01)

    def frame(self, window):
        return self.manager._frame(window)

    def assert_docked(self, share=dock_layout.DEFAULT_SHARE):
        main, panel = self.frame(self.main), self.frame(self.panel)
        self.assertFalse(dock_layout.overlaps(main, panel), (main, panel))
        self.assertLessEqual(abs(right(panel) - right(self.available)), dock_layout.TOLERANCE)
        self.assertLessEqual(abs(main[0] - self.available[0]), dock_layout.TOLERANCE)
        self.assertLessEqual(abs(panel[2] - max(380, self.available[2] * share)), 2 * dock_layout.TOLERANCE + 4)
        self.assertLessEqual(abs(panel[3] - self.available[3]), dock_layout.TOLERANCE)

    def test_open_docks_and_close_restores(self):
        self.manager.open()
        self.pump()
        self.assertTrue(self.panel.isVisible())
        self.assert_docked()
        self.assertEqual(self.prefs.values["general/window_width"], 700)
        self.panel.hide()
        self.pump()
        self.assertFalse(self.manager.active)
        self.assertEqual(self.main.geometry(), self.original)

    def test_reopen_reuses_the_same_panel(self):
        self.manager.open()
        self.pump()
        first = self.frame(self.panel)
        self.manager.open()
        self.pump()
        self.assertEqual(self.frame(self.panel), first)
        self.assertTrue(self.manager.active)

    def test_maximized_main_window_is_restored_as_maximized(self):
        self.main.showMaximized()
        self.pump()
        self.manager.open()
        self.pump()
        self.assertFalse(int(self.main.windowState()) & int(Qt.WindowMaximized))
        self.assert_docked()
        self.assertEqual(self.prefs.values["general/window_state"], int(Qt.WindowMaximized))
        self.panel.hide()
        self.pump()
        self.assertTrue(int(self.main.windowState()) & int(Qt.WindowMaximized))

    def test_user_resizing_the_panel_is_remembered(self):
        share = max(0.35, 400.0 / self.available[2])
        if share > dock_layout.MAX_SHARE:
            self.skipTest("the screen is too narrow to widen the panel past its minimum width")
        self.manager.open()
        self.pump()
        layout = self.manager.layout()
        wider = int(self.available[2] * share)
        edges = self.manager._edges(self.panel)
        frame = (right(self.available) - wider, self.available[1], wider, self.available[3])
        self.panel.setGeometry(QRect(*dock_layout.shrink(frame, edges)))
        self.pump()
        self.assertAlmostEqual(float(self.settings.values["panel_share"]), share, places=2)
        self.assert_docked(share)
        self.assertNotEqual(layout["panel_frame"], self.manager.layout()["panel_frame"])

    def test_moving_the_panel_detaches_and_restores_the_main_window(self):
        self.manager.open()
        self.pump()
        moved = QRect(self.panel.x() - 180, self.panel.y() + 80, self.panel.width(), self.panel.height() - 120)
        self.panel.setGeometry(moved)
        self.pump()
        self.assertEqual(self.panel.geometry(), moved)
        self.assertEqual(self.main.geometry(), self.original)
        self.assertTrue(self.manager.active)
        self.assertIsNone(self.manager.layout())

    def test_moving_the_main_window_is_not_undone(self):
        self.manager.open()
        self.pump()
        moved = QRect(self.available[0] + 300, self.available[1] + 200, 600, 400)
        self.main.setGeometry(moved)
        self.pump()
        self.assertEqual(self.main.geometry(), moved)
        self.assertTrue(self.manager.active)
        self.assertIsNone(self.manager.layout())

    def test_opening_an_already_visible_detached_panel_does_not_redock(self):
        self.manager.open()
        self.pump()
        moved = QRect(self.panel.x() - 180, self.panel.y() + 80, self.panel.width(), self.panel.height() - 120)
        self.panel.setGeometry(moved)
        self.pump()
        self.manager.open()
        self.pump()
        self.assertEqual(self.panel.geometry(), moved)
        self.assertEqual(self.main.geometry(), self.original)

    def test_legacy_geometry_is_migrated_once(self):
        self.settings.values["window_geometry"] = "0,0,%d,900" % self.available[2]
        self.manager.open()
        self.pump()
        self.assert_docked()
        self.assertEqual(self.settings.values["window_geometry"], "")
        self.assertEqual(self.settings.values["panel_share"], "")

    def test_sane_legacy_width_becomes_the_share(self):
        width = int(self.available[2] * 0.3)
        self.settings.values["window_geometry"] = "10,10,%d,700" % width
        self.assertAlmostEqual(self.manager.share(), width / float(self.available[2]), places=3)
        self.assertEqual(self.settings.values["window_geometry"], "")
        self.assertAlmostEqual(float(self.settings.values["panel_share"]), 0.3, places=2)

    def test_obsolete_half_screen_share_is_reset_to_default(self):
        self.settings.values["panel_share"] = "0.5000"
        self.assertEqual(self.manager.share(), dock_layout.DEFAULT_SHARE)
        self.assertEqual(self.settings.values["panel_share"], "0.2500")


if __name__ == "__main__":
    unittest.main()
