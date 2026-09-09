"""Screenshot every slide draft to sNN.png, so an agent can see its own work.

`scripts/compose_qa.py` crops the same strip out of every slide and stacks
the crops; a footer five pixels low on slide 17 is invisible slide by slide
and obvious in a stack. Its input has always been `export_png.ps1`'s PPTX
export, which needs Windows and PowerPoint. An HTML deck has neither, and it
has the same failure mode - so this writes the same `sNN.png` filenames, at
the same 1600x900 the PPTX export writes, out of the drafts themselves.
Everything downstream is unchanged.

Each draft is served over a loopback HTTP server rooted at `--root` and
opened at 1280x720, then written at `--scale` (default 1.25, which is
1600x900 - the factor `references/05-qa.md`'s crop boxes are derived with).
Served rather than opened as a `file://` URL for the reason
`references/02-html-stage.md` gives: a CSS `@import` resolves against the
importing stylesheet's own URL, and the root has to be high enough that
`../../` still resolves. The server is `preview.py`'s, root proof included:
a server answering 404 under an announced root would capture ten unstyled
slides that look like a design decision.

**Seeing the drafts is a requirement of this pipeline, not a nicety.** An
agent that cannot screenshot its drafts cannot judge them, and the deck is
worse for it. So every route is tried before anything gives up:

1. **Python Playwright**, when it is importable.
2. **A Chromium-family browser binary driven directly**, which needs no
   Python package at all - `--headless=new --screenshot=<png>` against the
   served URL. The search order is in `browser_candidates`, and
   `DECKWRIGHT_BROWSER` overrides it.
3. **Nothing.** Then this exits non-zero with `CAPTURE UNAVAILABLE`, the
   three remedies, and the real diagnostics for every route it tried. It
   does not print a cheerful skip and let the gate stay green.

`scripts/doctor.py` reports the same browser search as a REQUIRED item, one
step before the intake, so the failure is met before a deck is started
rather than after ten drafts are written.

Run: PYTHONIOENCODING=utf-8 uv run --offline --no-project --with python-pptx \\
       --with pillow python scripts/capture_drafts.py \\
       --drafts examples/ai-horizon/drafts --out out/ai-horizon/png_html \\
       --root . --expect 10

That invocation captures through the browser binary route on a machine with
no Playwright, which is this one; `--url http://127.0.0.1:8123` uses a server
that is already running instead of starting one.

Pinned by tests/test_capture_drafts.py.
"""

import argparse
import functools
import http.server
import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import preview  # noqa: E402
from build_html_deck import DraftError, slide_files  # noqa: E402

CANVAS_W, CANVAS_H = 1280, 720
# 1600x900 / 1280x720. The PPTX export writes 1600x900 and every crop box in
# the QA loop is a design coordinate times this number; a capture at another
# scale would need its own boxes.
EXPORT_SCALE = 1.25
# Per capture, not per run. A browser that hangs - which Edge does on this
# machine, a GPU-process crash then nothing - must fail over to the next
# binary rather than hang the gate.
BROWSER_TIMEOUT = 60
# Milliseconds of virtual time the browser advances before it shoots, so a
# web font still in its block period cannot render its text invisibly. See
# browser_command; the measurement is in docs/decisions.md.
FONT_WAIT_MS = 3000
BROWSER_ENV = "DECKWRIGHT_BROWSER"
PLAYWRIGHT = "Python Playwright"

UNAVAILABLE = """\
CAPTURE UNAVAILABLE: this agent cannot see its own drafts. Without screenshots
the layout is unreviewed and the quality of the deck will suffer. Fix one of:
  (1) `uv pip install playwright && python -m playwright install chromium`
      (on this machine PyPI is blocked by a corporate TLS interceptor:
      `invalid peer certificate: UnknownIssuer`; `--native-tls` did not help;
      a mirror or a pip.conf with the corporate CA is needed);
  (2) install Google Chrome or Microsoft Edge;
  (3) set DECKWRIGHT_BROWSER to any Chromium-family binary.
Then re-run. Do not continue to the port without a capture."""


