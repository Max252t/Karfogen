import argparse
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests"))

import qml_harness


def pump(app, rounds=8):
    for _ in range(rounds):
        app.processEvents()


def grab(app, window, path):
    window.setOpacity(0.0)
    pump(app)
    time.sleep(0.1)
    pump(app)
    image = window.grabWindow()
    image.save(path, "PNG")
    return path


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
        window.setHeight(int(760 * scale))
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

    controller.send("Кронштейн под нагрузку" if language == "ru" else "Load-bearing bracket")
    ui_fakes.publish(bus, ui_fakes.CONVERSATION)
    controller.tick()
    shots.append(grab(app, window, os.path.join(out_dir, "03_running_%s.png" % suffix)))

    ui_fakes.publish(bus, ui_fakes.FINISH)
    agent.running = False
    controller.tick()
    shots.append(grab(app, window, os.path.join(out_dir, "04_chat_done_%s.png" % suffix)))

    bus.publish("user_message", {"text": "Сделай деталь прочнее"})
    bus.publish("error", {"message": "Ключ API отклонён (HTTP 401).", "code": "auth", "status": 401})
    bus.publish("done", {})
    controller.tick()
    shots.append(grab(app, window, os.path.join(out_dir, "05_error_%s.png" % suffix)))

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
    pump(app)
    for item in alive:
        item[0].stop()
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
