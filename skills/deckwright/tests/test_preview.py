"""preview.py serve - it may not announce a root it is not serving.

The failure this file pins was found by an unattended run of the skill
against a user's own tree: a stale `preview.py serve` from an earlier
session was still holding port 8123 rooted at another directory, a second
serve bound the same port "successfully" because the script set
SO_REUSEADDR, printed `serving <the new root>`, and answered 404 to every
URL under it. The printed line was the only evidence, and it was false.
"""

import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "preview.py"
sys.path.insert(0, str(ROOT / "scripts"))

import preview  # noqa: E402


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _tree(tmp_path, name, body):
    d = tmp_path / name
    (d / "sub").mkdir(parents=True)
    (d / "sub" / "page.html").write_text(body, encoding="utf-8")
    return d


class _Serving:
    """`preview.py serve` as a subprocess, with its announcement read back."""

    def __init__(self, root, port):
        self.proc = subprocess.Popen(
            [sys.executable, str(SCRIPT), "serve", "--root", str(root),
             "--port", str(port)],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            encoding="utf-8", bufsize=1)
        self.lines = []

    def wait_for(self, needle, timeout=20):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.proc.poll() is not None:
                self.lines += self.proc.stdout.read().splitlines()
                break
            line = self.proc.stdout.readline()
            if not line:
                break
            self.lines.append(line.rstrip("\n"))
            if needle in line:
                return True
        return any(needle in l for l in self.lines)

    def close(self):
        if self.proc.poll() is None:
            self.proc.terminate()
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.proc.kill()


@pytest.fixture
def served(tmp_path):
    running = []

    def start(root, port):
        s = _Serving(root, port)
        running.append(s)
        return s

    yield start
    for s in running:
        s.close()


def test_the_reuse_flag_that_allowed_the_hijack_is_off():
    """socketserver.TCPServer defaults to False; the script used to set the
    CLASS attribute to True, which is a POSIX TIME_WAIT convenience and on
    Windows means a second process may bind a port the first still holds."""
    assert preview._Server.allow_reuse_address is False
    import socketserver
    assert socketserver.TCPServer.allow_reuse_address is False, \
        "importing preview must not turn the flag on for every other server"


def test_serve_announces_the_resolved_absolute_root_and_the_file_it_proved(tmp_path, served):
    root = _tree(tmp_path, "good", "<p>hello</p>")
    port = _free_port()
    s = served(root, port)
    assert s.wait_for("serving"), s.lines
    text = "\n".join(s.lines)
    assert str(root.resolve()) in text, text
    assert "verified: /sub/page.html" in text, text
    # The verification line comes first: nothing is announced until the
    # bytes coming back off the port are the bytes on disk.
    assert text.index("verified:") < text.index("serving "), text


def test_a_busy_port_is_refused_rather_than_hijacked(tmp_path, served):
    """The F-8 case, end to end: one server holding the port, a second serve
    pointed at a different root. The second must refuse, not announce."""
    first = _tree(tmp_path, "first", "<p>first</p>")
    second = _tree(tmp_path, "second", "<p>second</p>")
    port = _free_port()
    holder = served(first, port)
    assert holder.wait_for("serving"), holder.lines

    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "serve", "--root", str(second),
         "--port", str(port)],
        capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert "cannot bind port %d" % port in proc.stdout
    assert "serving %s" % second.resolve() not in proc.stdout
    assert "Traceback" not in proc.stdout + proc.stderr


def test_serve_refuses_a_root_that_is_not_a_directory(tmp_path):
    import io
    stream = io.StringIO()
    assert preview.serve(tmp_path / "nowhere", _free_port(), stream=stream) == 2
    assert "no such root" in stream.getvalue()


def test_the_probe_is_the_first_file_in_sorted_breadth_first_order(tmp_path):
    (tmp_path / "b").mkdir()
    (tmp_path / "b" / "deep.txt").write_text("deep", encoding="utf-8")
    (tmp_path / "a.txt").write_text("shallow", encoding="utf-8")
    probe, url_path = preview._probe_file(tmp_path)
    assert probe == tmp_path / "a.txt"
    assert url_path == "/a.txt"


def test_a_root_with_no_file_to_probe_still_serves_but_says_so(tmp_path, served):
    root = tmp_path / "empty"
    root.mkdir()
    port = _free_port()
    s = served(root, port)
    assert s.wait_for("serving"), s.lines
    assert any("holds no file to verify" in l for l in s.lines), s.lines