class CaptureError(ValueError):
    """A capture this script will not pretend it made."""


def export_size(scale):
    """The exact pixel size a capture at `scale` must come out at.

    At scale 1 that is the 1280x720 canvas itself; at the default 1.25 it is
    the 1600x900 `export_png.ps1` writes. Checked against every PNG before
    it is counted, because a browser that rendered at the wrong device scale
    writes a plausible image that every crop box in `references/05-qa.md`
    then misses.
    """
    return int(round(CANVAS_W * scale)), int(round(CANVAS_H * scale))


# ---- the server -------------------------------------------------------------

class _Quiet(http.server.SimpleHTTPRequestHandler):
    """Counts what it serves instead of logging every line of it.

    Ten drafts fetch a hundred URLs and the log buries the capture's own
    output. What is worth reporting is the ones that came back 404: a
    stylesheet, a font or an icon that did not resolve renders a slide that
    is subtly wrong and says nothing about it, which is the exact failure
    the serving root exists to prevent. `/favicon.ico` is excluded - every
    page load asks for one and no draft has one.
    """

    def log_message(self, fmt, *args):
        pass

    def send_error(self, code, message=None, explain=None):
        if code == 404 and self.path != "/favicon.ico":
            self.server.missing.append(self.path)
        super().send_error(code, message, explain)


def serve_in_thread(root):
    """A loopback server on an ephemeral port, its root proved. (httpd, port).

    Port 0, so a run never collides with a `preview.py serve` the user left
    running. `preview._Server` and `preview._verify` rather than a second
    copy: the root proof is what stops a capture of ten slides that fetched
    nothing.
    """
    root = Path(root).resolve()
    if not root.is_dir():
        raise CaptureError("no such serving root: %s" % root)
    handler = functools.partial(_Quiet, directory=str(root))
    httpd = preview._Server(("127.0.0.1", 0), handler)
    httpd.missing = []
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    port = httpd.server_address[1]
    probe, url_path = preview._probe_file(root)
    if probe is not None:
        problem = preview._verify(port, probe, url_path)
        if problem is not None:
            httpd.shutdown()
            httpd.server_close()
            raise CaptureError(problem)
    return httpd, port


def draft_urls(drafts, root, port=None, base=None):
    """[(number, url, out_name)] for every draft, in slide order."""
    if base is None:
        base = "http://127.0.0.1:%d" % port
    base = base.rstrip("/")
    root = Path(root).resolve()
    out = []
    for index, path in enumerate(slide_files(drafts), 1):
        rel = path.resolve().relative_to(root).as_posix()
        out.append((index, "%s/%s" % (base, rel), "s%02d.png" % index))
    return out


# ---- finding a browser ------------------------------------------------------

def _version_key(path):
    """The trailing integer of `chromium-1217`, so the newest build wins."""
    tail = path.name.rsplit("-", 1)[-1]
    return int(tail) if tail.isdigit() else -1


def _ms_playwright(base, pattern, *tails):
    """Every installed build of one ms-playwright package, newest first.

    The Playwright MCP server installs these, so a machine that has never
    run `pip install playwright` can still hold a Chromium. The tail differs
    between packages and between Playwright versions - the headless shell
    moved from `chrome-win64/headless_shell.exe` to
    `chrome-headless-shell-win64/chrome-headless-shell.exe` - so both are
    named and whichever exists is used.
    """
    out = []
    if base.is_dir():
        for build in sorted(base.glob(pattern), key=_version_key, reverse=True):
            out += [build / tail for tail in tails]
    # Nothing installed: return the pattern itself, unexpanded. It cannot be
    # a file, so `find_browsers` drops it - but `CAPTURE UNAVAILABLE` lists
    # every candidate, and a diagnostic that omits the place it looked
    # hardest is the one a reader most needs.
    return out or [base / pattern / tails[0]]


