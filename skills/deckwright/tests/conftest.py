"""Anchor the suite to the repository root.

Several tests reach for repository-relative paths - the brand's fonts, the
scripts they invoke as subprocesses, and the source tree that the autofit
doctrine test walks. Run from anywhere else, those tests would silently scan
the wrong tree and pass for the wrong reason.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True, scope="session")
def _repo_root():
    previous = Path.cwd()
    os.chdir(ROOT)
    yield ROOT
    os.chdir(previous)


@pytest.fixture(scope="session")
def template(tmp_path_factory):
    """A freshly generated template, built for the session.

    Never `out/template.pptx`: the gate runs the unit tests before it builds
    the template, so a hardcoded path fails on a clean checkout, and on a
    dirty tree it silently measures against whatever the last run left there.
    """
    out = tmp_path_factory.mktemp("tpl") / "template.pptx"
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "make_template.py"),
                        "--brand", "relay", "--out", str(out)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    return out
