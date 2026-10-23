import os
import re
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGIN = os.path.join(ROOT, "plugin")
RESULTS = os.path.join(ROOT, "results")
LEAK_PATTERNS = [re.compile(rb"sk-[A-Za-z0-9_\-]{8,}"), re.compile(rb"Bearer\s+[A-Za-z0-9_\-\.]{12,}")]
TIME_MARKERS = (";TIME:", "; TIME", ";PRINT.TIME", "print_time", "PRINT TIME", ";Print time")
MATERIAL_MARKERS = (";Filament used", "Filament used", "filament_amount", "MATERIAL", ";Material", "material_g")
SKIP_SUFFIXES = (".log", ".pyc", ".zip")


class PackError(Exception):
    pass


def check_results(problems):
    if not os.path.isdir(RESULTS):
        problems.append("results/ missing")
        return
    folders = [d for d in sorted(os.listdir(RESULTS)) if os.path.isdir(os.path.join(RESULTS, d)) and not d.startswith("_")]
    if not folders:
        problems.append("results/ has no model folders")
    for name in folders:
        folder = os.path.join(RESULTS, name)
        files = os.listdir(folder)
        for required in ("project.3mf", "result.gcode"):
            if required not in files:
                problems.append("%s: missing %s" % (name, required))
        if not [f for f in files if re.match(r"chat_\d+\.png$", f)]:
            problems.append("%s: no chat_*.png" % name)
        gcode = os.path.join(folder, "result.gcode")
        if os.path.isfile(gcode):
            if os.path.getsize(gcode) == 0:
                problems.append("%s: result.gcode is empty" % name)
            else:
                with open(gcode, "r", encoding="utf-8", errors="replace") as handle:
                    head = handle.read(200000)
                with open(gcode, "rb") as handle:
                    handle.seek(max(0, os.path.getsize(gcode) - 200000))
                    tail = handle.read().decode("utf-8", "replace")
                text = head + tail
                if not any(m in text for m in TIME_MARKERS):
                    problems.append("%s: no print time line in G-code" % name)
                if not any(m in text for m in MATERIAL_MARKERS):
                    problems.append("%s: no material usage line in G-code" % name)
        project = os.path.join(folder, "project.3mf")
        if os.path.isfile(project) and not zipfile.is_zipfile(project):
            problems.append("%s: project.3mf is not a valid zip" % name)


def plugin_files():
    for base, dirs, files in os.walk(PLUGIN):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for name in files:
            yield os.path.join(base, name)


def check_plugin(problems):
    if not os.path.isfile(os.path.join(PLUGIN, "AIAssistant", "README.md")):
        problems.append("plugin/AIAssistant/README.md missing")
    for base, dirs, files in os.walk(PLUGIN):
        if "__pycache__" in dirs:
            problems.append("__pycache__ found in %s" % base)
        for name in files:
            if name.endswith(SKIP_SUFFIXES) or name == "local_settings.json":
                problems.append("forbidden file: %s" % os.path.join(base, name))


def check_leaks(problems):
    extra = os.environ.get("AI_KEY_CHECK")
    patterns = list(LEAK_PATTERNS)
    if extra:
        patterns.append(re.compile(re.escape(extra.encode("utf-8"))))
    for path in plugin_files():
        with open(path, "rb") as handle:
            data = handle.read()
        for pattern in patterns:
            if pattern.search(data):
                raise PackError("possible API key leak in %s" % path)
    for base, _, files in os.walk(RESULTS):
        for name in files:
            if name.endswith((".gcode", ".txt", ".json", ".md")):
                with open(os.path.join(base, name), "rb") as handle:
                    data = handle.read()
                for pattern in patterns:
                    if pattern.search(data):
                        raise PackError("possible API key leak in %s" % os.path.join(base, name))


def build(team):
    target = os.path.join(ROOT, "%s.zip" % team)
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in plugin_files():
            archive.write(path, os.path.relpath(path, ROOT).replace(os.sep, "/"))
        for base, dirs, files in os.walk(RESULTS):
            dirs[:] = [d for d in dirs if not d.startswith("_")]
            for name in files:
                full = os.path.join(base, name)
                archive.write(full, os.path.relpath(full, ROOT).replace(os.sep, "/"))
    return target


def main(argv):
    if len(argv) < 2:
        print("usage: pack.py <team_name>")
        return 2
    problems = []
    try:
        check_leaks(problems)
    except PackError as e:
        print("STOP: %s" % e)
        return 1
    check_results(problems)
    check_plugin(problems)
    if problems:
        for line in problems:
            print("problem: %s" % line)
        return 1
    print("created %s" % build(argv[1]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
