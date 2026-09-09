"""capture_drafts.py - an agent that cannot see its drafts must say so loudly.

Seeing the drafts is a requirement of this pipeline, not a nicety, so the
script tries Python Playwright, then every Chromium-family binary on the
machine, and only then fails - with one unmissable message and the real
diagnostics per route. This file pins the search order, the env override,
the timeout and failover, the size verification, the exact-count rule and
that message.

Nothing here reaches the network and nothing here needs a real browser,
except `test_a_real_headless_browser_captures_a_1600x900_png`, which runs
the genuine capture when a binary is present and skips with a reason
naming what was searched when none is.
"""

import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "capture_drafts.py"
sys.path.insert(0, str(ROOT / "scripts"))

import capture_drafts as cd  # noqa: E402

NO_PLAYWRIGHT = "not importable: pinned off in this test"


@pytest.fixture
def tree(tmp_path):
    drafts = tmp_path / "deck" / "drafts"
    drafts.mkdir(parents=True)
    for name in ("s01-cover.html", "s02-body.html", "s10-last.html"):
        (drafts / name).write_text(
            "<html><body><div class=slide>x</div></body></html>",
            encoding="utf-8")
    return tmp_path, drafts


@pytest.fixture
def no_playwright(monkeypatch):
    """Route a off, whether or not the machine running the tests has it."""
    monkeypatch.setattr(cd, "capture_with_playwright",
                        lambda jobs, out_dir, scale=cd.EXPORT_SCALE: NO_PLAYWRIGHT)


def _fake_machine(tmp_path):
    """A filesystem holding one of everything the search knows about."""
    local = tmp_path / "local"
    program_files = tmp_path / "pf"
    program_files_x86 = tmp_path / "pf86"
    paths = {
        "chromium_new": local / "ms-playwright/chromium-1217/chrome-win64/chrome.exe",
        "chromium_old": local / "ms-playwright/chromium-1200/chrome-win64/chrome.exe",
        "shell": local / ("ms-playwright/chromium_headless_shell-1217/"
                          "chrome-headless-shell-win64/chrome-headless-shell.exe"),
        "chrome": program_files / "Google/Chrome/Application/chrome.exe",
        "chrome_x86": program_files_x86 / "Google/Chrome/Application/chrome.exe",
        "chrome_local": local / "Google/Chrome/Application/chrome.exe",
        "edge_x86": program_files_x86 / "Microsoft/Edge/Application/msedge.exe",
        "edge": program_files / "Microsoft/Edge/Application/msedge.exe",
    }
    for path in paths.values():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"MZ")
    env = {"LOCALAPPDATA": str(local), "ProgramFiles": str(program_files),
           "ProgramFiles(x86)": str(program_files_x86)}
    return env, paths


# ---- the URLs ---------------------------------------------------------------

def test_the_urls_follow_slide_order_and_name_the_export_filenames(tree):
    """`sNN.png` is what export_png.ps1 writes and what compose_qa.py globs,
    so an HTML capture is a drop-in for a PowerPoint export."""
    root, drafts = tree
    urls = cd.draft_urls(drafts, root, 8123)
    # Numbered by POSITION, not by the draft's own NN: compose_qa.py's
    # --slides and --expect count slides, and lint_deck's draft positions do
    # the same, so `s10-last.html` is the third slide and writes s03.png.
    assert [name for _, _, name in urls] == ["s01.png", "s02.png", "s03.png"]
    assert [n for n, _, _ in urls] == [1, 2, 3]
    assert urls[0][1] == "http://127.0.0.1:8123/deck/drafts/s01-cover.html"
    assert urls[2][1].endswith("s10-last.html"), "numeric order, not lexical"


def test_a_given_base_url_is_used_instead_of_a_server_of_our_own(tree):
    """`--url` is for a `preview.py serve` the user already has running."""
    root, drafts = tree
    urls = cd.draft_urls(drafts, root, base="http://127.0.0.1:8123/")
    assert urls[0][1] == "http://127.0.0.1:8123/deck/drafts/s01-cover.html"


# ---- the browser search -----------------------------------------------------

def test_the_browser_search_order_is_the_measured_one(tmp_path):
    """Order is a measurement: on the machine this was written for the
    ms-playwright Chromium captured a draft in 1.4 s and Edge hung, so the
    browser Playwright itself would use comes first. Newest build of a
    package wins - 1217 before 1200 - and the system browsers come after."""
    env, paths = _fake_machine(tmp_path)
    assert cd.find_browsers(env) == [
        paths["chromium_new"], paths["chromium_old"], paths["shell"],
        paths["chrome"], paths["chrome_x86"], paths["chrome_local"],
        paths["edge_x86"], paths["edge"],
    ]


