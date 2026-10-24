import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QML_DIR = os.path.join(ROOT, "plugin", "AIAssistant", "qml")

ALLOWED_IMPORTS = {
    "QtQuick": "2.2",
    "QtQuick.Controls": "1.1",
    "QtQuick.Controls.Styles": "1.1",
    "QtQuick.Layouts": "1.1",
    "QtQuick.Dialogs": "1.1",
    "QtQuick.Window": "2.2",
    "UM": "1.2",
    "SteSlicer": "1.0",
}
FORBIDDEN = [
    (r"\b(left|right|top|bottom)?[pP]adding\s*:", "padding properties need QtQuick 2.6+"),
    (r"\bStackLayout\b", "StackLayout needs QtQuick.Layouts 1.3"),
    (r"\bQt\.callLater\b", "Qt.callLater needs Qt 5.8"),
    (r"\bBusyIndicator\b", "BusyIndicator needs QtQuick.Controls 1.3"),
    (r"\bfunction on[A-Z]\w*\s*\(", "function-style Connections handlers need Qt 5.15"),
    (r"\bXMLHttpRequest\b", "the native UI must not use HTTP"),
    (r"\bfetch\s*\(", "the native UI must not use HTTP"),
    (r"https?://(127\.0\.0\.1|localhost)", "the native UI must not talk to the local server"),
    (r"\blet\s+\w+\s*=", "use var: the Qt 5.10 JavaScript engine is ES5"),
    (r"=>", "arrow functions are not supported by the Qt 5.10 JavaScript engine"),
    (r"`", "template literals are not supported by the Qt 5.10 JavaScript engine"),
    (r"^\s*property\s+\w+\s+[A-Z]\w*\s*:", "property names must start with a lower case letter"),
]


def check_file(path):
    problems = []
    name = os.path.basename(path)
    with open(path, "r", encoding="utf-8") as handle:
        lines = handle.read().split("\n")
    for number, line in enumerate(lines, 1):
        stripped = line.strip()
        match = re.match(r'import\s+([\w.]+)\s+([\d.]+)', stripped)
        if match:
            module, version = match.groups()
            allowed = ALLOWED_IMPORTS.get(module)
            if allowed is None:
                problems.append("%s:%d import of %s is not allowed" % (name, number, module))
            elif tuple(int(p) for p in version.split(".")) > tuple(int(p) for p in allowed.split(".")):
                problems.append("%s:%d %s %s is newer than %s" % (name, number, module, version, allowed))
            continue
        if stripped.startswith("import") and stripped not in ('import "."',):
            problems.append("%s:%d unexpected import: %s" % (name, number, stripped))
            continue
        if stripped.startswith("//"):
            continue
        for pattern, reason in FORBIDDEN:
            if re.search(pattern, line):
                problems.append("%s:%d %s" % (name, number, reason))
    return problems


def check_qmldir():
    problems = []
    listed = set()
    with open(os.path.join(QML_DIR, "qmldir"), "r", encoding="utf-8") as handle:
        for line in handle:
            parts = line.split()
            if parts:
                listed.add(parts[-1])
    for name in os.listdir(QML_DIR):
        if name.endswith(".qml") and name != "AssistantWindow.qml" and name not in listed:
            problems.append("qmldir does not list %s" % name)
    for name in listed:
        if not os.path.isfile(os.path.join(QML_DIR, name)):
            problems.append("qmldir lists missing file %s" % name)
    return problems


def main():
    problems = check_qmldir()
    for name in sorted(os.listdir(QML_DIR)):
        if name.endswith(".qml"):
            problems.extend(check_file(os.path.join(QML_DIR, name)))
    for line in problems:
        print(line)
    print("qml static check: %s" % ("FAILED" if problems else "ok"))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
