import os
import sys
import unittest

import support

SCRIPTS = os.path.join(support.ROOT, "scripts")
sys.path.insert(0, SCRIPTS)
import check_commits


class CheckCommitsTest(unittest.TestCase):
    def test_conventional_subjects(self):
        for subject in ("feat: add chat", "fix(ui): align buttons", "feat!: change format", "ci: add workflow"):
            self.assertTrue(check_commits.PATTERN.match(subject), subject)

    def test_non_conventional_subjects(self):
        for subject in ("Новый дизайн", "update stuff", "fix:no space", "Feat: capital"):
            self.assertFalse(check_commits.PATTERN.match(subject), subject)

    def test_ignore_by_prefix(self):
        self.assertTrue(check_commits.is_ignored("F79F6468474F", ["f79f6468"]))
        self.assertFalse(check_commits.is_ignored("abc12345", ["f79f6468"]))

    def test_known_bad_commit_is_listed(self):
        prefixes = check_commits.ignored_prefixes()
        self.assertIn("f79f6468474fbf48eccad0979a43fc390cc37d3f", prefixes)


if __name__ == "__main__":
    unittest.main()