def test_the_search_skips_what_is_not_on_disk(tmp_path):
    env, paths = _fake_machine(tmp_path)
    paths["chromium_new"].unlink()
    paths["shell"].unlink()
    assert cd.find_browsers(env)[0] == paths["chromium_old"]
    assert paths["shell"] not in cd.find_browsers(env)


def test_a_machine_with_no_browser_finds_none_and_still_names_what_it_looked_for(tmp_path):
    env = {"LOCALAPPDATA": str(tmp_path / "local"),
           "ProgramFiles": str(tmp_path / "pf")}
    assert cd.find_browsers(env) == []
    named = [str(p) for p in cd.browser_candidates(env)]
    assert any("ms-playwright" in p for p in named)
    assert any("chrome.exe" in p for p in named)


def test_deckwright_browser_overrides_the_search(tmp_path):
    """One env var, in front of everything, for a browser in a place this
    script has never heard of."""
    env, paths = _fake_machine(tmp_path)
    mine = tmp_path / "elsewhere" / "my-chromium.exe"
    mine.parent.mkdir()
    mine.write_bytes(b"MZ")
    env[cd.BROWSER_ENV] = str(mine)
    found = cd.find_browsers(env)
    assert found[0] == mine
    assert found[1] == paths["chromium_new"], "the rest of the search survives"


def test_a_browser_named_twice_is_tried_once(tmp_path):
    """The override usually names a binary the search would find anyway."""
    env, paths = _fake_machine(tmp_path)
    env[cd.BROWSER_ENV] = str(paths["chrome"])
    found = cd.find_browsers(env)
    assert found.count(paths["chrome"]) == 1
    assert found[0] == paths["chrome"]


def test_the_browser_command_is_the_invocation_that_was_measured(tmp_path):
    """The flags are not decoration. `--force-device-scale-factor` is what
    makes a 1280x720 window write the 1600x900 the crop boxes are derived
    from, and `--user-data-dir` appears only when a profile is passed."""
    png = tmp_path / "s01.png"
    args = cd.browser_command("chrome.exe", "http://x/y.html", png, 1.25)
    assert args[0] == "chrome.exe" and args[-1] == "http://x/y.html"
    assert "--headless=new" in args
    assert "--window-size=1280,720" in args
    assert "--force-device-scale-factor=1.25" in args
    assert "--screenshot=%s" % png in args
    assert not any(a.startswith("--user-data-dir") for a in args)
    # The load event does not wait for web fonts, and a face still in its
    # block period renders its text invisibly - a capture with every rule
    # and box in place and not one word on it. Measured on this machine:
    # 1 blank in 8 without the flag, 0 in 20 with it.
    assert "--virtual-time-budget=%d" % cd.FONT_WAIT_MS in args
    assert cd.FONT_WAIT_MS >= 1000, "shorter than a font-display block period"
    with_profile = cd.browser_command("chrome.exe", "http://x/y.html", png,
                                      1.25, tmp_path / "prof")
    assert "--user-data-dir=%s" % (tmp_path / "prof") in with_profile


# ---- verifying a capture ----------------------------------------------------

def test_a_capture_of_the_wrong_size_is_refused(tmp_path):
    """A browser that ignored the device scale writes a plausible 1280x720
    PNG that every 1600x900 crop box in references/05-qa.md then misses."""
    png = tmp_path / "s01.png"
    Image.new("RGB", (1280, 720), "white").save(png)
    problem = cd.verify_png(png, 1.25)
    assert problem is not None and "1280x720" in problem and "1600x900" in problem
    assert cd.verify_png(png, 1) is None, "scale 1 IS the 1280x720 canvas"


def test_a_capture_that_was_never_written_is_refused(tmp_path):
    """A browser that failed to render still exits 0 with no file."""
    problem = cd.verify_png(tmp_path / "s01.png", 1.25)
    assert problem is not None and "was not written" in problem


def test_the_export_size_is_the_canvas_times_the_scale():
    assert cd.export_size(1) == (1280, 720)
    assert cd.export_size(cd.EXPORT_SCALE) == (1600, 900)


# ---- the routes -------------------------------------------------------------

def _sleeper(seconds):
    return [sys.executable, "-c", "import time; time.sleep(%d)" % seconds]


def _painter(png, size=(1600, 900)):
    return [sys.executable, "-c",
            "import sys\nfrom PIL import Image\n"
            "Image.new('RGB', (%d, %d), 'white').save(sys.argv[1])" % size,
            str(png)]


