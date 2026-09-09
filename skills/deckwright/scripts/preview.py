"""Serve a directory and optionally capture a page headlessly.

Serve from a root high enough that every relative CSS @import resolves. An
@import resolves against the importing stylesheet's own URL, so a stylesheet
reaching its tokens through ../../ will 404 silently when the server is
rooted at the slide directory - and the slide renders unstyled, with no
error anywhere.

Run: PYTHONIOENCODING=utf-8 uv run --offline --no-project python \
       scripts/preview.py serve --root . --port 8123

     PYTHONIOENCODING=utf-8 uv run --no-project --with playwright python \
       scripts/preview.py capture \
       http://127.0.0.1:8123/templates/iconsheet.html \
       --out out/iconsheet.png --width 640 --height 160

`capture` is the one command in this repository that drops `--offline`:
`--offline` cannot fetch Playwright, and Playwright then has a browser of its
own to download. Any browser driven to the same viewport at device scale 1
does the same job, and `capture` prints exactly that instead of failing
silently.

`serve` announces nothing until it has proved what it is serving. It used to
set `socketserver.TCPServer.allow_reuse_address = True`, which is a POSIX
TIME_WAIT convenience and on Windows means SO_REUSEADDR lets a second process
bind a port a first process is still listening on - the first listener keeps
answering. A stale preview server rooted at another tree therefore made this
one bind "successfully", print a reassuring line naming a root it was not
serving, and answer 404 to every URL under it. So: the reuse flag is off, a
busy port is a clear refusal rather than a silent hijack, and after binding
the server fetches one file it knows is under the root and compares the bytes
before it prints anything.
"""

import argparse
import functools
import http.server
import socketserver
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

# Never opened as a probe: reading one could be slow or huge, and the probe
# runs on every serve.
PROBE_MAX_BYTES = 200_000


class _Server(socketserver.TCPServer):
    # Explicit, and the point of the fix: with SO_REUSEADDR set, a second
    # server binds a port another process holds and answers nothing.
    allow_reuse_address = False


def _probe_file(root):
    """One small file under `root`, with its URL path, or (None, None).

    Deterministic - sorted, breadth-first from the root - so two runs against
    the same tree probe the same file, and so a tree whose first file is a
    100 MB video is not the one read.
    """
    dirs = [root]
    while dirs:
        current = dirs.pop(0)
        try:
            entries = sorted(current.iterdir(), key=lambda p: p.name)
        except OSError:
            continue
        for entry in entries:
            if entry.is_file() and 0 < entry.stat().st_size <= PROBE_MAX_BYTES:
                rel = entry.relative_to(root).as_posix()
                return entry, "/" + urllib.parse.quote(rel)
        dirs += [e for e in entries if e.is_dir() and not e.name.startswith(".")]
    return None, None


def _verify(port, probe, url_path):
    """Fetch `url_path` and compare it with the file on disk.

    Returns None when the served bytes are the file's, or a sentence saying
    what answered instead. This is what makes the announced root true.
    """
    url = "http://127.0.0.1:%d%s" % (port, url_path)
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            served = response.read()
    except urllib.error.HTTPError as exc:
        return ("%s came back %s: something else is listening on port %d"
                % (url, exc.code, port))
    except OSError as exc:
        return "%s could not be fetched (%s)" % (url, exc)
    if served != probe.read_bytes():
        return ("%s did not serve %s: another server is answering on port %d"
                % (url, probe, port))
    return None


def serve(root, port, stream=None):
    """Bind, prove the root, then announce and block. Non-zero on refusal."""
    stream = sys.stdout if stream is None else stream
    root = Path(root).resolve()
    if not root.is_dir():
        print("preview: no such root: %s" % root, file=stream)
        return 2

    handler = functools.partial(http.server.SimpleHTTPRequestHandler,
                                directory=str(root))
    try:
        httpd = _Server(("127.0.0.1", port), handler)
    except OSError as exc:
        print("preview: cannot bind port %d: %s\n"
              "Another server is already holding it - stop it, or pass a "
              "different --port. This is a refusal on purpose: binding a "
              "port somebody else holds serves nothing and reports success."
              % (port, exc), file=stream)
        return 2

    with httpd:
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        probe, url_path = _probe_file(root)
        if probe is None:
            print("preview: %s holds no file to verify the root with" % root,
                  file=stream)
        else:
            problem = _verify(port, probe, url_path)
            if problem is not None:
                httpd.shutdown()
                print("preview: %s" % problem, file=stream)
                return 2
            print("verified: %s serves %s" % (url_path, probe), file=stream)
        print("serving %s at http://127.0.0.1:%d/ (ctrl-c to stop)" % (root, port),
              file=stream)
        stream.flush()
        try:
            thread.join()
        except KeyboardInterrupt:
            httpd.shutdown()
    return 0


def capture(url, out, width, height, scale):
    """Capture with Playwright if it is available.

    Slide drafts are captured at scale 1 so the DOM geometry read back is
    unscaled. The icon sheet does not need a device-scale trick: its cells
    are authored large, and the cropper derives cell size from the image.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright is not installed. Either install it, or open %s in a\n"
              "browser at %dx%d and save the screenshot to %s - the cropper does\n"
              "not care which tool produced the image."
              % (url, width, height, out))
        return 1
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": width, "height": height},
                                device_scale_factor=scale)
        page.goto(url)
        page.wait_for_timeout(300)
        page.screenshot(path=str(out),
                        clip={"x": 0, "y": 0, "width": width, "height": height})
        browser.close()
    print("captured", out)
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("serve")
    s.add_argument("--root", default=".", type=Path)
    s.add_argument("--port", default=8123, type=int)
    c = sub.add_parser("capture")
    c.add_argument("url")
    c.add_argument("--out", required=True)
    c.add_argument("--width", type=int, default=1280)
    c.add_argument("--height", type=int, default=720)
    c.add_argument("--scale", type=int, default=1)
    a = ap.parse_args()
    if a.cmd == "serve":
        raise SystemExit(serve(a.root, a.port))
    raise SystemExit(capture(a.url, a.out, a.width, a.height, a.scale))
