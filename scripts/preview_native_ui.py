import argparse
import os
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests"))

import qml_harness
from PyQt5.QtCore import QCoreApplication, QEvent
from PyQt5.QtGui import QColor, QImage


def pump(app, rounds=8):
    for _ in range(rounds):
        app.processEvents()


def visual_items(root):
    stack = [root]
    while stack:
        item = stack.pop(0)
        yield item
        stack.extend(item.childItems())


def grab(app, window, path):
    window.setOpacity(0.0)
    pump(app)
    time.sleep(0.1)
    pump(app)
    image = window.grabWindow()
    image.save(path, "PNG")
    return path


def set_on(window, name, value):
    for item in visual_items(window.contentItem()):
        if item.property(name) is not None and item.metaObject().indexOfProperty(name) >= 0:
            item.setProperty(name, value)


def render(out_dir, language, scale, theme_dir=None):
    app = qml_harness.app(scale, theme_dir)
    import ui_fakes
    from AIAssistant import config

    shots = []
    alive = []
    suffix = "%s_%d" % (language, int(scale * 100))

    def env(configured=True, objects=None):
        controller, agent, bus, registry, manager = ui_fakes.fresh_environment(configured, objects)
        config.set_value("language", language)
        controller._check_language()
        controller.refreshScene()
        engine, context, component, window, errors = qml_harness.create(controller, scale=scale)
        if window is None:
            raise SystemExit("\n".join(errors))
        window.setWidth(int(560 * scale))
        window.setHeight(min(int(760 * scale), app.primaryScreen().availableGeometry().height() - 80))
        window.show()
        alive.append((controller, agent, bus, window, engine, context, component))
        return controller, agent, bus, window, (engine, context, component)

    controller, agent, bus, window, keep = env(configured=False)
    shots.append(grab(app, window, os.path.join(out_dir, "01_first_run_%s.png" % suffix)))
    window.close()

    objects = [ui_fakes.scene_object("obj1", "bracket.stl", 62, 40, 35),
               ui_fakes.scene_object("obj2", "cover_plate_with_a_very_long_file_name_for_wrapping.stl", 120.5, 80, 3.2)]
    controller, agent, bus, window, keep = env(objects=objects)
    controller.setUseScene(True)
    shots.append(grab(app, window, os.path.join(out_dir, "02_empty_project_%s.png" % suffix)))

    def shot(name, target=None):
        controller._live.reset()
        controller.tick()
        shots.append(grab(app, target or window, os.path.join(out_dir, "%s_%s.png" % (name, suffix))))

    controller.send("Кронштейн под нагрузку" if language == "ru" else "Load-bearing bracket")
    conversation = ui_fakes.CONVERSATION
    ui_fakes.publish(bus, conversation[:2])
    controller.tick()
    shot("03a_waiting")
    ui_fakes.publish(bus, conversation[2:6])
    controller.tick()
    shot("03b_analysis")
    ui_fakes.publish(bus, conversation[6:16] + ui_fakes.MORE_SETTINGS)
    controller.tick()
    pump(app)
    set_on(window, "historyOpen", True)
    shot("03c_settings_history")
    set_on(window, "historyOpen", False)
    ui_fakes.publish(bus, conversation[16:18])
    for fraction, name in ((0.10, "03d_slicing_10"), (0.55, "03e_slicing_55"), (0.95, "03f_slicing_95")):
        bus.publish("slice_progress", {"state": "slicing", "progress": fraction})
        controller.tick()
        shot(name)

    ui_fakes.publish(bus, ui_fakes.FINISH)
    agent.running = False
    controller.tick()
    shot("04a_done")
    window.setHeight(min(int(1000 * scale), app.primaryScreen().availableGeometry().height() - 80))
    set_on(window, "moreOpen", True)
    shot("04b_done_details")
    set_on(window, "openStages", {"1": True})
    set_on(window, "openTech", {"1": True})
    shot("04c_tech_details")
    set_on(window, "openTech", {})
    window.setWidth(int(400 * scale))
    shot("04d_narrow_details")
    window.setWidth(int(560 * scale))
    set_on(window, "moreOpen", False)
    window.setHeight(min(int(760 * scale), app.primaryScreen().availableGeometry().height() - 80))

    bus.publish("user_message", {"text": "Сделай деталь прочнее"})
    bus.publish("error", {"message": "Ключ API отклонён (HTTP 401).", "code": "auth", "status": 401})
    bus.publish("done", {})
    controller.tick()
    shots.append(grab(app, window, os.path.join(out_dir, "05_error_%s.png" % suffix)))

    bus.publish("user_message", {"text": "Сделай вариант из PETG" if language == "ru" else "Make a PETG version"})
    ui_fakes.publish(bus, ui_fakes.CONVERSATION[3:9])
    bus.publish("error", {"message": "LLM недоступна: timed out", "code": "network"})
    bus.publish("done", {})
    controller.tick()
    pump(app)
    set_on(window, "historyOpen", True)
    shot("05b_error_partial")
    bus.publish("user_message", {"text": "Повтори" if language == "ru" else "Again"})
    ui_fakes.publish(bus, ui_fakes.CONVERSATION[3:7])
    bus.publish("status", {"text": "Останавливаю"})
    controller.tick()
    shot("05c_stopping")
    bus.publish("assistant_message", {"text": "Остановлено пользователем.", "intermediate": True, "code": "cancelled"})
    bus.publish("done", {})
    controller.tick()
    shot("05d_cancelled")

    controller.showTab.emit("result")
    shots.append(grab(app, window, os.path.join(out_dir, "06_result_%s.png" % suffix)))

    controller.showTab.emit("projects")
    controller.refreshProjects()
    shots.append(grab(app, window, os.path.join(out_dir, "07_projects_%s.png" % suffix)))

    controller.showTab.emit("chat")
    controller.openSettingsRequested.emit()
    pump(app)
    for child in app.topLevelWindows():
        if child is not window and child.isVisible() and child.title():
            shots.append(grab(app, child, os.path.join(out_dir, "08_settings_%s.png" % suffix)))
            child.close()
    window.setWidth(int(400 * scale))
    window.setHeight(int(460 * scale))
    shots.append(grab(app, window, os.path.join(out_dir, "09_narrow_%s.png" % suffix)))
    window.close()

    controller, agent, bus, window, keep = env(objects=[ui_fakes.scene_object("obj1", "gear.stl", 33.1, 10.1, 33.1)])
    folder = tempfile.mkdtemp()
    image = QImage(96, 64, QImage.Format_RGB32)
    image.fill(QColor(206, 132, 72))
    files = [os.path.join(folder, "photo_of_the_worn_part.png"), os.path.join(folder, "gear_v2.stl"),
             os.path.join(folder, "assembly_with_a_really_long_descriptive_name_for_the_conveyor_line.3mf")]
    image.save(files[0])
    for path in files[1:]:
        with open(path, "wb") as handle:
            handle.write(b"solid demo\n" * 300)
    controller.addFiles(files)
    controller.setUseScene(True)
    shots.append(grab(app, window, os.path.join(out_dir, "10_attachments_%s.png" % suffix)))

    long_text = ui_fakes.LONG_ANSWER_RU if language == "ru" else ui_fakes.LONG_ANSWER_EN
    controller.send("Шестерня" if language == "ru" else "Gear")
    bus.publish("user_message", {"text": "Шестерня" if language == "ru" else "Gear"})
    ui_fakes.publish(bus, ui_fakes.CONVERSATION[3:9])
    bus.publish("assistant_message", {"text": long_text})
    bus.publish("done", {})
    agent.running = False
    controller.tick()
    shots.append(grab(app, window, os.path.join(out_dir, "12a_long_answer_%s.png" % suffix)))
    set_on(window, "expanded", True)
    shots.append(grab(app, window, os.path.join(out_dir, "12b_long_answer_open_%s.png" % suffix)))
    bus.publish("user_message", {"text": "Таблица" if language == "ru" else "Table"})
    bus.publish("assistant_message", {"text": ui_fakes.TABLE_ANSWER})
    bus.publish("done", {})
    controller.tick()
    shots.append(grab(app, window, os.path.join(out_dir, "12c_table_answer_%s.png" % suffix)))

    from AIAssistant.server import projects
    projects.create_project("Корпус редуктора, версия для печати из PETG с усиленными рёбрами жёсткости"
                            if language == "ru" else "Gearbox housing, PETG print version with reinforced stiffening ribs")
    projects.create_project("Пыльник ШРУСа" if language == "ru" else "CV joint boot")
    controller.refreshProjects()
    controller.showTab.emit("projects")
    shots.append(grab(app, window, os.path.join(out_dir, "13_projects_many_%s.png" % suffix)))
    window.close()
    pump(app)
    for item in alive:
        item[0].stop()
        item[3].close()
        item[3].deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    pump(app)
    return shots


def main(argv):
    parser = argparse.ArgumentParser(description="Render the native AI Assistant window to PNG files")
    parser.add_argument("--out", required=True)
    parser.add_argument("--lang", default="ru", choices=["ru", "en"])
    parser.add_argument("--scale", type=float, default=1.0)
    parser.add_argument("--theme", default=None)
    args = parser.parse_args(argv)
    if not os.path.isdir(args.out):
        os.makedirs(args.out)
    shots = render(args.out, args.lang, args.scale, args.theme)
    for path in shots:
        print(path)
    problems = qml_harness.problems()
    for line in problems:
        print("QML: %s" % line)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