def test_a_browser_that_hangs_times_out_and_the_next_one_captures(
        tree, tmp_path, monkeypatch, no_playwright, capsys):
    """Edge hung on this machine - a GPU-process crash, then nothing - so a
    hung binary must fail over to the next rather than hang the run. Both
    attempts on the hung binary have to expire, which is what the per-capture
    timeout is for."""
    root, drafts = tree
    hangs, works = tmp_path / "hangs.exe", tmp_path / "works.exe"
    for path in (hangs, works):
        path.write_bytes(b"MZ")
    monkeypatch.setattr(cd, "find_browsers", lambda environ=None: [hangs, works])
    monkeypatch.setattr(cd, "browser_command",
                        lambda binary, url, png, scale, profile=None:
                        _sleeper(60) if binary == hangs else _painter(png))
    out = tmp_path / "png"
    assert cd.capture(drafts, out, root=root, timeout=2) == 0
    printed = capsys.readouterr().out
    assert "route failed, moved on: %s" % hangs in printed
    assert "timeout" in printed, "the hung route says it timed out"
    assert "CAPTURE OK via %s" % works in printed
    assert sorted(p.name for p in out.glob("s*.png")) == \
        ["s01.png", "s02.png", "s03.png"]


def test_a_browser_that_writes_the_wrong_size_fails_its_route(
        tree, tmp_path, monkeypatch, no_playwright, capsys):
    root, drafts = tree
    wrong, works = tmp_path / "wrong.exe", tmp_path / "works.exe"
    for path in (wrong, works):
        path.write_bytes(b"MZ")
    monkeypatch.setattr(cd, "find_browsers", lambda environ=None: [wrong, works])
    monkeypatch.setattr(cd, "browser_command",
                        lambda binary, url, png, scale, profile=None:
                        _painter(png, (800, 600)) if binary == wrong
                        else _painter(png))
    assert cd.capture(drafts, tmp_path / "png", root=root, timeout=30) == 0
    printed = capsys.readouterr().out
    assert "800x600" in printed and "CAPTURE OK via %s" % works in printed


def test_the_retry_adds_a_throwaway_profile_and_then_gives_up(
        tree, tmp_path, monkeypatch, no_playwright):
    """Two attempts per slide, and the second is not a repeat: it adds a
    `--user-data-dir` under the output directory, which is what a Chrome the
    user has open needs. It is the retry rather than the default because the
    ms-playwright Chromium hangs with one and captures in 1.4 s without."""
    root, drafts = tree
    binary = tmp_path / "b.exe"
    binary.write_bytes(b"MZ")
    seen = []
    monkeypatch.setattr(cd, "find_browsers", lambda environ=None: [binary])
    monkeypatch.setattr(cd, "browser_command",
                        lambda b, url, png, scale, profile=None:
                        seen.append(profile) or [sys.executable, "-c", "pass"])
    out = tmp_path / "png"
    assert cd.capture(drafts, out, root=root, timeout=30) == 1
    assert seen[0] is None, "the first attempt passes no profile"
    assert seen[1] == out / "_browser_profile"
    assert len(seen) == 2, "one retry, then the binary is abandoned"
    assert not (out / "_browser_profile").exists(), "the profile is thrown away"


def test_playwright_is_tried_before_any_binary(tree, tmp_path, monkeypatch, capsys):
    root, drafts = tree

    def never(*a, **kw):
        raise AssertionError("a binary was tried while Playwright worked")

    def paint_them_all(jobs, out_dir, scale=cd.EXPORT_SCALE):
        for _, _, name in jobs:
            Image.new("RGB", cd.export_size(scale), "white").save(Path(out_dir) / name)
        return None

    monkeypatch.setattr(cd, "find_browsers", never)
    monkeypatch.setattr(cd, "capture_with_playwright", paint_them_all)
    assert cd.capture(drafts, tmp_path / "png", root=root) == 0
    printed = capsys.readouterr().out
    assert "CAPTURE OK via %s" % cd.PLAYWRIGHT in printed
    assert "RULING:" not in printed, "the reference route needs no ledger entry"


def test_a_fallback_route_asks_for_a_ledger_entry(
        tree, tmp_path, monkeypatch, no_playwright, capsys):
    """A capture judged through a renderer other than the reference one is a
    ruling with a cost, and SKILL.md says to record it on the spec's ledger."""
    root, drafts = tree
    binary = tmp_path / "b.exe"
    binary.write_bytes(b"MZ")
    monkeypatch.setattr(cd, "find_browsers", lambda environ=None: [binary])
    monkeypatch.setattr(cd, "browser_command",
                        lambda b, url, png, scale, profile=None: _painter(png))
    assert cd.capture(drafts, tmp_path / "png", root=root, timeout=30) == 0
    assert "RULING: record on the spec's ledger" in capsys.readouterr().out


# ---- the message that must be impossible to miss ----------------------------