def browser_candidates(environ=None):
    """Every Chromium-family binary this machine might hold, best first.

    Order is a measurement, not a preference. On this machine the
    ms-playwright Chromium captured a draft in 1.4 s while Edge hung - a
    GPU-process crash, then the timeout - so the browser Playwright itself
    would have used comes first and the system browsers come after it.
    `DECKWRIGHT_BROWSER` overrides the whole search by sitting in front of
    it. Paths are returned whether or not they exist; `find_browsers`
    filters.
    """
    env = os.environ if environ is None else environ
    out = []
    override = (env.get(BROWSER_ENV) or "").strip().strip('"')
    if override:
        out.append(Path(override))
    local = env.get("LOCALAPPDATA")
    if local:
        ms = Path(local) / "ms-playwright"
        out += _ms_playwright(ms, "chromium-*", "chrome-win64/chrome.exe")
        out += _ms_playwright(
            ms, "chromium_headless_shell-*",
            "chrome-headless-shell-win64/chrome-headless-shell.exe",
            "chrome-win64/headless_shell.exe")
    program_files = env.get("ProgramFiles")
    program_files_x86 = env.get("ProgramFiles(x86)")
    for base in (program_files, program_files_x86):
        if base:
            out.append(Path(base) / "Google/Chrome/Application/chrome.exe")
    if local:
        out.append(Path(local) / "Google/Chrome/Application/chrome.exe")
    for base in (program_files_x86, program_files):
        if base:
            out.append(Path(base) / "Microsoft/Edge/Application/msedge.exe")
    return out


def find_browsers(environ=None):
    """The candidates that are actually on disk, in order, without repeats."""
    seen, out = set(), []
    for path in browser_candidates(environ):
        key = str(path).lower()
        if key in seen or not path.is_file():
            continue
        seen.add(key)
        out.append(path)
    return out


# ---- driving one -------------------------------------------------------------

def browser_command(binary, url, png, scale, profile=None):
    """The headless invocation, measured on this machine before it was written.

    `--force-device-scale-factor` is what makes a 1280x720 window write a
    1600x900 PNG, so the DOM geometry stays the canvas the builder works on
    while the file matches the PPTX export.

    `--virtual-time-budget` is the one flag here that is not obvious, and it
    is load-bearing. `--screenshot` fires on the load event, and the load
    event does not wait for web fonts; a `@font-face` still in its block
    period renders its text **invisibly**, so the capture comes out with
    every rule, box and icon in place and not one word on it. Measured
    against `s06-toward-2050.html` on this machine: 1 blank in 8 without the
    flag, 0 in 20 with it. That failure is why the flag is here rather than
    a 300 ms sleep - and it is exactly the kind of thing only looking at the
    capture finds, which is the argument for this whole script.

    `--user-data-dir` is passed only on the retry: see `capture_with_binary`.
    """
    args = [str(binary), "--headless=new", "--disable-gpu", "--no-sandbox",
            "--hide-scrollbars",
            "--window-size=%d,%d" % (CANVAS_W, CANVAS_H),
            "--force-device-scale-factor=%s" % scale,
            "--virtual-time-budget=%d" % FONT_WAIT_MS,
            "--screenshot=%s" % png]
    if profile is not None:
        args.append("--user-data-dir=%s" % profile)
    args.append(url)
    return args


def _kill_tree(proc):
    """Kill the browser and everything it spawned.

    `Popen.kill` kills the one process; a Chromium leaves renderer and GPU
    children behind, and on the machine this was written for a hung Edge
    left both. `taskkill /T` is the only thing that clears them, and a gate
    that leaves browser processes behind on every run is its own failure.
    """
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                       capture_output=True)
    else:
        proc.kill()


