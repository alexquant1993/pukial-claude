"""What this machine can and cannot do, checked before a deck is started.

`SKILL.md`'s intake runs this as step 0, before question 1, because every
requirement it names fails late and expensively otherwise: a missing browser
is discovered after ten drafts are written, a missing `python-pptx` after the
spec is agreed, and a missing PowerPoint only when the integrity check runs
on a deck that is already built.

Three requirements are REQUIRED and one is OPTIONAL:

* **python-pptx** - REQUIRED. Without it nothing builds a `.pptx` and the
  `pptx` and `both` outputs are unreachable.
* **Pillow** - REQUIRED. The builder measures text with it, `compose_qa.py`
  crops with it, and `capture_drafts.py` verifies every capture's size with
  it.
* **A browser the capture script can drive** - REQUIRED, and it is required
  for the same reason the QA loop exists: an agent that cannot screenshot
  its drafts cannot judge them, and the deck is worse for it. Python
  Playwright is the reference route; any Chromium-family binary is the
  other, and the one the Playwright MCP server installs under
  `%LOCALAPPDATA%\\ms-playwright` counts.
* **PowerPoint through COM** - OPTIONAL, and only for a PPTX deliverable's
  file integrity (`check_pptx.ps1`) and PNG export (`export_png.ps1`). An
  `Output: html` deck needs none of it.

A missing REQUIRED item exits 1 with its consequence and the same remedies
`capture_drafts.py` prints. A missing OPTIONAL item is reported and exits 0:
it is a smaller pipeline, not a broken one.

Run: PYTHONIOENCODING=utf-8 uv run --offline --no-project --with python-pptx \\
       --with pillow python scripts/doctor.py

Pinned by tests/test_doctor.py.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import capture_drafts  # noqa: E402

REQUIRED, OPTIONAL = "REQUIRED", "OPTIONAL"

BROWSER_REMEDY = """\
  Fix one of:
    (1) `uv pip install playwright && python -m playwright install chromium`
        (on this machine PyPI is blocked by a corporate TLS interceptor:
        `invalid peer certificate: UnknownIssuer`; `--native-tls` did not
        help; a mirror or a pip.conf with the corporate CA is needed);
    (2) install Google Chrome or Microsoft Edge;
    (3) set DECKWRIGHT_BROWSER to any Chromium-family binary.
  Then re-run. Do not continue to the port without a capture."""


def probe_pptx():
    """(ok, detail) for python-pptx."""
    try:
        import pptx
    except ImportError as exc:
        return False, str(exc)
    return True, "python-pptx %s" % getattr(pptx, "__version__", "(no version)")


def probe_pillow():
    """(ok, detail) for Pillow."""
    try:
        import PIL
    except ImportError as exc:
        return False, str(exc)
    return True, "Pillow %s" % getattr(PIL, "__version__", "(no version)")


def probe_browser(environ=None):
    """(ok, detail): Python Playwright first, then a browser binary.

    The same search `capture_drafts.py` runs, called rather than restated -
    a doctor that reports a browser the capture script would not find is
    worse than no doctor.
    """
    try:
        import playwright  # noqa: F401
        return True, "Python Playwright"
    except ImportError:
        pass
    found = capture_drafts.find_browsers(environ)
    if found:
        return True, "%s (Playwright is not importable)" % found[0]
    return False, ("no Python Playwright and no Chromium-family binary; "
                   "searched %s"
                   % ", ".join(str(p) for p in
                               capture_drafts.browser_candidates(environ)))


def probe_powerpoint():
    """(ok, detail) for PowerPoint, read from the registry rather than launched.

    `PowerPoint.Application` under HKEY_CLASSES_ROOT is what
    `check_pptx.ps1`'s `New-Object -ComObject` resolves. Reading the key is
    instant; starting PowerPoint to find out whether PowerPoint is there
    would put a COM instance on the machine of every agent that runs the
    intake.
    """
    if sys.platform != "win32":
        return False, "not Windows, so there is no PowerPoint COM to reach"
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, "PowerPoint.Application"):
            return True, "PowerPoint.Application is registered for COM"
    except OSError as exc:
        return False, "PowerPoint.Application is not registered (%s)" % exc


# Each row: level, name, probe, the consequence of its absence, the remedy.
CHECKS = [
    (REQUIRED, "python-pptx", probe_pptx,
     "no .pptx can be built, so the `pptx` and `both` outputs are unreachable.",
     "  Add --with python-pptx to the uv invocation README.md gives."),
    (REQUIRED, "Pillow", probe_pillow,
     "the builder cannot measure text, compose_qa.py cannot crop, and "
     "capture_drafts.py cannot verify a capture's size.",
     "  Add --with pillow to the uv invocation README.md gives."),
    (REQUIRED, "a browser to capture drafts", probe_browser,
     "this agent cannot see its own drafts; the layout goes unreviewed and "
     "the quality of the deck suffers.",
     BROWSER_REMEDY),
    (OPTIONAL, "PowerPoint through COM", probe_powerpoint,
     "no doubled-open integrity check and no PNG export, so a `pptx` "
     "deliverable ships unverified. An `Output: html` deck needs none of it.",
     "  Run the PPTX half of the pipeline on a Windows machine with "
     "PowerPoint installed."),
]


def run(checks=None, stream=None):
    """Print one line per requirement and return the process exit code."""
    stream = sys.stdout if stream is None else stream
    checks = CHECKS if checks is None else checks
    missing_required = 0
    for level, name, probe, consequence, remedy in checks:
        ok, detail = probe()
        print("%s %s: %s - %s" % (level, name, "OK" if ok else "MISSING", detail),
              file=stream)
        if ok:
            continue
        print("  consequence: %s" % consequence, file=stream)
        print(remedy, file=stream)
        if level == REQUIRED:
            missing_required += 1
    if missing_required:
        print("DOCTOR FAILED: %d required item(s) missing. Fix them before "
              "starting a deck." % missing_required, file=stream)
        return 1
    print("DOCTOR PASSED: every required item is present.", file=stream)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__.split("\n", 1)[0],
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.parse_args(argv)
    return run()


if __name__ == "__main__":
    sys.exit(main())
