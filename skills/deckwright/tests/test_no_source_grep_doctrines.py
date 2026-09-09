"""A lint over the Phase 2 test files' own source, not a proof about their
doctrines. Phase 1's two false doctrines were both established by grepping
*.py: the autofit test grepped for an import that never existed, and the
no-colour test grepped for one spelling. Both passed while the artifact
disagreed - which is exactly the failure mode this file cannot itself avoid,
because it is built the same way: a source-text scan of *.py.

What it catches: a Phase 2 test whose CODE reads the source tree (`read_text`,
`rglob`, `importlib`, ...) to establish something, the way Phase 1's two false
doctrines did. What it cannot catch: a smell string sitting in a comment, a
docstring, or a commented-out line - `assert not re.search(smell, body)` does
not parse Python, it pattern-matches text, so "# used to call .read_text()
here" fails this check exactly as hard as calling it would, and a smell
carefully worded around (or simply commented out) passes it exactly as
cleanly as never having been there. It is a lint, catching the unremarkable
case, not a guarantee that no Phase 2 test still secretly leans on the
source tree.

This test does not ban source reading - test_style.py legitimately reads the
brand module. It bans a Phase 2 test file's own source from containing that
handful of read-the-source-tree calls at all, because every Phase 2 doctrine
has an artifact that is supposed to express it instead.
"""

from pathlib import Path

import re

PHASE_2 = ["test_merge.py", "test_fonts.py", "test_textedit.py",
           "test_pagenums.py", "test_deck.py", "test_new_version.py"]

PHASE_3 = ["test_notes.py"]

# Regexes, not literal substrings: the first draft banned the literal
# "read_text()" and test_new_version.py's own read_text(encoding="utf-8")
# slipped straight past it.
SMELLS = (r"\.read_text\(", r"\.read_bytes\(", r"\brglob\(", r"\biterdir\(",
          r"\binspect\.getsource\b", r"\bimportlib\b")

# One narrow exemption, named rather than implied: dump_text.py's round-trip
# test reads back the .txt file the script wrote, which is an artifact, not
# source.
ALLOW = {("test_new_version.py", r"\.read_text\("),
         # test_notes.py's teleprompter test writes an .html file to tmp_path
         # and reads it back to assert on the rendered artifact - the same
         # exemption as test_new_version.py's, not a read of the source tree.
         ("test_notes.py", r"\.read_text\(")}

# The lint has covered both phases since Phase 3 added test_notes.py; the two
# tests below are named for what they iterate, not for the phase that first
# needed them.
COVERED = PHASE_2 + PHASE_3


def test_no_covered_test_file_contains_a_read_the_source_tree_call():
    here = Path(__file__).resolve().parent
    for name in COVERED:
        body = (here / name).read_text(encoding="utf-8")
        for smell in SMELLS:
            if (name, smell) in ALLOW:
                continue
            assert not re.search(smell, body), (
                "%s matches %s - a package-opening doctrine must be asserted "
                "against a built package, not against the source tree"
                % (name, smell))


def test_every_covered_test_file_actually_opens_a_package():
    """Banning source-reading calls is not enough on its own. A file that
    opens nothing and asserts nothing about XML passes the ban cleanly - this
    is the other half of the same lint, not a stronger guarantee."""
    here = Path(__file__).resolve().parent
    for name in COVERED:
        body = (here / name).read_text(encoding="utf-8")
        assert "read_package(" in body or "zipfile.ZipFile(" in body, (
            "%s never opens a built package" % name)