def _run(args, timeout):
    """(returncode or None, output, seconds). None means it timed out."""
    started = time.time()
    proc = subprocess.Popen(args, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True,
                            encoding="utf-8", errors="replace")
    try:
        output = proc.communicate(timeout=timeout)[0]
        return proc.returncode, output or "", time.time() - started
    except subprocess.TimeoutExpired:
        _kill_tree(proc)
        try:
            proc.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        return None, "timed out after %ds" % timeout, time.time() - started


def verify_png(path, scale):
    """None when `path` is an image of exactly `export_size(scale)`.

    A sentence naming what is wrong otherwise. A browser that failed to
    render still exits 0 with no file, and one that ignored the device scale
    writes a 1280x720 PNG that every 1600x900 crop box misses by a quarter.
    """
    width, height = export_size(scale)
    if not path.exists():
        return "%s was not written" % path.name
    try:
        from PIL import Image
        with Image.open(path) as image:
            size = image.size
    except (OSError, ImportError) as exc:
        return "%s is not a readable image (%s)" % (path.name, exc)
    if size != (width, height):
        return ("%s is %dx%d, not the %dx%d a capture at scale %s must be"
                % (path.name, size[0], size[1], width, height, scale))
    return None


def capture_with_binary(binary, jobs, out_dir, scale=EXPORT_SCALE,
                        timeout=BROWSER_TIMEOUT):
    """Screenshot every job with one browser binary. None, or what went wrong.

    Two attempts per slide, and the second is not a repeat: it adds a
    throwaway `--user-data-dir` under the output directory, which is what a
    Chrome or an Edge the user has open needs, since a running profile
    refuses a second instance. It is the *retry* rather than the default
    because the ms-playwright Chromium does the opposite - measured on this
    machine, it captures in 1.4 s with no profile flag and hangs until the
    timeout with one.
    """
    profile = Path(out_dir) / "_browser_profile"
    try:
        for _, url, name in jobs:
            png = Path(out_dir) / name
            problem = None
            for attempt in (None, profile):
                if png.exists():
                    png.unlink()
                code, output, seconds = _run(
                    browser_command(binary, url, png, scale, attempt), timeout)
                problem = verify_png(png, scale)
                if problem is None:
                    break
                problem = ("%s (exit %s, %.1fs%s): %s"
                           % (name, "timeout" if code is None else code,
                              seconds, "" if attempt is None else ", own profile",
                              problem))
            if problem is not None:
                return problem
            print("captured", Path(out_dir) / name)
    finally:
        shutil.rmtree(profile, ignore_errors=True)
    return None


