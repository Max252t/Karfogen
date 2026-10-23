import re
import subprocess
import sys

PATTERN = re.compile(r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore)(\([\w\-./]+\))?!?: \S.*")
ZERO = "0" * 40


def commits(rev_range):
    out = subprocess.check_output(["git", "log", "--format=%H%x1f%s%x1f%b%x1e", rev_range]).decode("utf-8")
    for record in out.split("\x1e"):
        record = record.strip("\n")
        if not record:
            continue
        sha, subject, body = (record.split("\x1f") + ["", ""])[:3]
        yield sha, subject, body


def main(argv):
    if len(argv) < 2 or argv[1].startswith(ZERO):
        print("commits: nothing to check")
        return 0
    problems = []
    for sha, subject, body in commits(argv[1]):
        if subject.startswith("Merge "):
            continue
        if not PATTERN.match(subject):
            problems.append("%s: not a Conventional Commit: %s" % (sha[:8], subject))
        if re.search(r"co-authored-by", body, re.I):
            problems.append("%s: co-author trailer is not allowed" % sha[:8])
    for line in problems:
        print(line)
    print("commits: %s" % ("FAILED" if problems else "ok"))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