def test_no_route_at_all_fails_loudly_and_says_what_to_do(
        tree, tmp_path, monkeypatch, no_playwright, capsys):
    """The whole point of this session's ruling: silence is what ended. A
    capture that cannot happen exits non-zero and says why, once."""
    root, drafts = tree
    monkeypatch.setattr(cd, "find_browsers", lambda environ=None: [])
    assert cd.capture(drafts, tmp_path / "png", root=root) == 1
    out = capsys.readouterr().out
    assert out.count("CAPTURE UNAVAILABLE") == 1, "printed once"
    assert "this agent cannot see its own drafts" in out
    assert "the quality of the deck will suffer" in out
    assert "playwright install chromium" in out
    assert "Google Chrome or Microsoft Edge" in out
    assert "DECKWRIGHT_BROWSER" in out
    assert "Do not continue to the port without a capture." in out
    # the real diagnostics, per route, under it
    assert "Tried, in order:" in out
    assert NO_PLAYWRIGHT in out
    assert "no Chromium-family binary found" in out
    # and the last resort, precisely enough to do by hand
    for name in ("s01.png", "s02.png", "s03.png"):
        assert name in out, name


def test_the_failure_names_every_route_it_tried(
        tree, tmp_path, monkeypatch, no_playwright, capsys):
    root, drafts = tree
    binary = tmp_path / "b.exe"
    binary.write_bytes(b"MZ")
    monkeypatch.setattr(cd, "find_browsers", lambda environ=None: [binary])
    monkeypatch.setattr(cd, "browser_command",
                        lambda b, url, png, scale, profile=None:
                        [sys.executable, "-c", "pass"])
    assert cd.capture(drafts, tmp_path / "png", root=root, timeout=30) == 1
    out = capsys.readouterr().out
    assert str(binary) in out and "s01.png was not written" in out


# ---- the counts and the server ----------------------------------------------

def test_the_expected_draft_count_is_exact(tree, tmp_path, capsys):
    root, drafts = tree
    assert cd.capture(drafts, tmp_path / "png", root=root, expect=10) == 1
    assert "expected 10 draft(s)" in capsys.readouterr().out


def test_the_server_serves_the_root_it_was_given(tree):
    """Served rather than opened as file://, because a CSS @import resolves
    against the importing stylesheet's own URL."""
    root, drafts = tree
    httpd, port = cd.serve_in_thread(root)
    try:
        with urllib.request.urlopen(
                "http://127.0.0.1:%d/deck/drafts/s01-cover.html" % port,
                timeout=10) as response:
            assert b"class=slide" in response.read()
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_a_url_that_is_not_there_is_counted_rather_than_logged(tree):
    """A stylesheet or a font that 404s renders a slide that is subtly wrong
    and says nothing; the count is what the capture reports afterwards."""
    root, _ = tree
    httpd, port = cd.serve_in_thread(root)
    try:
        with pytest.raises(urllib.error.HTTPError):
            urllib.request.urlopen("http://127.0.0.1:%d/nope.css" % port,
                                   timeout=10)
        assert httpd.missing == ["/nope.css"]
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_serve_refuses_a_root_that_is_not_a_directory(tmp_path):
    with pytest.raises(cd.CaptureError):
        cd.serve_in_thread(tmp_path / "nowhere")


def test_the_cli_fails_cleanly_on_a_directory_with_no_drafts(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--drafts", str(empty),
         "--out", str(tmp_path / "png")],
        capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 1
    assert proc.stdout.startswith("FAIL:")
    assert "Traceback" not in proc.stdout + proc.stderr


# ---- the one test that drives a real browser --------------------------------

def test_a_real_headless_browser_captures_a_1600x900_png(tmp_path):
    """The route the gate uses, end to end, on one throwaway draft.

    Skipped rather than failed when the machine holds no browser - and the
    skip reason names what was searched, because "skipped" with no reason is
    the silence this session's ruling ended."""
    browsers = cd.find_browsers()
    if not browsers:
        pytest.skip("no Chromium-family binary on this machine; searched %s"
                    % ", ".join(str(p) for p in cd.browser_candidates()))
    drafts = tmp_path / "drafts"
    drafts.mkdir()
    (drafts / "s01-only.html").write_text(
        "<html><body style='margin:0'>"
        "<div style='width:1280px;height:720px;background:#123456'></div>"
        "</body></html>", encoding="utf-8")
    out = tmp_path / "png"
    assert cd.capture(drafts, out, root=tmp_path, expect=1) == 0
    with Image.open(out / "s01.png") as image:
        assert image.size == (1600, 900)
        assert image.convert("RGB").getpixel((800, 450)) == (0x12, 0x34, 0x56)