def capture_with_playwright(jobs, out_dir, scale=EXPORT_SCALE):
    """The reference route. None, or what went wrong."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        return "not importable: %s" % exc
    with sync_playwright() as play:
        browser = play.chromium.launch()
        page = browser.new_page(
            viewport={"width": CANVAS_W, "height": CANVAS_H},
            device_scale_factor=scale)
        try:
            for _, url, name in jobs:
                png = Path(out_dir) / name
                page.goto(url)
                # The same font race `--virtual-time-budget` covers on the
                # binary route: a face still in its block period renders its
                # text invisibly, and the load event does not wait for one.
                page.evaluate("() => document.fonts.ready")
                page.wait_for_timeout(200)
                page.screenshot(path=str(png),
                                clip={"x": 0, "y": 0,
                                      "width": CANVAS_W, "height": CANVAS_H})
                problem = verify_png(png, scale)
                if problem is not None:
                    return problem
                print("captured", png)
        finally:
            browser.close()
    return None


# ---- the report -------------------------------------------------------------

def manual_instruction(jobs, out_dir, scale):
    """The last resort: drive a browser by hand, precisely enough to do it."""
    width, height = export_size(scale)
    lines = ["Last resort, until one of those is done - any browser driven to "
             "a %dx%d" % (CANVAS_W, CANVAS_H),
             "viewport, each shot saved at %dx%d (scale %s):"
             % (width, height, scale),
             ""]
    for _, url, name in jobs:
        lines.append("  %s  ->  %s" % (url, Path(out_dir) / name))
    return "\n".join(lines)


def unavailable(tried, jobs, out_dir, scale):
    """The one message, printed once, with the real diagnostics under it."""
    lines = [UNAVAILABLE, "", "Tried, in order:"]
    for route, seconds, problem in tried:
        lines.append("  %s (%.1fs): %s" % (route, seconds, problem))
    lines += ["", manual_instruction(jobs, out_dir, scale)]
    return "\n".join(lines)


# ---- the entry point --------------------------------------------------------

def capture(drafts, out_dir, root=".", scale=EXPORT_SCALE, expect=None,
            url=None, environ=None, timeout=BROWSER_TIMEOUT):
    """Write one PNG per draft, by whichever route works. Process exit code."""
    files = slide_files(drafts)
    if expect is not None and len(files) != expect:
        print("FAIL: expected %d draft(s) in %s, found %d"
              % (expect, drafts, len(files)))
        return 1
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    tried, route, httpd = [], None, None
    try:
        if url is None:
            httpd, port = serve_in_thread(root)
            jobs = draft_urls(drafts, root, port)
        else:
            jobs = draft_urls(drafts, root, base=url)

        started = time.time()
        problem = capture_with_playwright(jobs, out_dir, scale)
        if problem is None:
            route = PLAYWRIGHT
        else:
            tried.append((PLAYWRIGHT, time.time() - started, problem))
            for binary in find_browsers(environ):
                started = time.time()
                problem = capture_with_binary(binary, jobs, out_dir, scale,
                                              timeout)
                if problem is None:
                    route = str(binary)
                    break
                tried.append((str(binary), time.time() - started, problem))
            else:
                if not tried[1:]:
                    tried.append(("browser binary", 0.0,
                                  "no Chromium-family binary found; searched "
                                  + ", ".join(str(p) for p in
                                              browser_candidates(environ))))
    finally:
        if httpd is not None:
            missing = sorted(set(httpd.missing))
            httpd.shutdown()
            httpd.server_close()
            if missing:
                print("WARNING: %d URL(s) came back 404 while capturing, so "
                      "something on a slide did not render: %s"
                      % (len(missing), ", ".join(missing)))

    if route is None:
        print(unavailable(tried, jobs, out_dir, scale))
        return 1
    # Printed on success too. A route that failed and was recovered from is
    # the evidence for the next run's timeout budget, and dropping it once
    # the capture worked is how a browser that fails half the time looks
    # like one that always works.
    for name, seconds, problem in tried:
        print("route failed, moved on: %s (%.1fs): %s" % (name, seconds, problem))
    print("CAPTURE OK via %s: %d slide(s) -> %s" % (route, len(files), out_dir))
    if route != PLAYWRIGHT:
        print("RULING: record on the spec's ledger that these captures came "
              "from this browser rather than from Python Playwright - the "
              "drafts were judged through a different renderer than the "
              "reference one.")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__.split("\n", 1)[0],
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--drafts", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--root", type=Path, default=Path("."),
                    help="serving root: high enough that every @import resolves")
    ap.add_argument("--scale", type=float, default=EXPORT_SCALE,
                    help="device scale factor (default 1.25 = 1600x900)")
    ap.add_argument("--expect", type=int, default=None,
                    help="exact number of drafts that must be found")
    ap.add_argument("--url", default=None,
                    help="base URL of a server that is already running; "
                         "without it this starts one on a free port")
    ap.add_argument("--timeout", type=int, default=BROWSER_TIMEOUT,
                    help="seconds one browser gets per slide (default 60)")
    args = ap.parse_args(argv)
    try:
        return capture(args.drafts, args.out, args.root, args.scale,
                       args.expect, args.url, timeout=args.timeout)
    except (DraftError, CaptureError, OSError, ValueError) as exc:
        print("FAIL: %s" % exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
