"""doctor.py - what this machine can do, said before a deck is started.

Every probe is replaced here, so the verdicts are pinned rather than the
machine the suite happens to run on. The one thing checked against the real
machine is that the CLI runs and says something about each requirement.
"""

import io
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "doctor.py"
sys.path.insert(0, str(ROOT / "scripts"))

import capture_drafts as cd  # noqa: E402
import doctor  # noqa: E402


def _row(level, name, ok, detail="detail"):
    return (level, name, lambda: (ok, detail),
            "the consequence of losing %s" % name, "  the remedy for %s" % name)


def _run(rows):
    stream = io.StringIO()
    code = doctor.run(rows, stream=stream)
    return code, stream.getvalue()


def test_everything_present_passes():
    code, out = _run([_row(doctor.REQUIRED, "python-pptx", True, "1.0.2"),
                      _row(doctor.OPTIONAL, "PowerPoint", True, "registered")])
    assert code == 0
    assert "REQUIRED python-pptx: OK - 1.0.2" in out
    assert "OPTIONAL PowerPoint: OK - registered" in out
    assert "DOCTOR PASSED" in out


def test_a_missing_required_item_fails_with_its_consequence_and_its_remedy():
    """Exit non-zero, because the intake runs this at step 0 and a red step
    the agent can read past is the silence this session's ruling ended."""
    code, out = _run([_row(doctor.REQUIRED, "Pillow", False, "no module")])
    assert code == 1
    assert "REQUIRED Pillow: MISSING - no module" in out
    assert "consequence: the consequence of losing Pillow" in out
    assert "the remedy for Pillow" in out
    assert "DOCTOR FAILED: 1 required item(s) missing" in out


def test_a_missing_optional_item_is_reported_and_still_passes():
    """PowerPoint is optional because an `Output: html` deck needs none of
    it: a smaller pipeline, not a broken one."""
    code, out = _run([_row(doctor.OPTIONAL, "PowerPoint", False, "not registered")])
    assert code == 0
    assert "OPTIONAL PowerPoint: MISSING - not registered" in out
    assert "consequence: the consequence of losing PowerPoint" in out
    assert "DOCTOR PASSED" in out


def test_every_missing_required_item_is_counted_not_just_the_first():
    code, out = _run([_row(doctor.REQUIRED, "a", False),
                      _row(doctor.REQUIRED, "b", False),
                      _row(doctor.OPTIONAL, "c", False)])
    assert code == 1
    assert "DOCTOR FAILED: 2 required item(s) missing" in out


def test_the_shipped_checks_are_the_four_the_skill_names():
    """python-pptx, Pillow and a browser are REQUIRED; PowerPoint is not.
    SKILL.md's Requirements block says exactly this, and a check that moved
    level without the block moving is a skill telling a user the wrong
    thing."""
    levels = {name: level for level, name, _, _, _ in doctor.CHECKS}
    assert levels == {
        "python-pptx": doctor.REQUIRED,
        "Pillow": doctor.REQUIRED,
        "a browser to capture drafts": doctor.REQUIRED,
        "PowerPoint through COM": doctor.OPTIONAL,
    }


def test_every_check_carries_a_consequence_and_a_remedy():
    """A verdict with no consequence is a line nobody acts on."""
    for level, name, probe, consequence, remedy in doctor.CHECKS:
        assert callable(probe), name
        assert len(consequence) > 20 and consequence.endswith("."), name
        assert remedy.strip(), name


def test_the_browser_probe_prefers_playwright_and_falls_back_to_a_binary(monkeypatch, tmp_path):
    """The same two routes capture_drafts.py tries, in the same order."""
    binary = tmp_path / "chrome.exe"
    binary.write_bytes(b"MZ")
    monkeypatch.setattr(cd, "find_browsers", lambda environ=None: [binary])
    ok, detail = doctor.probe_browser()
    assert ok
    # Whichever route this machine has, the detail names it.
    assert detail == "Python Playwright" or str(binary) in detail


def test_the_browser_probe_fails_when_there_is_neither(monkeypatch):
    monkeypatch.setitem(sys.modules, "playwright", None)
    monkeypatch.setattr(cd, "find_browsers", lambda environ=None: [])
    ok, detail = doctor.probe_browser({"LOCALAPPDATA": "nowhere"})
    assert not ok
    assert "no Python Playwright and no Chromium-family binary" in detail
    assert "searched" in detail and "ms-playwright" in detail


def test_the_browser_probe_runs_capture_drafts_own_search(monkeypatch):
    """A doctor that reports a browser the capture script would not find is
    worse than no doctor, so it calls that search rather than restating it."""
    monkeypatch.setitem(sys.modules, "playwright", None)
    called = []
    monkeypatch.setattr(cd, "find_browsers",
                        lambda environ=None: called.append(environ) or [])
    doctor.probe_browser({"LOCALAPPDATA": "x"})
    assert called == [{"LOCALAPPDATA": "x"}]


def test_the_browser_remedy_is_the_capture_scripts_own_three(monkeypatch):
    """One set of instructions. Two that drift is how a user is told to
    install something that would not have helped."""
    for needle in ("playwright install chromium", "Google Chrome or Microsoft Edge",
                   "DECKWRIGHT_BROWSER",
                   "Do not continue to the port without a capture."):
        assert needle in doctor.BROWSER_REMEDY, needle
        assert needle in cd.UNAVAILABLE, needle


def test_the_powerpoint_probe_never_launches_powerpoint():
    """It reads HKEY_CLASSES_ROOT. Starting PowerPoint to find out whether
    PowerPoint is there would leave a COM instance on the machine of every
    agent that runs the intake."""
    source = (ROOT / "scripts" / "doctor.py").read_text(encoding="utf-8")
    body = source.split("def probe_powerpoint")[1].split("\n# Each row")[0]
    assert "winreg" in body
    assert "Dispatch" not in body and "EnsureDispatch" not in body


def test_the_powerpoint_probe_says_not_windows_off_windows(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    ok, detail = doctor.probe_powerpoint()
    assert not ok and "not Windows" in detail


def test_the_cli_reports_every_requirement_on_this_machine():
    proc = subprocess.run(
        [sys.executable, str(SCRIPT)], capture_output=True, text=True,
        encoding="utf-8", cwd=str(ROOT))
    assert "Traceback" not in proc.stdout + proc.stderr
    for _, name, _, _, _ in doctor.CHECKS:
        assert name in proc.stdout, name
    assert ("DOCTOR PASSED" in proc.stdout) == (proc.returncode == 0)
