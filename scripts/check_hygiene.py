import io
import os
import re
import subprocess
import sys
import tokenize

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGIN = os.path.join(ROOT, "plugin")
LEAK_PATTERNS = [re.compile(r"sk-[A-Za-z0-9_\-]{16,}"), re.compile(r"Bearer\s+[A-Za-z0-9_\-\.]{20,}")]
FORBIDDEN_SUFFIXES = (".log", ".pyc", ".zip")
FORBIDDEN_NAMES = ("local_settings.json",)
TEXT_SUFFIXES = (".py", ".qml", ".js", ".json", ".html", ".css", ".md", ".sh", ".yml", ".yaml", ".txt", ".pem")


def walk(base):
    for folder, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__", "node_modules")]
        for name in files:
            yield os.path.join(folder, name)


def tracked_plugin_files():
    try:
        out = subprocess.check_output(["git", "ls-files", "plugin"], cwd=ROOT).decode("utf-8")
        return [os.path.join(ROOT, line) for line in out.splitlines() if line]
    except (OSError, subprocess.CalledProcessError):
        return list(walk(PLUGIN))


def check_forbidden(problems):
    for path in tracked_plugin_files():
        name = os.path.basename(path)
        if "__pycache__" in path or name.endswith(FORBIDDEN_SUFFIXES) or name in FORBIDDEN_NAMES:
            problems.append("forbidden file is tracked: %s" % os.path.relpath(path, ROOT))


def check_leaks(problems):
    for path in walk(ROOT):
        rel = os.path.relpath(path, ROOT)
        if rel.startswith("tests" + os.sep) or not path.endswith(TEXT_SUFFIXES):
            continue
        with io.open(path, "r", encoding="utf-8", errors="replace") as handle:
            text = handle.read()
        for pattern in LEAK_PATTERNS:
            match = pattern.search(text)
            if match:
                problems.append("possible secret in %s: %s..." % (rel, match.group(0)[:6]))


def check_python_comments(problems):
    for path in walk(PLUGIN):
        if not path.endswith(".py"):
            continue
        with open(path, "rb") as handle:
            tokens = tokenize.tokenize(handle.readline)
            for token in tokens:
                if token.type == tokenize.COMMENT:
                    problems.append("%s:%d code comment: %s" % (os.path.relpath(path, ROOT), token.start[0], token.string[:40]))


def main():
    problems = []
    check_forbidden(problems)
    check_leaks(problems)
    check_python_comments(problems)
    for line in problems:
        print(line)
    print("hygiene: %s" % ("FAILED" if problems else "ok"))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
