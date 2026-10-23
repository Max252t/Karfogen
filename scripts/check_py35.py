import ast
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    failures = []
    for base, _, files in os.walk(os.path.join(ROOT, "plugin")):
        if "__pycache__" in base:
            continue
        for name in files:
            if not name.endswith(".py"):
                continue
            path = os.path.join(base, name)
            with open(path, "rb") as handle:
                source = handle.read()
            try:
                ast.parse(source, path, feature_version=(3, 5))
            except SyntaxError as e:
                failures.append("%s:%s %s" % (path, e.lineno, e.msg))
    for line in failures:
        print(line)
    print("python 3.5 syntax: %s" % ("FAILED" if failures else "ok"))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
